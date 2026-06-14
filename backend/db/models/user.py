"""User and auth models — aligned to the live PostgreSQL schema."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.core.database.database import Base


def _utcnow():
    return datetime.utcnow()


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    """Maps to the live `users` table.

    Enum columns (role, status) are represented as String so SQLAlchemy
    does not attempt to recreate the PostgreSQL enum types on create_all.
    Valid role values : OWNER ADMIN ANALYST USER READONLY
    Valid status values: ACTIVE INACTIVE SUSPENDED LOCKED
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")

    # Enum-backed columns stored as plain strings in ORM layer
    role = Column(String(32), default="admin")
    status = Column(String(32), default="active")

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Mandatory FK — every user belongs to exactly one workspace
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)

    # GitHub OAuth
    github_id = Column(String(128), unique=True, nullable=True, index=True)
    github_username = Column(String(255), nullable=True)
    github_access_token = Column(String(512), nullable=True)

    # PGL Identity
    pgl_id = Column(String(36), unique=True, nullable=True, index=True)

    # MFA
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)
    mfa_recovery_codes_json = Column(Text, nullable=True)

    # Security tracking
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    ip_address = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    last_accessed = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="sessions")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), default="")
    name = Column(String(128), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(16), nullable=False)
    scopes = Column(Text, default="[]")
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="api_keys")
