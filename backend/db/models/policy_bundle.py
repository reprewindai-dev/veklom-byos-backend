"""Policy Versioning and Enforcement Bundle models for PGL Policy Registry."""

from sqlalchemy import Boolean, Column, DateTime, JSON, String
from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class PolicyVersion(Base):
    """Stores versioned policy definitions and their approval/active states."""

    __tablename__ = "policy_versions"

    id = Column(String(36), primary_key=True, default=_uuid)
    version = Column(String(32), nullable=False, unique=True, index=True)
    policies = Column(JSON, nullable=False, default=dict)
    approved_by = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class EnforcementBundle(Base):
    """Represents compiled, validated enforcement configuration linking policies and constitution."""

    __tablename__ = "enforcement_bundles"

    id = Column(String(36), primary_key=True, default=_uuid)
    policy_version = Column(String(32), nullable=False)
    constitution_version = Column(String(32), nullable=False)
    bundle_hash = Column(String(128), nullable=False, unique=True, index=True)
    regression_passed = Column(Boolean, default=True)
    compiled_at = Column(DateTime(timezone=True), default=_utcnow)
