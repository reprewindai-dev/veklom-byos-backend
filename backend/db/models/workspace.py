"""Workspace / tenant models — aligned to the live PostgreSQL schema."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class Workspace(Base):
    """Maps to the live `workspaces` table."""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # License fields
    license_key_id = Column(String(128), nullable=True)
    license_key_prefix = Column(String(32), nullable=True)
    license_tier = Column(String(64), nullable=True)
    license_issued_at = Column(DateTime, nullable=True)
    license_expires_at = Column(DateTime, nullable=True)
    license_download_url = Column(String(512), nullable=True)

    # Configuration
    industry = Column(String(128), nullable=False, default="generic")
    playground_profile = Column(String(128), nullable=False, default="standard")
    risk_tier = Column(String(64), nullable=False, default="generic")
    default_policy_pack = Column(String(128), nullable=True)
    default_demo_scenarios = Column(Text, nullable=True)
    default_evidence_requirements = Column(Text, nullable=True)
    default_blocking_rules = Column(Text, nullable=True)

    plugins = relationship("WorkspacePlugin", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    role = Column(String(32), default="member")
    invited_by = Column(String(36), default="")
    joined_at = Column(DateTime, default=_utcnow)


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    provider = Column(String(64), nullable=False)
    model_name = Column(String(128), nullable=False)
    display_name = Column(String(255), default="")
    is_enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")
    cost_per_1k_input = Column(String(32), default="0.0")
    cost_per_1k_output = Column(String(32), default="0.0")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
