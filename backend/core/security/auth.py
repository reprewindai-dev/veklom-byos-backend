"""JWT auth utilities."""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db, reset_tenant_session, set_tenant_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)


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


_jwt_redis_client = None


async def _get_active_session(db: AsyncSession, user_id: str, token: str):
    """Return the active server-side session matching the presented access token."""
    from backend.db.models.user import Session

    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.session_token == token,
            Session.is_active.is_(True),
            Session.expires_at > datetime.utcnow(),
        )
    )
    return result.scalar_one_or_none()


def verify_token(token: str, enforce_replay: bool = False) -> dict:
    candidate_keys = [settings.JWT_SECRET_KEY]

    payload = None
    last_err = None
    for key in candidate_keys:
        try:
            # Decode without verifying aud initially to allow soft enforcement
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_aud": False}
            )
            break
        except JWTError as exc:
            last_err = exc

    if payload is None:
        # TODO: issuer/rotation drift must be resolved with the token issuer
        # owner; verification keys and JWT verification behavior stay unchanged here.
        try:
            unverified = jwt.get_unverified_claims(token)
            jti = unverified.get("jti")
            sub = unverified.get("sub")

            try:
                unverified_header = jwt.get_unverified_header(token)
                alg = unverified_header.get("alg")
                kid = unverified_header.get("kid")
            except Exception:
                alg = "unknown"
                kid = "unknown"

            logging.error(
                "[JWT_VERIFY_FAILED] jti=%s sub=%s token_prefix=%s alg=%s kid=%s error=%s",
                jti,
                sub,
                token[:8],
                alg,
                kid,
                last_err,
                exc_info=last_err,
            )
        except Exception as ue:
            logging.error(
                "[JWT_VERIFY_FAILED] jti=%s sub=%s token_prefix=%s error=%s metadata_error=%s",
                None,
                None,
                token[:8],
                last_err,
                ue
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from last_err

    # Audience Enforcement
    aud = payload.get("aud")
    expected_aud = getattr(settings, "JWT_EXPECTED_AUDIENCE", "veklom-api")
    if aud != expected_aud:
        msg = f"Invalid or missing audience in token: expected {expected_aud}, got {aud}"
        logging.error("[JWT_AUD_REJECTED] %s", msg)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token audience")

    # JTI replay checks (optional/configurable)
    jti = payload.get("jti")
    if jti:
        import redis
        global _jwt_redis_client
        try:
            if _jwt_redis_client is None:
                _jwt_redis_client = redis.Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            r = _jwt_redis_client
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


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
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
            full_name = "Autonomous Agent"
            is_superuser = False
            mfa_enabled = False
            github_username = ""
            github_id = ""
            github_access_token = ""
            pgl_id = "agent_pgl"
            created_at = datetime.now(timezone.utc)
            last_activity = datetime.now(timezone.utc)
        return MockAgentUser()

    token = None
    if credentials is not None:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication credentials")

    payload = verify_token(token)
    user_id: Optional[str] = payload.get("sub")
    jwt_workspace_id: Optional[str] = payload.get("workspace_id")

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Zero-trust: every JWT must carry a workspace_id claim.
    # Tokens without workspace_id cannot be given a tenant context, so we reject
    # them here rather than enabling bypass_rls which would allow cross-tenant
    # data access across all RLS-protected tables.
    if not jwt_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing workspace_id claim. Re-authenticate to obtain a scoped token."
        )

    from backend.db.models.user import User

    # The JWT claim is only a provisional scope used to locate the account under
    # RLS. It must never survive a failed authentication decision.
    await set_tenant_session(db, jwt_workspace_id)
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        if await _get_active_session(db, user_id, token) is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked or expired")

        if not user.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is missing a workspace assignment.",
            )
        if jwt_workspace_id != user.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace claim does not match account")

        status_value = (user.status or "").upper()
        if status_value in {"LOCKED", "SUSPENDED", "INACTIVE"} or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account inactive")

        if status_value == "PENDING_VERIFICATION":
            allowed_paths = {
                "/api/v1/auth/me",
                "/api/v1/auth/resend-verification",
                "/api/v1/auth/verify-email",
                "/api/v1/auth/logout",
                "/api/v1/workspace/onboarding/vertical",
                "/api/v1/workspace/config",
            }
            if request.url.path not in allowed_paths:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_verification_required")

        now_utc = datetime.utcnow()
        needs_commit = False

        # Ensure naive datetime is compared, as user.last_activity is usually naive
        last_activity = user.last_activity
        if last_activity and last_activity.tzinfo is not None:
            last_activity = last_activity.replace(tzinfo=None)

        # Throttle last_activity updates to max once per 5 minutes to reduce DB write contention
        if not last_activity or (now_utc - last_activity).total_seconds() > 300:
            user.last_activity = now_utc
            needs_commit = True

        if needs_commit:
            await db.commit()
    finally:
        await reset_tenant_session(db)

    # Only the database-backed workspace survives successful authentication.
    await set_tenant_session(db, user.workspace_id)
    # Expunge the user from this internal session before it closes.
    # After commit(), SQLAlchemy expires all attributes; if any route accesses
    # a relationship on the returned user, it would trigger a lazy-load inside
    # a closed session (the greenlet "missing greenlet" error). Expunging makes
    # the object detached — column values are preserved, relationships are not
    # lazily fetched (raises DetachedInstanceError if accessed, but that's safe
    # and catchable). Routes that need relationships should re-query via their
    # own injected db session.
    db.expunge(user)
    return user



async def get_current_admin(user=Depends(get_current_user)):
    if (user.role or "").lower() not in ("admin", "super_admin", "owner"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


class _InternalOperatorUser:
    """Sentinel user returned when x-uacp-internal-key auth succeeds."""
    id = "uacp-internal"
    email = "uacp-internal@veklom.com"
    workspace_id = "internal"
    plan = "operator"
    role = "operator"
    is_active = True
    status = "active"

_INTERNAL_OPERATOR_USER = _InternalOperatorUser()

_UACP_INTERNAL_KEY = os.getenv("UACP_INTERNAL_API_KEY", "") or os.getenv("UACP_ADMIN_KEY", "")


async def require_internal_operator(
    request: Request,
    x_uacp_internal_key: Optional[str] = Header(None, alias="x-uacp-internal-key"),
):
    """Guard for UACP internal API routes.

    Accepts either:
      1. A valid x-uacp-internal-key header (shared secret for machine-to-machine calls from UACP V3)
      2. A JWT bearer token with role admin/super_admin/operator/owner (human operators)
    """
    # --- Machine-to-machine: shared secret header ---
    if x_uacp_internal_key:
        if _UACP_INTERNAL_KEY and x_uacp_internal_key == _UACP_INTERNAL_KEY:
            return _INTERNAL_OPERATOR_USER
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid x-uacp-internal-key"
        )

    # --- Human operator: JWT bearer token ---
    try:
        credentials = await security_scheme(request)
        user = await get_current_user(request, credentials=credentials)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for UACP internal routes"
        )
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
    db: AsyncSession = Depends(get_db)
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
    jwt_workspace_id: Optional[str] = payload.get("workspace_id")

    if user_id is None:
        return _GUEST_USER

    from backend.db.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return _GUEST_USER

    if await _get_active_session(db, user_id, token) is None:
        return _GUEST_USER

    if jwt_workspace_id and jwt_workspace_id != user.workspace_id:
        return _GUEST_USER

    status_value = (user.status or "").upper()
    if status_value in {"LOCKED", "SUSPENDED", "INACTIVE"} or not user.is_active:
        return _GUEST_USER

    if user.workspace_id:
        from backend.core.database.database import set_tenant_session
        await set_tenant_session(db, user.workspace_id)

    now_utc = datetime.utcnow()

    # Ensure naive datetime is compared, as user.last_activity is usually naive
    last_activity = user.last_activity
    if last_activity and last_activity.tzinfo is not None:
        last_activity = last_activity.replace(tzinfo=None)

    if not last_activity or (now_utc - last_activity).total_seconds() > 300:
        user.last_activity = now_utc
        await db.commit()
    return user


async def get_current_user_or_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    if credentials is not None:
        return await get_current_user(request, credentials, db=db)

    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        if not api_key_header.startswith("byos_"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key format")

        prefix = api_key_header[:10]
        from sqlalchemy.orm import joinedload

        from backend.db.models.user import APIKey
        result = await db.execute(
            select(APIKey)
            .options(joinedload(APIKey.user))
            .where(APIKey.key_prefix == prefix, APIKey.is_active)
        )
        keys = result.scalars().all()
        for key in keys:
            if verify_password(api_key_header, key.key_hash):
                user = key.user
                if user is not None:
                    if not key.is_active or (key.expires_at and key.expires_at <= datetime.utcnow()):
                        continue
                    if key.workspace_id and key.workspace_id != user.workspace_id:
                        continue
                    if user.workspace_id:
                        from backend.core.database.database import set_tenant_session
                        await set_tenant_session(db, user.workspace_id)
                    now_utc = datetime.utcnow()
                    # Ensure naive datetime is compared, as user.last_activity is usually naive
                    last_activity = user.last_activity
                    if last_activity and last_activity.tzinfo is not None:
                        last_activity = last_activity.replace(tzinfo=None)
                    if not last_activity or (now_utc - last_activity).total_seconds() > 300:
                        user.last_activity = now_utc
                        await db.commit()
                    request.state.api_key_scopes = key.scopes or "[]"
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

    # RLS policies use app.workspace_id. SET LOCAL scopes the value to this transaction.
    await db.execute(text("SELECT set_config('app.workspace_id', :tenant_id, true)"), {"tenant_id": tenant_id})
    try:
        yield db
    finally:
        # Prevent connection pool leakage
        try:
            await reset_tenant_session(db)
        except Exception:
            pass
