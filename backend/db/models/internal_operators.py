"""Database models for Veklom Governed Operator Committees and Sub-Agents."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class InternalOperatorTask(Base):
    __tablename__ = "internal_operator_tasks"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(64), nullable=False, index=True)
    committee = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, default="")
    status = Column(String(32), default="pending", index=True)  # pending, running, completed, failed, blocked
    assigned_vertical = Column(String(64), default="generic")
    risk_level = Column(String(32), default="low")  # low, medium, high, critical
    cost_estimate_usd = Column(Float, default=0.0)
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class InternalOperatorSchedule(Base):
    __tablename__ = "internal_operator_schedules"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(64), nullable=False, index=True, unique=True)
    cron_expression = Column(String(128), nullable=False)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_status = Column(String(32), default="unknown")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class InternalOperatorMemory(Base):
    __tablename__ = "internal_operator_memory"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(64), nullable=False, index=True)
    key = Column(String(256), nullable=False, index=True)
    value = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class InternalOperatorArtifact(Base):
    __tablename__ = "internal_operator_artifacts"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    name = Column(String(256), nullable=False)
    path = Column(String(512), default="")
    content_hash = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class InternalOperatorEscalation(Base):
    __tablename__ = "internal_operator_escalations"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(36), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    severity = Column(String(32), default="high")  # high, critical
    status = Column(String(32), default="pending", index=True)  # pending, reviewed, dismissed
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class InternalOperatorBudget(Base):
    __tablename__ = "internal_operator_budgets"

    worker_id = Column(String(64), primary_key=True)
    daily_cap_usd = Column(Float, default=0.0)
    daily_spent_usd = Column(Float, default=0.0)
    monthly_cap_usd = Column(Float, default=0.0)
    monthly_spent_usd = Column(Float, default=0.0)
    last_reset_at = Column(DateTime(timezone=True), default=_utcnow)


class InternalOperatorProviderUsage(Base):
    __tablename__ = "internal_operator_provider_usage"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(64), nullable=False, index=True)
    provider = Column(String(64), nullable=False, index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)


class InternalOperatorApproval(Base):
    __tablename__ = "internal_operator_approvals"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(36), nullable=False, index=True)
    request_type = Column(String(64), nullable=False)  # release_deploy, outbound_outreach, payment_settlement
    request_payload = Column(JSON, default=dict)
    status = Column(String(32), default="pending", index=True)  # pending, approved, rejected
    reviewer_id = Column(String(36), nullable=True)
    review_notes = Column(Text, default="")
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
