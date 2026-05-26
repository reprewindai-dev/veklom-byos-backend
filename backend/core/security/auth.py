"""JWT auth utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from backend.core.config.settings import settings
from backend.core.database.database import get_db_session

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
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
):
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
