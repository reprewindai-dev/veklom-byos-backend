"""Security, audit, compliance models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), default="", index=True)
    workspace_id = Column(String(36), default="", index=True)
    action = Column(String(128), nullable=False)
    resource_type = Column(String(64), default="")
    resource_id = Column(String(36), default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    hash_chain = Column(String(128), default="")
    prev_hash = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), default="", index=True)
    workspace_id = Column(String(36), default="", index=True)
    event_type = Column(String(64), nullable=False)
    threat_type = Column(String(64), default="")
    severity = Column(String(32), default="low")
    description = Column(Text, default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String(64), default="")
    status = Column(String(32), default="open")
    resolution = Column(Text, default="")
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), default="", index=True)
    regulation = Column(String(64), nullable=False)
    content_hash = Column(String(128), default="")
    result = Column(String(32), default="pass")
    findings = Column(JSON, default=list)
    score = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class KillSwitchState(Base):
    __tablename__ = "kill_switch_states"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), default="", index=True)
    is_active = Column(Boolean, default=False)
    activated_by = Column(String(36), default="")
    reason = Column(Text, default="")
    activated_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
