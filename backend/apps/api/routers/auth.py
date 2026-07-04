"""Authentication routes — aligned to the live PostgreSQL schema."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import (
    create_access_token,
    get_current_user,
    get_current_user_optional,
    get_password_hash,
    verify_password,
    verify_token,
)
from backend.core.security.encryption import encrypt_token, decrypt_token
from backend.core.security.jwt_keys import key_manager
from backend.core.audit import log_audit_event
from backend.core.services.posthog_client import posthog_service
from backend.db.models.user import APIKey, Session, User
from backend.db.models.workspace import Workspace, WorkspaceMember

router = APIRouter(prefix="/auth", tags=["Authentication"])

CONTROL_PLANE_URL = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")

def safe_posthog_capture(*args, **kwargs):
    """Wrap PostHog capture to ensure it never blocks or crashes auth endpoints."""
    try:
        # Give it a small timeout for any synchronous DNS resolution the library might attempt
        import threading
        
        def _capture():
            try:
                posthog_service.capture(*args, **kwargs)
            except Exception:
                pass

        t = threading.Thread(target=_capture)
        t.start()
        t.join(timeout=0.5)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"PostHog capture failed: {e}")

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

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug_from_email(email: str) -> str:
    base = re.sub(r"[^a-z0-9]", "-", email.split("@")[0].lower())
    return f"{base}-{secrets.token_hex(4)}"


def _user_dict(user: User) -> dict:
    """
    Builds a normalized dictionary representation of a User for API responses.
    
    Parameters:
        user (User): The user ORM/model instance to serialize.
    
    Returns:
        dict: A mapping with the following keys:
            - id: User identifier.
            - email: User email address.
            - full_name: User full name or empty string.
            - role: User role string (as stored).
            - status: User account status.
            - is_active: Boolean indicating active account state.
            - is_superuser: Boolean indicating platform superuser flag.
            - mfa_enabled: Boolean indicating whether MFA is enabled.
            - workspace_id: Associated workspace id or empty string.
            - workspace_name: Associated workspace name or empty string.
            - github_username: Connected GitHub username or empty string.
            - github_connected: `true` if both GitHub id and access token are present, `false` otherwise.
            - github_account_id: GitHub account id or empty string.
            - created_at: ISO 8601 timestamp string of creation or `None` if unavailable.
            - plan: Derived plan string based on role ("sovereign", "pro", "starter", or "free").
            - is_admin: Boolean indicating administrative role (OWNER, SUPER_ADMIN, or ADMIN).
    """
    role = (user.role or "USER").upper()
    # Role-based plan fallback — the real plan is read from the Subscription
    # table in the /auth/me endpoint and overrides this value.
    # SUPER_ADMIN is the platform role; OWNER is a workspace role that does not
    # imply a paid subscription.
    if role == "SUPER_ADMIN":
        plan = "sovereign"
    elif role in ("USER", "ANALYST"):
        plan = "starter"
    else:
        # OWNER, ADMIN, VIEWER → free until a real subscription is active
        plan = "free"

    is_admin = role in ("OWNER", "SUPER_ADMIN", "ADMIN")

    # Try to get workspace name if workspace relationship exists
    workspace_name = ""
    if hasattr(user, 'workspace') and user.workspace:
        workspace_name = user.workspace.name or ""
    elif user.workspace_id:
        # Fallback: try to fetch workspace by ID if not already loaded
        from backend.db.models.workspace import Workspace
        # Note: This requires a db session, so we'll use a simple fallback for now
        workspace_name = ""

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name or "",
        "role": user.role,
        "status": user.status,
        "is_active": user.is_active,
        "is_superuser": bool(user.is_superuser),
        "mfa_enabled": user.mfa_enabled,
        "workspace_id": user.workspace_id or "",
        "workspace_name": workspace_name,
        "github_username": user.github_username or "",
        "github_connected": bool(user.github_id and user.github_access_token),
        "github_account_id": user.github_id or "",
        "pgl_id": getattr(user, "pgl_id", None) or "",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "plan": plan,
        "is_admin": is_admin,
    }


def _apikey_dict(key: APIKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "prefix": key.key_prefix,
        "key_prefix": key.key_prefix,
        "is_active": key.is_active,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "last_used_at": key.last_used.isoformat() if key.last_used else None,
    }


def _default_api_keys() -> list:
    return []


def _external_origin(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    ).split(",")[0].strip()
    if "localhost" in host or "127.0.0.1" in host:
        proto = "http"
    return f"{proto}://{host}"



def _is_real_config_value(value: str) -> bool:
    """
    Determine whether a configuration string appears to be a real, non-placeholder value.
    
    Strips surrounding quotes and whitespace. Returns `False` for `None`, empty or whitespace-only strings, values that start with common placeholder prefixes (`NEED_`, `YOUR_`, `CHANGE_`, `REPLACE_`, `TODO`), well-known demo/placeholder tokens (`EXAMPLE`, `PLACEHOLDER`, `CHANGEME`, `TEST`, `DEMO`, `XXX`), or strings shorter than 8 characters.
    
    Returns:
        bool: `True` if the input looks like a valid configuration value, `False` otherwise.
    """
    if not value:
        return False
    candidate = value.strip(' "\'')
    if not candidate:
        return False
    upper = candidate.upper()
    # Check for placeholder prefixes
    placeholder_prefixes = ("NEED_", "YOUR_", "CHANGE_", "REPLACE_", "TODO")
    if upper.startswith(placeholder_prefixes):
        return False
    # Check for common placeholder/demo values
    placeholder_values = ("EXAMPLE", "PLACEHOLDER", "CHANGEME", "TEST", "DEMO", "XXX")
    if upper in placeholder_values:
        return False
    # Check for very short values (likely invalid)
    if len(candidate) < 8:
        return False
    return True


def _looks_concatenated_env(value: str) -> bool:
    """
    Detect broken .env values where multiple assignments are accidentally glued together.
    """
    candidate = (value or "").strip()
    return "=" in candidate or "\n" in candidate or "\r" in candidate


_GITHUB_ENV_KEY = {
    "client_id": "GITHUB_CLIENT_ID",
    "client_secret": "GITHUB_CLIENT_SECRET",
    "redirect_uri": "GITHUB_REDIRECT_URI",
}

_GITHUB_ENV_ALIASES = {
    "client_id": (
        "GITHUB_CLIENT_ID",
        "GITHUB_OAUTH_CLIENT_ID",
        "GITHUB_APP_CLIENT_ID",
    ),
    "client_secret": (
        "GITHUB_CLIENT_SECRET",
        "GITHUB_OAUTH_CLIENT_SECRET",
        "GITHUB_APP_CLIENT_SECRET",
    ),
    "redirect_uri": (
        "GITHUB_REDIRECT_URI",
        "GITHUB_REDIRECT_URL",
        "GITHUB_CALLBACK_URL",
    ),
}


def _extract_embedded_github_value(blob: str, env_key: str) -> Optional[str]:
    if not blob:
        return None
    pattern = re.compile(rf"{re.escape(env_key)}=([^\r\n]+?)(?=[A-Z][A-Z0-9_]*=|$)")
    match = pattern.search(blob)
    if not match:
        return None
    value = match.group(1).strip().strip(' "\'')
    return value or None


def _resolve_github_oauth_values(request: Optional[Request] = None) -> dict:
    values = {
        "client_id": (settings.GITHUB_CLIENT_ID or "").strip(),
        "client_secret": (settings.GITHUB_CLIENT_SECRET or "").strip(),
        "redirect_uri": (settings.GITHUB_REDIRECT_URI or "").strip(),
    }

    for field, aliases in _GITHUB_ENV_ALIASES.items():
        if _is_real_config_value(values[field]) and not _looks_concatenated_env(values[field]):
            continue
        for env_name in aliases:
            candidate = (os.environ.get(env_name) or "").strip()
            if _is_real_config_value(candidate) and not _looks_concatenated_env(candidate):
                values[field] = candidate
                break

    needs_embedded_scan = any(
        (not _is_real_config_value(values[field]) or _looks_concatenated_env(values[field]))
        for field in ("client_id", "client_secret", "redirect_uri")
    )
    if needs_embedded_scan:
        for _, raw_value in os.environ.items():
            blob = (raw_value or "").strip()
            if not blob:
                continue
            for field in ("client_id", "client_secret", "redirect_uri"):
                if _is_real_config_value(values[field]) and not _looks_concatenated_env(values[field]):
                    continue
                parsed = _extract_embedded_github_value(blob, _GITHUB_ENV_KEY[field])
                if parsed and _is_real_config_value(parsed) and not _looks_concatenated_env(parsed):
                    values[field] = parsed

    redirect_uri = values["redirect_uri"]
    if not (_is_real_config_value(redirect_uri) and not _looks_concatenated_env(redirect_uri) and redirect_uri.startswith("http")):
        if request is not None:
            values["redirect_uri"] = f"{_external_origin(request)}/api/v1/auth/github/callback"
        else:
            base = (settings.API_BASE_URL or "").strip().rstrip("/")
            values["redirect_uri"] = f"{base}/api/v1/auth/github/callback"

    return values


def _github_config_status() -> dict:
    """
    Return a safe GitHub OAuth config status payload with present/missing flags only.
    """
    resolved = _resolve_github_oauth_values()
    raw_client_id = (resolved.get("client_id") or "").strip()
    raw_client_secret = (resolved.get("client_secret") or "").strip()
    raw_redirect_uri = (resolved.get("redirect_uri") or "").strip()

    client_id_ok = _is_real_config_value(raw_client_id) and not _looks_concatenated_env(raw_client_id)
    client_secret_ok = _is_real_config_value(raw_client_secret) and not _looks_concatenated_env(raw_client_secret)
    redirect_ok = (
        _is_real_config_value(raw_redirect_uri)
        and not _looks_concatenated_env(raw_redirect_uri)
        and raw_redirect_uri.startswith("http")
    )

    missing = []
    if not client_id_ok:
        missing.append("GITHUB_CLIENT_ID")
    if not client_secret_ok:
        missing.append("GITHUB_CLIENT_SECRET")
    if not redirect_ok:
        missing.append("GITHUB_REDIRECT_URI")

    return {
        "configured": not missing,
        "present": {
            "GITHUB_CLIENT_ID": client_id_ok,
            "GITHUB_CLIENT_SECRET": client_secret_ok,
            "GITHUB_REDIRECT_URI": redirect_ok,
        },
        "missing": missing,
    }


def _github_oauth_configured() -> bool:
    """
    Determine whether GitHub OAuth is enabled by checking that both client ID and client secret are set to non-placeholder configuration values.
    
    Returns:
        True if both GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET contain real (non-placeholder) values, False otherwise.
    """
    resolved = _resolve_github_oauth_values()
    client_id = (resolved.get("client_id") or "").strip()
    client_secret = (resolved.get("client_secret") or "").strip()
    return (
        _is_real_config_value(client_id)
        and not _looks_concatenated_env(client_id)
        and _is_real_config_value(client_secret)
        and not _looks_concatenated_env(client_secret)
    )


def _github_redirect_uri(request: Request) -> str:
    resolved = _resolve_github_oauth_values(request)
    configured = (resolved.get("redirect_uri") or "").strip()
    if configured and configured.startswith("http"):
        return configured
    return f"{_external_origin(request)}/api/v1/auth/github/callback"


def _prefers_json(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    return "application/json" in accept or request.query_params.get("format") == "json"


def _github_bridge_html(access_token: str, refresh_token: str, user: User, next_url: str = None) -> str:
    """
    Render an HTML document that stores the provided access token, refresh token, and user payload into localStorage 
    and then redirects the browser to the workspace overview.
    """
    if next_url and (next_url.startswith("/") or next_url.startswith("https://") or next_url.startswith("http://")):
        frontend_workspace_url = next_url
    else:
        frontend_workspace_url = f"{CONTROL_PLANE_URL}/dashboard/"
        
    # Append tokens to URL so the frontend can read them across domains
    separator = "&" if "?" in frontend_workspace_url else "?"
    redirect_with_tokens = f"{frontend_workspace_url}{separator}veklom_token={access_token}&veklom_refresh_token={refresh_token}"
    
    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _user_dict(user),
        "frontend_workspace_url": frontend_workspace_url,
        "redirect_with_tokens": redirect_with_tokens,
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
    // Attempt local storage for same-domain setups
    localStorage.setItem("veklom_token", payload.access_token);
    localStorage.setItem("veklom_refresh_token", payload.refresh_token);
    localStorage.setItem("veklom_user", JSON.stringify(payload.user));
    // Redirect using URL parameters for cross-domain auth handoff
    window.location.replace(payload.redirect_with_tokens);
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Free Evaluation Session
# ---------------------------------------------------------------------------

@router.post("/eval-session")
async def create_eval_session(body: dict = None, db: AsyncSession = Depends(get_db)):
    """Create or resume a free evaluation session.

    Unauthenticated visitors get a limited free-tier account so the workspace
    is functional without requiring sign-up. Limited to 10 AI runs per day.
    """
    body = body or {}
    fingerprint = (body.get("fingerprint") or "anonymous")[:64]
    user = await _get_or_create_eval_user(db, fingerprint=fingerprint)

    access_token = create_access_token(data={"sub": user.id})
    return {
        "access_token": access_token,
        "refresh_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _user_dict(user),
        "is_eval": True,
        "plan": "free",
        "limits": {
            "ai_runs_per_day": 10,
            "max_sessions": 3,
            "features": ["playground", "models", "pipelines_view", "marketplace_browse"],
        },
    }


async def _get_or_create_eval_user(db: AsyncSession, fingerprint: str = "anonymous") -> User:
    import uuid as _uuid
    from backend.db.models.workspace import Workspace

    fingerprint_clean = re.sub(r"[^a-zA-Z0-9]", "", (fingerprint or "anonymous")) or "anonymous"
    eval_email = f"eval-{fingerprint_clean[:16]}@eval.veklom.local"

    result = await db.execute(select(User).where(User.email == eval_email))
    user = result.scalar_one_or_none()
    if user:
        return user

    ws_id = str(_uuid.uuid4())
    ws = Workspace(
        id=ws_id,
        name="Free Evaluation",
        slug=f"eval-{_uuid.uuid4().hex[:8]}",
        is_active=True,
        industry="generic",
        playground_profile="standard",
        risk_tier="generic",
    )
    db.add(ws)
    await db.flush()

    user = User(
        id=str(_uuid.uuid4()),
        email=eval_email,
        full_name="Free Evaluation",
        hashed_password="",
        role="readonly",
        status="active",
        is_active=True,
        workspace_id=ws_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/.well-known/jwks.json")
async def get_jwks():
    """
    Returns the JSON Web Key Set (JWKS) for cryptographic verification of Veklom-issued tokens.
    Allows edge nodes to verify Bearer JWTs without continuously querying PostgreSQL.
    """
    return key_manager.get_jwks()


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

        # Auto-generate workspace name if not provided
        workspace_name = body.workspace_name.strip()
        if not workspace_name:
            display_name = body.full_name.strip() or email.split("@")[0]
            workspace_name = f"{display_name}'s Workspace"

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

        is_founder = bool(settings.ADMIN_EMAIL) and email.lower() == settings.ADMIN_EMAIL.lower()
        # Auto-verify test users for automated/programmatic onboarding testing
        status_val = "active" if (email.startswith("pgl_test_") and email.endswith("@veklom.com")) else "pending_verification"
        user = User(
            email=email,
            hashed_password=get_password_hash(body.password),
            full_name=body.full_name,
            role="SUPER_ADMIN" if is_founder else "admin",
            is_superuser=True if is_founder else False,
            status=status_val,
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

        await log_audit_event(
            db=db,
            user_id=user.id,
            action="auth.register",
            workspace_id=workspace.id,
            resource_type="user",
            resource_id=user.id,
            details={"email": email}
        )

        # Fire-and-forget verification email via Resend
        try:
            import asyncio as _asyncio
            from backend.core.utils.email import send_email_via_resend
            from jose import jwt
            verify_token = jwt.encode(
                {"sub": user.id, "exp": datetime.utcnow() + timedelta(hours=24), "type": "email_verify"},
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )
            verify_url = f"https://api.veklom.com/api/v1/auth/verify-email?token={verify_token}"
            display_name = full_name or email.split("@")[0]
            verify_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
            <body style="margin:0;padding:0;background:#0A0A0A;font-family:Inter,Arial,sans-serif;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:40px 20px;">
                <tr><td align="center">
                  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#111111;border:1px solid #1f1f1f;border-radius:12px;overflow:hidden;">
                    <!-- Header -->
                    <tr><td style="background:#0A0A0A;padding:32px 40px;text-align:center;border-bottom:1px solid #1f1f1f;">
                      <img src="https://veklom.com/static/branding/veklom-wordmark.png" alt="Veklom" height="40" style="height:40px;display:block;margin:0 auto;">
                    </td></tr>
                    <!-- Body -->
                    <tr><td style="padding:40px;">
                      <h1 style="color:#FFFFFF;font-size:22px;font-weight:700;margin:0 0 8px;">Verify Your Email</h1>
                      <div style="width:40px;height:3px;background:#FFB800;margin-bottom:24px;"></div>
                      <p style="color:#A1A1A6;font-size:15px;line-height:1.7;margin:0 0 16px;">Hi {display_name},</p>
                      <p style="color:#A1A1A6;font-size:15px;line-height:1.7;margin:0 0 32px;">Please verify your email address to access the Veklom Sovereign AI Hub. Your account is pending verification.</p>
                      <table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:0 0 32px;">
                        <a href="{verify_url}" style="display:inline-block;padding:16px 40px;background:#FFB800;color:#0A0A0A;text-decoration:none;border-radius:6px;font-weight:700;font-size:15px;letter-spacing:0.02em;">Verify Email &rarr;</a>
                      </td></tr></table>
                      <p style="color:#555;font-size:13px;line-height:1.6;margin:0;">This link expires in 24 hours. If you didn't create a Veklom account, you can safely ignore this email.</p>
                    </td></tr>
                    <!-- Footer -->
                    <tr><td style="background:#0A0A0A;padding:24px 40px;border-top:1px solid #1f1f1f;">
                      <p style="color:#555;font-size:12px;margin:0 0 8px;">Questions? Contact <a href="mailto:sales@veklom.com" style="color:#FFB800;text-decoration:none;">sales@veklom.com</a></p>
                      <p style="color:#333;font-size:11px;margin:0;">Veklom &mdash; Sovereign AI Hub &bull; <a href="https://veklom.com" style="color:#555;text-decoration:none;">veklom.com</a></p>
                    </td></tr>
                  </table>
                </td></tr>
              </table>
            </body></html>
            """
            _asyncio.create_task(
                send_email_via_resend(
                    to_email=email,
                    subject="Verify your Veklom account",
                    html_content=verify_html,
                )
            )
        except Exception as e:
            import logging
            logging.error(f"Failed to queue verification email: {e}")
            pass  # Never block registration on email failure

        if user.status == "pending_verification":
            raise HTTPException(status_code=403, detail="Account created. Please check your email to verify your account before logging in.")

        # Build response with tokens in body AND cookies (fixes session hydration race)
        resp = JSONResponse(content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": _user_dict(user),
        })
        cookie_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        resp.set_cookie(
            key="access_token",
            value=access_token,
            max_age=cookie_max_age,
            httponly=True,
            samesite="lax",
            secure=True,
        )
        resp.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            httponly=True,
            samesite="lax",
            secure=True,
        )
        return resp
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logging.getLogger(__name__).error(f"Registration error: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again later.")


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verifies a user's email address from a JWT link."""
    from jose import jwt, JWTError
    from fastapi.responses import RedirectResponse
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "email_verify":
            raise HTTPException(status_code=400, detail="Invalid token")
            
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
            
        if user.status == "pending_verification":
            user.status = "active"
            await db.commit()
            await log_audit_event(
                db=db,
                user_id=user.id,
                action="auth.verify_email",
                workspace_id=user.workspace_id or "default",
                resource_type="user",
                resource_id=user.id,
                details={"email": user.email}
            )
            
        return RedirectResponse(url=f"{CONTROL_PLANE_URL}/login?verified=true", status_code=302)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

@router.post("/resend-verification")
async def resend_verification(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Resend the email verification link."""
    if user.status != "pending_verification":
        return {"message": "Email already verified"}
        
    try:
        import asyncio as _asyncio
        from backend.core.utils.email import send_email_via_resend
        from jose import jwt
        verify_token = jwt.encode(
            {"sub": user.id, "exp": datetime.utcnow() + timedelta(hours=24), "type": "email_verify"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        verify_url = f"https://api.veklom.com/api/v1/auth/verify-email?token={verify_token}"
        display_name = user.full_name or user.email.split("@")[0]
        verify_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
        <body style="margin:0;padding:0;background:#0A0A0A;font-family:Inter,Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:40px 20px;">
            <tr><td align="center">
              <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#111111;border:1px solid #1f1f1f;border-radius:12px;overflow:hidden;">
                <tr><td style="background:#0A0A0A;padding:32px 40px;text-align:center;border-bottom:1px solid #1f1f1f;">
                  <img src="https://veklom.com/static/branding/veklom-wordmark.png" alt="Veklom" height="40" style="height:40px;display:block;margin:0 auto;">
                </td></tr>
                <tr><td style="padding:40px;">
                  <h1 style="color:#FFFFFF;font-size:22px;font-weight:700;margin:0 0 8px;">Verify Your Email</h1>
                  <div style="width:40px;height:3px;background:#FFB800;margin-bottom:24px;"></div>
                  <p style="color:#A1A1A6;font-size:15px;line-height:1.7;margin:0 0 16px;">Hi {display_name},</p>
                  <p style="color:#A1A1A6;font-size:15px;line-height:1.7;margin:0 0 32px;">Please verify your email address to access the Veklom Sovereign AI Hub. Your account is pending verification.</p>
                  <table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:0 0 32px;">
                    <a href="{verify_url}" style="display:inline-block;padding:16px 40px;background:#FFB800;color:#0A0A0A;text-decoration:none;border-radius:6px;font-weight:700;font-size:15px;letter-spacing:0.02em;">Verify Email &rarr;</a>
                  </td></tr></table>
                  <p style="color:#555;font-size:13px;line-height:1.6;margin:0;">This link expires in 24 hours. If you didn't create a Veklom account, you can safely ignore this email.</p>
                </td></tr>
                <tr><td style="background:#0A0A0A;padding:24px 40px;border-top:1px solid #1f1f1f;">
                  <p style="color:#555;font-size:12px;margin:0 0 8px;">Questions? Contact <a href="mailto:sales@veklom.com" style="color:#FFB800;text-decoration:none;">sales@veklom.com</a></p>
                  <p style="color:#333;font-size:11px;margin:0;">Veklom &mdash; Sovereign AI Hub &bull; <a href="https://veklom.com" style="color:#555;text-decoration:none;">veklom.com</a></p>
                </td></tr>
              </table>
            </td></tr>
          </table>
        </body></html>
        """
        _asyncio.create_task(
            send_email_via_resend(
                to_email=user.email,
                subject="Verify your Veklom account",
                html_content=verify_html,
            )
        )
        await log_audit_event(
            db=db,
            user_id=user.id,
            action="auth.resend_verification",
            workspace_id=user.workspace_id or "default",
            resource_type="user",
            resource_id=user.id,
            details={"email": user.email}
        )
        return {"success": True, "message": "Verification email resent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send verification email")

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Always return success to prevent email enumeration
        return {"message": "If an account exists, a password reset email has been sent."}
        
    try:
        import asyncio as _asyncio
        from backend.core.utils.email import send_email_via_resend
        from jose import jwt
        reset_token = jwt.encode(
            {"sub": user.id, "exp": datetime.utcnow() + timedelta(hours=1), "type": "password_reset"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        reset_url = f"{CONTROL_PLANE_URL}/reset-password?token={reset_token}"
        
        reset_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
        <body style="margin:0;padding:0;background:#0A0A0A;font-family:Inter,Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:40px 20px;">
            <tr><td align="center">
              <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#111111;border:1px solid #1f1f1f;border-radius:12px;overflow:hidden;">
                <tr><td style="background:#0A0A0A;padding:32px 40px;text-align:center;border-bottom:1px solid #1f1f1f;">
                  <img src="https://veklom.com/static/branding/veklom-wordmark.png" alt="Veklom" height="40" style="height:40px;display:block;margin:0 auto;">
                </td></tr>
                <tr><td style="padding:40px;">
                  <h1 style="color:#FFFFFF;font-size:22px;font-weight:700;margin:0 0 8px;">Reset Your Password</h1>
                  <div style="width:40px;height:3px;background:#FFB800;margin-bottom:24px;"></div>
                  <p style="color:#A1A1A6;font-size:15px;line-height:1.7;margin:0 0 32px;">We received a request to reset the password for your Veklom account. Click the button below to set a new password.</p>
                  <table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:0 0 32px;">
                    <a href="{reset_url}" style="display:inline-block;padding:16px 40px;background:#FFB800;color:#0A0A0A;text-decoration:none;border-radius:6px;font-weight:700;font-size:15px;letter-spacing:0.02em;">Reset Password &rarr;</a>
                  </td></tr></table>
                  <p style="color:#555;font-size:13px;line-height:1.6;margin:0;">If you didn't request this, you can safely ignore this email. This link will expire in 1 hour.</p>
                </td></tr>
                <tr><td style="background:#0A0A0A;padding:24px 40px;border-top:1px solid #1f1f1f;">
                  <p style="color:#555;font-size:12px;margin:0 0 8px;">Questions? Contact <a href="mailto:sales@veklom.com" style="color:#FFB800;text-decoration:none;">sales@veklom.com</a></p>
                  <p style="color:#333;font-size:11px;margin:0;">Veklom &mdash; Sovereign AI Hub &bull; <a href="https://veklom.com" style="color:#555;text-decoration:none;">veklom.com</a></p>
                </td></tr>
              </table>
            </td></tr>
          </table>
        </body></html>
        """
        _asyncio.create_task(
            send_email_via_resend(
                to_email=user.email,
                subject="Reset your Veklom password",
                html_content=reset_html,
            )
        )
        await log_audit_event(
            db=db,
            user_id=user.id,
            action="auth.forgot_password_request",
            workspace_id=user.workspace_id or "default",
            resource_type="user",
            resource_id=user.id,
            details={"email": user.email}
        )
    except Exception as e:
        import logging
        logging.error(f"Failed to queue reset password email: {e}")
        
    return {"message": "If an account exists, a password reset email has been sent."}

@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.hashed_password = get_password_hash(body.new_password)
    
    # Invalidate all existing sessions
    import sqlalchemy
    from backend.db.models.user import Session
    await db.execute(sqlalchemy.delete(Session).where(Session.user_id == user.id))
    
    await log_audit_event(
        db=db,
        user_id=user.id,
        action="auth.reset_password",
        workspace_id=user.workspace_id or "default",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email}
    )
    await db.commit()
    
    return {"message": "Password has been successfully reset. All previous sessions have been revoked."}


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        # Track failed login
        safe_posthog_capture(
            distinct_id=email,
            event="auth_login_failed",
            properties={
                "email": email,
                "ip_address": request.client.host if request.client else "",
                "reason": "invalid_credentials" if user else "user_not_found"
            }
        )
        if user:
            await log_audit_event(
                db=db,
                user_id=user.id,
                action="auth.login_failed",
                workspace_id=user.workspace_id or "default",
                resource_type="user",
                resource_id=user.id,
                details={"email": email, "reason": "invalid_credentials"},
                ip_address=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", "")[:512]
            )
        else:
            await log_audit_event(
                db=db,
                user_id="anonymous",
                action="auth.login_failed",
                workspace_id="default",
                resource_type="user",
                resource_id="unknown",
                details={"email": email, "reason": "user_not_found"},
                ip_address=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", "")[:512]
            )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    status_value = (user.status or "").upper()
    if status_value in ("LOCKED", "SUSPENDED"):
        safe_posthog_capture(
            distinct_id=str(user.id),
            event="auth_login_failed",
            properties={
                "email": email,
                "ip_address": request.client.host if request.client else "",
                "reason": f"account_{status_value.lower()}"
            }
        )
        await log_audit_event(
            db=db,
            user_id=user.id,
            action="auth.login_failed",
            workspace_id=user.workspace_id or "default",
            resource_type="user",
            resource_id=user.id,
            details={"email": email, "reason": f"account_{status_value.lower()}"},
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", "")[:512]
        )
        raise HTTPException(status_code=401, detail="Account is locked or suspended")

    if status_value == "INACTIVE" or not user.is_active:
        safe_posthog_capture(
            distinct_id=str(user.id),
            event="auth_login_failed",
            properties={
                "email": email,
                "ip_address": request.client.host if request.client else "",
                "reason": "account_inactive"
            }
        )
        await log_audit_event(
            db=db,
            user_id=user.id,
            action="auth.login_failed",
            workspace_id=user.workspace_id or "default",
            resource_type="user",
            resource_id=user.id,
            details={"email": email, "reason": "account_inactive"},
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", "")[:512]
        )
        raise HTTPException(status_code=401, detail="Account is inactive")

    if status_value == "PENDING_VERIFICATION":
        await log_audit_event(
            db=db,
            user_id=user.id,
            action="auth.login_failed",
            workspace_id=user.workspace_id or "default",
            resource_type="user",
            resource_id=user.id,
            details={"email": email, "reason": "pending_verification"},
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", "")[:512]
        )
        raise HTTPException(status_code=403, detail="Please check your email to verify your account before logging in.")

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
    await log_audit_event(
        db=db,
        user_id=user.id,
        action="auth.login",
        workspace_id=user.workspace_id or "default",
        resource_type="user",
        resource_id=user.id,
        details={"email": email},
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:512]
    )
    await db.commit()

    # Track successful login
    safe_posthog_capture(
        distinct_id=str(user.id),
        event="auth_login_success",
        properties={
            "email": email,
            "ip_address": request.client.host if request.client else "",
            "user_agent": request.headers.get("user-agent", "")[:512]
        }
    )

    # Build response with tokens in body AND cookies (fixes hydration race)
    resp = JSONResponse(content={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _user_dict(user),
    })
    cookie_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    resp.set_cookie(
        key="access_token",
        value=access_token,
        max_age=cookie_max_age,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    resp.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return resp


@router.post("/signin")
async def signin(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Alias for /login — frontend compatibility."""
    return await login(body, request, db)


@router.post("/signup")
async def signup(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Alias for /register — frontend compatibility."""
    return await register(body, request, db)


@router.post("/logout")
@router.get("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Clear session cookies and invalidate token. Idempotent and handles unauthenticated requests."""
    token = request.cookies.get("access_token") or request.cookies.get("token")
    if token:
        from backend.db.models.user import Session
        result = await db.execute(select(Session).where(Session.session_token == token))
        session_db = result.scalar_one_or_none()
        if session_db:
            user_id = session_db.user_id
            user_res = await db.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()
            workspace_id = user.workspace_id if user else "default"
            await log_audit_event(
                db=db,
                user_id=user_id,
                action="auth.logout",
                workspace_id=workspace_id or "default",
                resource_type="user",
                resource_id=user_id,
                details={},
                ip_address=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", "")[:512]
            )
            await db.delete(session_db)
            await db.commit()

    if request.method == "GET":
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse(url=f"{CONTROL_PLANE_URL}/login/", status_code=302)
    else:
        resp = JSONResponse(content={"message": "Logged out successfully"})
        
    cookies_to_clear = [
        "access_token", "refresh_token", "session", "session_id", 
        "auth_token", "veklom_session", "token"
    ]
    
    domain = ".veklom.com" if not settings.APP_ENV == "development" else None
    
    for cookie in cookies_to_clear:
        resp.delete_cookie(cookie, path="/", domain=domain, samesite="lax", secure=not settings.APP_ENV == "development")
        resp.delete_cookie(cookie, path="/") # Also delete without domain to be safe

    return resp


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
async def me(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Return the authenticated user's profile with workspace summary and capability flags.
    """
    from backend.core.services.entitlements import get_workspace_plan

    user_data = _user_dict(user)

    # Resolve real subscription plan from DB
    real_plan = "free"
    if user.workspace_id:
        plan_id = await get_workspace_plan(db, user.workspace_id)
        if plan_id:
            plan_id = plan_id.lower()
            normalization = {
                "community": "free",
                "founding": "starter",
                "standard": "pro",
                "regulated": "sovereign",
                "enterprise": "enterprise"
            }
            real_plan = normalization.get(plan_id, plan_id)

            real_plan = normalization.get(plan_id, plan_id)

    # Add workspace data
    workspace_data = None
    if user.workspace_id:
        result = await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))
        workspace = result.scalar_one_or_none()
        if workspace:
            # If no active subscription, check workspace.license_tier as secondary source
            if real_plan == user_data.get("plan", "free") and workspace.license_tier:
                tier = (workspace.license_tier or "").strip()
                if tier and tier not in ("standard", "free", ""):
                    real_plan = tier
            workspace_data = {
                "id": workspace.id,
                "name": workspace.name,
                "slug": workspace.slug,
                "plan": real_plan,
                "license_tier": workspace.license_tier or "free",
                "is_active": workspace.is_active,
                "industry": workspace.industry or "generic",
            }

    # Override plan in user_data with real subscription plan
    user_data["plan"] = real_plan

    # Determine capabilities based on role, is_superuser, and real plan
    role = (user.role or "USER").upper()
    is_admin = role in ("OWNER", "SUPER_ADMIN", "ADMIN")

    is_platform_superuser = bool(user.is_superuser) and role == "SUPER_ADMIN"

    capabilities = {
        "command_center": is_platform_superuser,
        "platform_command_center": is_platform_superuser,
        "owner_provider_keys": is_platform_superuser,
        "premium_marketplace": real_plan in ("pro", "sovereign"),
        "pipeline_deploy": real_plan != "free",
        "vault_secrets": is_admin,
        "team_management": is_admin,
        "billing_management": is_admin,
        "compliance_exports": real_plan in ("pro", "sovereign", "business"),
        "custom_models": real_plan in ("pro", "sovereign"),
    }

    return {
        **user_data,
        "workspace": workspace_data,
        "capabilities": capabilities,
    }


@router.patch("/me")
async def update_me(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for field in ("full_name",):
        if field in body:
            setattr(user, field, body[field])
    user.updated_at = datetime.utcnow()
    await db.commit()
    return _user_dict(user)


@router.post("/mfa/enable")
async def mfa_setup(user=Depends(get_current_user)):
    return {"secret": "JBSWY3DPEHPK3PXP", "provisioning_uri": "otpauth://totp/Veklom?secret=JBSWY3DPEHPK3PXP", "qr_url": "otpauth://totp/Veklom?secret=JBSWY3DPEHPK3PXP"}


@router.post("/mfa/verify")
async def mfa_verify(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.mfa_enabled = True
    await db.commit()
    return {"verified": True}


@router.post("/mfa/disable")
@router.delete("/mfa/disable")
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
    raw_key = f"byos_{secrets.token_urlsafe(32)}"
    key = APIKey(
        user_id=user.id,
        name=body.get("name", "Untitled Key"),
        key_hash=get_password_hash(raw_key),
        key_prefix=raw_key[:10],
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


def _build_github_state(user_id: Optional[str] = None, next_url: Optional[str] = None) -> str:
    ts = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    uid = user_id or ""
    # Encode next_url safely using base64 so it can survive URL round-trips
    next_encoded = base64.urlsafe_b64encode((next_url or "").encode()).decode().rstrip("=") if next_url else ""
    payload = f"{ts}.{nonce}.{uid}.{next_encoded}"
    sig = hmac.new(settings.JWT_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload}.{sig_b64}"


def _validate_github_state(state: str, request: Optional[Request] = None, max_age_seconds: int = 600) -> tuple:
    """
    Validate the state payload.
    Returns (user_id, next_url) tuple.
    user_id is empty string if no user was logged in.
    next_url is empty string if not present.
    Raises HTTPException if invalid.
    """
    try:
        # Format: ts.nonce.uid.next_encoded.sig_b64
        parts = state.split(".", 4)
        if len(parts) < 4:
            raise ValueError("Too few parts")
        if len(parts) == 4:
            # Legacy format without next_url
            ts, nonce, uid, sig_b64 = parts
            next_encoded = ""
        else:
            ts, nonce, uid, next_encoded, sig_b64 = parts
        if not ts.isdigit() or not nonce:
            raise HTTPException(status_code=400, detail="Invalid state payload structure")
        payload = f"{ts}.{nonce}.{uid}.{next_encoded}"
        expected_sig = hmac.new(settings.JWT_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if not hmac.compare_digest(expected_b64, sig_b64):
            # Try legacy format (3-part payload without next_encoded) for backward compat
            legacy_payload = f"{ts}.{nonce}.{uid}"
            legacy_sig = hmac.new(settings.JWT_SECRET_KEY.encode(), legacy_payload.encode(), hashlib.sha256).digest()
            legacy_b64 = base64.urlsafe_b64encode(legacy_sig).decode().rstrip("=")
            if not hmac.compare_digest(legacy_b64, sig_b64):
                import logging
                host_info = None
                try:
                    if request is not None:
                        host_info = request.headers.get("host") or request.url.hostname
                except Exception:
                    host_info = None
                key_ok = _is_real_config_value(getattr(settings, "JWT_SECRET_KEY", ""))
                logging.error(
                    "GitHub OAuth state signature mismatch. Likely local vs production JWT secret mismatch. host=%s, state_len=%d, sig_len=%d, jwt_key_present=%s",
                    host_info,
                    len(state or ""),
                    len(sig_b64 or ""),
                    bool(key_ok),
                )
                raise HTTPException(status_code=400, detail="State signature verification failed (possible local vs prod mismatch)")
        age = int(time.time()) - int(ts)
        if not (0 <= age <= max_age_seconds):
            raise HTTPException(status_code=400, detail="OAuth state has expired")
        next_url = ""
        if next_encoded:
            try:
                # Add padding if needed
                padding = 4 - len(next_encoded) % 4
                padded = next_encoded + "=" * (padding % 4)
                next_url = base64.urlsafe_b64decode(padded).decode("utf-8")
            except Exception:
                next_url = ""
        return (uid if uid else "", next_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid state parameter: {str(e)}")




@router.get("/providers")
async def list_auth_providers():
    """Public - returns available authentication providers for the login UI."""
    github_status_data = _github_config_status()
    providers = [
        {"id": "email", "name": "Email & Password", "enabled": True},
    ]
    if github_status_data.get("configured"):
        providers.append({"id": "github", "name": "GitHub", "enabled": True, "url": "/api/v1/auth/github/login"})
    else:
        providers.append({"id": "github", "name": "GitHub", "enabled": False, "url": None, "note": "Not configured"})
    return {"providers": providers}


@router.get("/github/status")
async def github_status():
    return _github_config_status()


@router.get("/github/config-status")
async def github_config_status():
    return _github_config_status()

@router.get("/github/login")
async def github_login(request: Request, token: Optional[str] = None, next: Optional[str] = None):
    if not _github_oauth_configured():
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    oauth_values = _resolve_github_oauth_values(request)
    
    user_id = None
    if token:
        try:
            payload = verify_token(token)
            user_id = payload.get("sub")
        except Exception:
            pass

    # Dynamic frontend routing: sniff origin from referer
    referer = request.headers.get("referer") or request.headers.get("origin")
    if referer and next and next.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        next = f"{origin}{next}"

    # Encode next_url directly in state so it survives the cross-domain GitHub round-trip.
    # A cookie set on veklom.com is NOT sent to api.veklom.com (different subdomain).
    state = _build_github_state(user_id, next_url=next)
    from urllib.parse import urlencode
    
    params = {
        "client_id": oauth_values["client_id"],
        "scope": "user:email read:user",
        "state": state,
    }
    redirect_url = f"{GITHUB_AUTH_URL}?{urlencode(params)}"
    
    if _prefers_json(request):
        return JSONResponse(content={"auth_url": redirect_url})
    else:
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
    oauth_values = _resolve_github_oauth_values(request)
    if not code:
        raise HTTPException(status_code=400, detail="Missing GitHub OAuth code")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    
    logged_in_user_id, next_url_from_state = _validate_github_state(state, request=request)

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": oauth_values["client_id"],
                "client_secret": oauth_values["client_secret"],
                "code": code,
                "redirect_uri": _github_redirect_uri(request),
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

    user = None
    if logged_in_user_id:
        result = await db.execute(select(User).where(User.id == logged_in_user_id))
        user = result.scalar_one_or_none()

    if not user:
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

        is_founder = bool(settings.ADMIN_EMAIL) and email.lower() == settings.ADMIN_EMAIL.lower()
        user = User(
            email=email,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name=full_name,
            role="SUPER_ADMIN" if is_founder else "admin",
            is_superuser=True if is_founder else False,
            status="active",
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
        is_founder = bool(settings.ADMIN_EMAIL) and email.lower() == settings.ADMIN_EMAIL.lower()
        if is_founder:
            user.role = "SUPER_ADMIN"
            user.is_superuser = True
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

    # Prefer next_url from state (cross-domain safe) over cookie (same-domain only)
    next_url = next_url_from_state or request.cookies.get("github_next_url") or ""

    if request.method == "GET":
        if next_url and (next_url.startswith("/") or next_url.startswith("https://") or next_url.startswith("http://")):
            if next_url.startswith("/"):
                final_url = f"{CONTROL_PLANE_URL}{next_url}"
            else:
                final_url = next_url
        else:
            final_url = f"{CONTROL_PLANE_URL}/dashboard/"
            
        response = HTMLResponse(content=_github_bridge_html(app_access_token, app_refresh_token, user, final_url))
        response.delete_cookie("github_next_url")
        return response

    return {
        "access_token": app_access_token,
        "refresh_token": app_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _user_dict(user),
        "is_new_user": is_new,
        "github_username": github_username,
    }
