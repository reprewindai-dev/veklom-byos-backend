"""JWT auth utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db_session, get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)

import bcrypt

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    import uuid
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "aud": getattr(settings, "JWT_EXPECTED_AUDIENCE", "veklom-api")
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


import logging

def verify_token(token: str, enforce_replay: bool = False) -> dict:
    try:
        # Decode without verifying aud initially to allow soft enforcement
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False}
        )

        # Audience Enforcement
        aud = payload.get("aud")
        expected_aud = getattr(settings, "JWT_EXPECTED_AUDIENCE", "veklom-api")
        enforcement_mode = getattr(settings, "JWT_AUD_ENFORCEMENT", "warn")

        if aud != expected_aud:
            msg = f"Invalid or missing audience in token: expected {expected_aud}, got {aud}"
            if enforcement_mode == "strict" or settings.APP_ENV == "production":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token audience")
            else:
                logging.warning(f"[JWT_AUD_WARN] {msg}")

        # JTI replay checks (optional/configurable)
        jti = payload.get("jti")
        if jti:
            import redis
            try:
                r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
                replay_mode = str(getattr(settings, "JWT_REPLAY_ENFORCEMENT", "off")).lower()
                replay_seen = bool(r.exists(f"jti_cache:{jti}"))
                if replay_seen:
                    if enforce_replay or replay_mode == "strict":
                        logging.critical(f"[JWT_REPLAY_DETECTED] Token replay attempted for JTI {jti}")
                        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token replay detected")
                    if replay_mode == "warn":
                        logging.warning(f"[JWT_REPLAY_WARN] repeated JTI observed for token {jti}")

                exp = payload.get("exp")
                if exp:
                    ttl = int(exp - datetime.now(timezone.utc).timestamp())
                    if ttl > 0 and not replay_seen:
                        r.setex(f"jti_cache:{jti}", ttl, "1")
            except redis.RedisError as e:
                logging.error(f"[REDIS_ERR] Failed to connect to Redis for JTI check: {e}")
                # Fail-open if Redis is down

        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
):
    if getattr(request.state, "x402_paid", False):
        class MockAgentUser:
            id = "agent_autonomous"
            email = "agent@veklom.com"
            workspace_id = "agent_workspace"
            plan = "pro"
            role = "agent"
            is_active = True
            status = "active"
        return MockAgentUser()

    token = None
    if credentials is not None:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        # Fallback to query parameter token for EventSource/SSE streams
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication credentials")

    payload = verify_token(token)
    user_id: Optional[str] = payload.get("sub")

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    from backend.db.models.user import User

    async with get_db_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        status_value = (user.status or "").upper()
        if status_value in {"LOCKED", "SUSPENDED", "INACTIVE"} or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account inactive")
            
        if status_value == "PENDING_VERIFICATION":
            allowed_paths = ["/me", "/resend-verification", "/verify-email", "/logout", "/onboarding/vertical", "/config"]
            if not any(request.url.path.endswith(p) for p in allowed_paths):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_verification_required")

        # Performance optimization: Throttle last_activity updates to reduce DB writes and lock contention.
        # Only update every 5 minutes (300 seconds) rather than on every API request.
        now = datetime.utcnow()
        if not user.last_activity or (now - user.last_activity).total_seconds() > 300:
            user.last_activity = now
            await db.commit()
        return user


async def get_current_admin(user=Depends(get_current_user)):
    if (user.role or "").lower() not in ("admin", "super_admin", "owner"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_internal_operator(user=Depends(get_current_user)):
    """Guard for UACP internal API routes."""
    if (user.role or "").lower() not in ("admin", "super_admin", "operator", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UACP Internal Operator access required"
        )
    return user


# ---------------------------------------------------------------------------
# Optional auth — returns a guest user instead of raising 401.
# Used by public inference endpoints so the Playground works without login.
# ---------------------------------------------------------------------------

class _GuestUser:
    """Ephemeral guest identity for unauthenticated Playground/inference calls."""
    id = "guest"
    email = "guest@veklom.com"
    workspace_id = "guest"
    plan = "starter"
    role = "user"
    is_active = True
    status = "active"


_GUEST_USER = _GuestUser()


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
):
    """Like get_current_user but returns a guest user instead of raising 401.

    Use on endpoints that should work for unauthenticated users (Playground,
    public inference) while still providing the real user object when a valid
    token is present.
    """
    if getattr(request.state, "x402_paid", False):
        class MockAgentUser:
            id = "agent_autonomous"
            email = "agent@veklom.com"
            workspace_id = "agent_workspace"
            plan = "pro"
            role = "agent"
            is_active = True
            status = "active"
        return MockAgentUser()

    token = None
    if credentials is not None:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        return _GUEST_USER

    try:
        payload = verify_token(token)
    except HTTPException:
        return _GUEST_USER

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        return _GUEST_USER

    from backend.db.models.user import User

    async with get_db_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return _GUEST_USER
        status_value = (user.status or "").upper()
        if status_value in {"LOCKED", "SUSPENDED", "INACTIVE"} or not user.is_active:
            return _GUEST_USER
        # Performance optimization: Throttle last_activity updates to reduce DB writes and lock contention.
        # Only update every 5 minutes (300 seconds) rather than on every API request.
        now = datetime.utcnow()
        if not user.last_activity or (now - user.last_activity).total_seconds() > 300:
            user.last_activity = now
            await db.commit()
        return user


async def get_current_user_or_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    if credentials is not None:
        return await get_current_user(request, credentials)

    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        if not api_key_header.startswith("byos_"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key format")

        prefix = api_key_header[:10]
        from backend.db.models.user import APIKey, User
        result = await db.execute(select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True))
        keys = result.scalars().all()
        for key in keys:
            if verify_password(api_key_header, key.key_hash):
                user_res = await db.execute(select(User).where(User.id == key.user_id))
                user = user_res.scalar_one_or_none()
                if user and user.status == "active":
                    user.last_activity = datetime.now(timezone.utc)
                    await db.commit()
                    return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive API Key")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication credentials missing")



def check_workspace_access(user, target_workspace_id: str) -> bool:
    """
    Check if a user has access to a specific workspace.
    Allows SUPER_ADMIN to access any workspace.
    """
    if not target_workspace_id:
        return True

    if user.workspace_id == target_workspace_id:
        return True

    role = (getattr(user, "role", "") or "").upper()
    if role == "SUPER_ADMIN":
        return True

    return False


async def require_workspace_access(
    workspace_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    FastAPI dependency to ensure the user has access to the requested workspace.
    If no workspace_id is provided in the request, it passes.
    """
    if workspace_id and not check_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    return current_user

async def get_rls_db(
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a database session with the PostgreSQL RLS context set for the current tenant.
    This enforces isolation at the DB layer using current_setting('app.current_tenant_id').
    The session is safely reset in a finally block to prevent leakage across pooled connections.
    """
    tenant_id = getattr(user, "workspace_id", None) or getattr(user, "tenant_id", "default_tenant")
    
    # Inject tenant variable
    await db.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})
    try:
        yield db
    finally:
        # Prevent connection pool leakage
        try:
            await db.execute(text("RESET app.current_tenant_id"))
        except Exception:
            pass

