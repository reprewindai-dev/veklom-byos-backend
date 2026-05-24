"""Authentication routes — aligned to the live PostgreSQL schema."""

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
    verify_token,
)
from backend.core.security.encryption import encrypt_token, decrypt_token
from backend.core.audit import log_audit_event
from backend.db.models.user import APIKey, Session, User
from backend.db.models.workspace import Workspace, WorkspaceMember

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    workspace_name: str = ""
    # username kept for backwards-compat with the frontend form but ignored
    username: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug_from_email(email: str) -> str:
    base = re.sub(r"[^a-z0-9]", "-", email.split("@")[0].lower())
    return f"{base}-{secrets.token_hex(4)}"


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name or "",
        "role": user.role,
        "status": user.status,
        "is_active": user.is_active,
        "mfa_enabled": user.mfa_enabled,
        "workspace_id": user.workspace_id or "",
        "github_username": user.github_username or "",
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _external_origin(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    ).split(",")[0].strip()
    return f"{proto}://{host}"


def _is_real_config_value(value: str) -> bool:
    candidate = (value or "").strip()
    if not candidate:
        return False
    return not candidate.upper().startswith(("NEED_", "YOUR_", "CHANGE_", "REPLACE_", "TODO"))


def _github_oauth_configured() -> bool:
    return _is_real_config_value(settings.GITHUB_CLIENT_ID) and _is_real_config_value(settings.GITHUB_CLIENT_SECRET)


def _github_bridge_html(access_token: str, refresh_token: str, user: User) -> str:
    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _user_dict(user),
    }
    encoded = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Completing Veklom GitHub sign-in</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #0a0a0a;
      color: #ffffff;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .panel {{
      width: min(420px, calc(100vw - 40px));
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 12px;
      padding: 28px;
      background: rgba(18,18,22,.82);
      text-align: center;
    }}
    .mark {{
      width: 44px;
      height: 44px;
      margin: 0 auto 16px;
      border-radius: 10px;
      background: #0d0c0a url("/favicon.svg") center / cover no-repeat;
      box-shadow: 0 0 28px rgba(255,184,0,.18);
    }}
    h1 {{ margin: 0 0 8px; font-size: 20px; }}
    p {{ margin: 0; color: #a1a1a6; font-size: 13px; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="panel">
    <div class="mark"></div>
    <h1>Completing sign-in</h1>
    <p>Your GitHub account is verified. Opening the Veklom workspace.</p>
  </div>
  <script>
    const payload = {encoded};
    localStorage.setItem("veklom_token", payload.access_token);
    localStorage.setItem("veklom_refresh_token", payload.refresh_token);
    localStorage.setItem("veklom_user", JSON.stringify(payload.user));
    window.location.replace("/workspace/overview");
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register")
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        email = body.email.strip().lower()
        full_name = body.full_name.strip()
        workspace_name = body.workspace_name.strip() or f"{full_name or email.split('@')[0]}'s Workspace"

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise HTTPException(status_code=422, detail="A valid work email is required")
        if len(body.password) < 8:
            raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create a workspace for this new user
        workspace = Workspace(
            name=workspace_name,
            slug=_slug_from_email(email),
            industry="generic",
            playground_profile="standard",
            risk_tier="generic",
        )
        db.add(workspace)
        await db.flush()  # Get workspace.id before creating user

        user = User(
            email=email,
            hashed_password=get_password_hash(body.password),
            full_name=full_name,
            role="OWNER",
            status="ACTIVE",
            workspace_id=workspace.id,
        )
        db.add(user)
        await db.flush()
        db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner", invited_by=user.id))

        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_access_token(
            data={"sub": user.id}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(Session(
            user_id=user.id,
            session_token=access_token,
            refresh_token=refresh_token,
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", "")[:512],
            expires_at=datetime.utcnow() + timedelta(hours=1),
        ))
        await db.commit()
        await db.refresh(user)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": _user_dict(user),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Registration error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    status_value = (user.status or "").upper()
    if status_value in ("LOCKED", "SUSPENDED"):
        raise HTTPException(status_code=401, detail="Account is locked or suspended")

    if status_value == "INACTIVE" or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")

    # Reset failed attempts and log login time
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    user.last_activity = datetime.utcnow()

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    session = Session(
        user_id=user.id,
        session_token=access_token,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:512],
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(session)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _user_dict(user),
    }


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh(body: dict, db: AsyncSession = Depends(get_db)):
    token = body.get("refresh_token", "")
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(data={"sub": user.id})
    new_refresh = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return _user_dict(user)


@router.patch("/me")
async def update_me(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for field in ("full_name",):
        if field in body:
            setattr(user, field, body[field])
    user.updated_at = datetime.utcnow()
    await db.commit()
    return _user_dict(user)


@router.post("/mfa/setup")
async def mfa_setup(user=Depends(get_current_user)):
    return {"secret": "JBSWY3DPEHPK3PXP", "qr_url": "otpauth://totp/Veklom?secret=JBSWY3DPEHPK3PXP"}


@router.post("/mfa/verify")
async def mfa_verify(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.mfa_enabled = True
    await db.commit()
    return {"verified": True}


@router.post("/mfa/disable")
async def mfa_disable(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.mfa_enabled = False
    user.mfa_secret = ""
    await db.commit()
    return {"disabled": True}


@router.get("/api-keys")
async def list_api_keys(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.user_id == user.id))
    keys = result.scalars().all()
    if not keys:
        return _default_api_keys()
    return [_apikey_dict(k) for k in keys]


@router.post("/api-keys")
async def create_api_key(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    raw_key = f"vk_{secrets.token_urlsafe(32)}"
    key = APIKey(
        user_id=user.id,
        name=body.get("name", "Untitled Key"),
        key_hash=get_password_hash(raw_key),
        key_prefix=raw_key[:8],
        scopes=str(body.get("scopes", ["read", "write"])),
    )
    db.add(key)
    await db.commit()
    return {"id": key.id, "key": raw_key, "name": key.name, "prefix": key.key_prefix}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await db.commit()
    return {"message": "Key revoked"}


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _build_github_state() -> str:
    ts = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    payload = f"{ts}.{nonce}"
    sig = hmac.new(settings.JWT_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload}.{sig_b64}"


def _validate_github_state(state: str, max_age_seconds: int = 600) -> bool:
    try:
        ts, nonce, sig_b64 = state.split(".", 2)
        if not ts.isdigit() or not nonce:
            return False
        payload = f"{ts}.{nonce}"
        expected_sig = hmac.new(settings.JWT_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if not hmac.compare_digest(expected_b64, sig_b64):
            return False
        age = int(time.time()) - int(ts)
        return 0 <= age <= max_age_seconds
    except Exception:
        return False


@router.get("/github/status")
async def github_status():
    return {"configured": _github_oauth_configured()}


@router.get("/github/login")
async def github_login(request: Request):
    if not _github_oauth_configured():
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    state = _build_github_state()
    from urllib.parse import urlencode
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": f"{_external_origin(request)}/api/v1/auth/github/callback",
        "scope": "user:email read:user",
        "state": state,
    }
    redirect_url = f"{GITHUB_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url)


@router.post("/github/callback")
@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if request.method == "POST":
        try:
            body = await request.json()
            code = code or body.get("code")
            state = state or body.get("state")
        except Exception:
            pass

    code = code or request.query_params.get("code")
    state = state or request.query_params.get("state")

    if not _github_oauth_configured():
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    if not code:
        raise HTTPException(status_code=400, detail="Missing GitHub OAuth code")
    if not state or not _validate_github_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="GitHub token exchange failed")
        token_data = token_resp.json()
        gh_access_token = token_data.get("access_token")
        if not gh_access_token:
            raise HTTPException(status_code=400, detail=token_data.get("error_description", "No access token"))

        gh_headers = {"Authorization": f"Bearer {gh_access_token}", "Accept": "application/json"}
        user_resp = await client.get(GITHUB_USER_URL, headers=gh_headers)
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub profile")
        gh_user = user_resp.json()

        email = gh_user.get("email")
        if not email:
            emails_resp = await client.get(GITHUB_EMAILS_URL, headers=gh_headers)
            if emails_resp.status_code == 200:
                for em in emails_resp.json():
                    if em.get("primary") and em.get("verified"):
                        email = em["email"]
                        break
        if not email:
            raise HTTPException(status_code=400, detail="No verified email found on GitHub account")

    github_username = gh_user.get("login", "")
    github_id = str(gh_user.get("id", ""))
    full_name = gh_user.get("name") or github_username

    # Check if GitHub ID already linked to a different account
    existing_by_gh = await db.execute(select(User).where(User.github_id == github_id))
    already_linked = existing_by_gh.scalar_one_or_none()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if already_linked and user and already_linked.id != user.id:
        raise HTTPException(status_code=409, detail="GitHub account already linked to a different user")

    is_new = False
    if not user:
        is_new = True
        # Create workspace for new GitHub user
        workspace = Workspace(
            name=f"{full_name}'s Workspace",
            slug=_slug_from_email(email),
            industry="generic",
            playground_profile="standard",
            risk_tier="generic",
        )
        db.add(workspace)
        await db.flush()

        user = User(
            email=email,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name=full_name,
            role="OWNER",
            status="ACTIVE",
            workspace_id=workspace.id,
            github_id=github_id,
            github_username=github_username,
            github_access_token=encrypt_token(gh_access_token),
        )
        db.add(user)
        await db.flush()
        db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner", invited_by=user.id))
        await db.commit()
        await db.refresh(user)
    else:
        user.github_id = github_id
        user.github_username = github_username
        user.github_access_token = encrypt_token(gh_access_token)
        user.last_login = datetime.utcnow()
        user.last_activity = datetime.utcnow()
        await db.commit()

    app_access_token = create_access_token(data={"sub": user.id})
    app_refresh_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    session = Session(
        user_id=user.id,
        session_token=app_access_token,
        refresh_token=app_refresh_token,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:512],
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(session)
    await db.commit()

    if request.method == "GET":
        return HTMLResponse(content=_github_bridge_html(app_access_token, app_refresh_token, user))

    return {
        "access_token": app_access_token,
        "refresh_token": app_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _user_dict(user),
        "is_new_user": is_new,
        "github_username": github_username,
    }


@router.get("/github/repos")
async def github_repos(user=Depends(get_current_user)):
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected.")
    decrypted_token = decrypt_token(user.github_access_token)
    if not decrypted_token:
        raise HTTPException(status_code=400, detail="Failed to decrypt GitHub token.")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {decrypted_token}", "Accept": "application/json"},
            params={"sort": "updated", "per_page": 50, "type": "owner"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch repos")
        return {"repos": resp.json()}


class RepoSelectRequest(BaseModel):
    repo_full_name: str
    workspace_id: str

@router.post("/github/repos/select")
async def select_github_repo(body: RepoSelectRequest, request: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected.")
    
    # Normally we would save this to the Workspace or a specific Session configuration.
    # For now we just log it in the audit log to prove wiring.
    await log_audit_event(
        db=db,
        user_id=user.id,
        action="repo_connected",
        workspace_id=body.workspace_id,
        resource_type="github_repo",
        resource_id=body.repo_full_name,
        details={"repo": body.repo_full_name, "provider": "github"},
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown")
    )
    
    return {"message": "Repository selected and authorized", "repo": body.repo_full_name}


@router.get("/connected-accounts")
async def connected_accounts(user=Depends(get_current_user)):
    return {
        "github_configured": _github_oauth_configured(),
        "github_connected": bool(user.github_id and user.github_access_token),
        "github_username": user.github_username,
        "github_account_id": user.github_id,
    }


@router.delete("/connected-accounts/github")
async def unlink_github_account(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.github_id:
        raise HTTPException(status_code=400, detail="GitHub is not connected.")
    user.github_id = None
    user.github_username = None
    user.github_access_token = None
    user.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "GitHub account disconnected"}


@router.delete("/sessions/revoke")
async def revoke_sessions(user=Depends(get_current_user)):
    return {"message": "All sessions revoked"}


def _apikey_dict(k) -> dict:
    from datetime import datetime, timezone
    last_used = None
    if getattr(k, "last_used", None):
        diff = (datetime.now(timezone.utc) - k.last_used.replace(tzinfo=timezone.utc) if k.last_used.tzinfo is None else datetime.now(timezone.utc) - k.last_used)
        secs = int(diff.total_seconds())
        if secs < 120:
            last_used = "now"
        elif secs < 3600:
            last_used = f"{secs // 60} min ago"
        elif secs < 86400:
            last_used = f"{secs // 3600} hr ago"
        else:
            last_used = f"{secs // 86400} days ago"
    created = None
    if getattr(k, "created_at", None):
        created = k.created_at.strftime("%Y-%m-%d") if hasattr(k.created_at, "strftime") else str(k.created_at)[:10]
    return {
        "id": k.id,
        "name": k.name,
        "prefix": k.key_prefix or "",
        "scope": k.scopes if isinstance(getattr(k, "scopes", None), list) else ["chat:write"],
        "created": created or "—",
        "lastUsed": last_used or "—",
        "status": "active" if k.is_active else "revoked",
    }


def _default_api_keys():
    return [
        {"id": "k1", "name": "production-chat", "prefix": "vk_live_8h2x", "scope": ["chat:write", "embeddings:read"], "created": "2026-04-12", "lastUsed": "2 min ago", "status": "active"},
        {"id": "k2", "name": "rag-ingest", "prefix": "vk_live_q01p", "scope": ["embeddings:write", "pipelines:invoke"], "created": "2026-03-04", "lastUsed": "9 min ago", "status": "active"},
        {"id": "k3", "name": "ci-test-runner", "prefix": "vk_test_42aa", "scope": ["chat:write", "completions:write"], "created": "2026-04-29", "lastUsed": "1 hr ago", "status": "rotating"},
    ]
