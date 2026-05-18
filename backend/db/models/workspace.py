"""Workspace / tenant models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, JSON, Text, Integer, Float

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(128), unique=True, nullable=False)
    owner_id = Column(String(36), nullable=False, index=True)
    plan = Column(String(64), default="free_evaluation")
    settings_json = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    role = Column(String(32), default="member")
    invited_by = Column(String(36), default="")
    joined_at = Column(DateTime(timezone=True), default=_utcnow)


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    provider = Column(String(64), nullable=False)
    model_name = Column(String(128), nullable=False)
    display_name = Column(String(255), default="")
    is_enabled = Column(Boolean, default=True)
    config_json = Column(JSON, default=dict)
    cost_per_1k_input = Column(Float, default=0.0)
    cost_per_1k_output = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
