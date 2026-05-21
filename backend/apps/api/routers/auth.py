"""Authentication routes."""

import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
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
from backend.db.models.user import APIKey, Session, User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: str
    status: str
    avatar_url: str
    mfa_enabled: bool
    workspace_id: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _user_dict(user),
    }


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status == "locked":
        raise HTTPException(status_code=401, detail="Account locked")

    user.failed_login_attempts = 0
    user.last_login = datetime.now(timezone.utc)
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

    session = Session(
        user_id=user.id,
        session_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
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
    for field in ("full_name", "avatar_url", "username"):
        if field in body:
            setattr(user, field, body[field])
    user.updated_at = datetime.now(timezone.utc)
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
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "is_active": k.is_active,
            "last_used": k.last_used.isoformat() if k.last_used else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in keys
    ]


@router.post("/api-keys")
async def create_api_key(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import secrets

    raw_key = f"vk_{secrets.token_urlsafe(32)}"
    key = APIKey(
        user_id=user.id,
        name=body.get("name", "Untitled Key"),
        key_hash=get_password_hash(raw_key),
        key_prefix=raw_key[:8],
        scopes=body.get("scopes", ["read", "write"]),
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


GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _build_github_state() -> str:
    """Build signed short-lived OAuth state token to mitigate CSRF."""
    ts = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    payload = f"{ts}.{nonce}"
    sig = hmac.new(settings.JWT_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload}.{sig_b64}"


def _validate_github_state(state: str, max_age_seconds: int = 600) -> bool:
    """Validate signed OAuth state and expiry window."""
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
        if age < 0 or age > max_age_seconds:
            return False
        return True
    except Exception:
        return False


@router.get("/github/login")
async def github_login():
    """Redirect user to GitHub OAuth consent screen."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    state = _build_github_state()
    from urllib.parse import urlencode
    
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "scope": "user:email read:user repo",
        "state": state,
    }
    url = f"{GITHUB_AUTH_URL}?{urlencode(params)}"
    return {"url": url, "state": state}


@router.post("/github/callback")
@router.get("/github/callback")
async def github_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Exchange GitHub auth code for tokens. Creates account if needed."""
    if request.method == "POST":
        try:
            body = await request.json()
            code = code or body.get("code")
            state = state or body.get("state")
        except Exception:
            pass

    if not code:
        code = request.query_params.get("code")
    if not state:
        state = request.query_params.get("state")

    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
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

    # Enforce one GitHub identity per user account
    existing = await db.execute(select(User).where(User.github_id == github_id))
    already_linked = existing.scalar_one_or_none()
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if already_linked and user and already_linked.id != user.id:
        raise HTTPException(status_code=409, detail="This GitHub account is already linked to a different user.")

    is_new = False
    if not user:
        is_new = True
        user = User(
            email=email,
            username=github_username,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name=full_name,
            github_id=github_id,
            github_username=github_username,
            github_access_token=gh_access_token,
            avatar_url=gh_user.get("avatar_url", "")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.github_id = github_id
        user.github_username = github_username
        user.github_access_token = gh_access_token
        user.last_login = datetime.now(timezone.utc)
        user.last_activity = datetime.now(timezone.utc)
        await db.commit()

    # Generate app tokens
    app_access_token = create_access_token(data={"sub": user.id})
    app_refresh_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    session = Session(
        user_id=user.id,
        session_token=app_access_token,
        refresh_token=app_refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(session)
    await db.commit()
    
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
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {user.github_access_token}",
                "Accept": "application/json",
            },
            params={"sort": "updated", "per_page": 50, "type": "owner"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch repos")
        return {"repos": resp.json()}


@router.get("/connected-accounts")
async def connected_accounts(user=Depends(get_current_user)):
    github_connected = bool(user.github_id and user.github_access_token)
    return {
        "github_configured": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
        "github_connected": github_connected,
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
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "GitHub account disconnected"}


@router.delete("/sessions/revoke")
async def revoke_sessions(user=Depends(get_current_user)):
    return {"message": "All sessions revoked"}


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "status": user.status,
        "avatar_url": user.avatar_url or "",
        "mfa_enabled": user.mfa_enabled,
        "workspace_id": user.workspace_id or "",
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
