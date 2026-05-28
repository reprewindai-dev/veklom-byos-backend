"""JWT auth utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
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

def verify_token(token: str) -> dict:
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
            if enforcement_mode == "strict":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token audience")
            else:
                logging.warning(f"[JWT_AUD_WARN] {msg}")
                
        # JTI Replay Cache (Redis)
        jti = payload.get("jti")
        if jti:
            import redis
            try:
                # Synchronous redis check; fast enough for auth
                r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
                if r.exists(f"jti_cache:{jti}"):
                    logging.critical(f"[JWT_REPLAY_DETECTED] Token replay attempted for JTI {jti}")
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token replay detected")
                
                exp = payload.get("exp")
                if exp:
                    ttl = int(exp - datetime.now(timezone.utc).timestamp())
                    if ttl > 0:
                        r.setex(f"jti_cache:{jti}", ttl, "1")
            except redis.RedisError as e:
                logging.error(f"[REDIS_ERR] Failed to connect to Redis for JTI check: {e}")
                # Fail-open if Redis is down, or configure to fail-closed
        
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
            role = "super_admin"
            is_active = True
            status = "active"
        return MockAgentUser()

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = verify_token(credentials.credentials)
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

        user.last_activity = datetime.utcnow()
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


async def get_current_user_or_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    if credentials is not None:
        return await get_current_user(credentials, db)

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
