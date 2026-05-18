"""User and auth models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from backend.core.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    role = Column(String(32), default="user")
    status = Column(String(32), default="active")
    avatar_url = Column(String(512), default="")
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), default="")
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    workspace_id = Column(String(36), default="")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

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
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_accessed = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="sessions")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), default="")
    name = Column(String(128), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(16), nullable=False)
    scopes = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="api_keys")
