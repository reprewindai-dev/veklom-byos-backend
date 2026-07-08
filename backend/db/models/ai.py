"""AI execution models, aligned to BYOS AI User Manual and Production."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, JSON, Boolean, ForeignKey, Enum as SQLEnum, UniqueConstraint

from backend.core.database.database import Base
from backend.core.ml.tier_types import DataTier
from backend.db.models.user import _utcnow, _uuid

from sqlalchemy import Index
from sqlalchemy.ext.hybrid import hybrid_property

class ExecutionLog(Base):
    """every /v1/exec call: tenant, model, provider, tokens, latency"""
    __tablename__ = "execution_logs"
    __table_args__ = (
        Index("ix_exec_logs_workspace_provider", "workspace_id", "provider"),
        Index("ix_execution_logs_created_at", "created_at"),
        Index("ix_execution_logs_data_tier", "workspace_id", "data_tier"),
        Index("idx_exec_log_tier_created_at", "data_tier", "created_at"),
        Index("idx_exec_log_ws_tier_created", "workspace_id", "data_tier", "created_at"),
        Index("idx_exec_log_gold_training", "workspace_id", "data_tier", "eligible_for_training", "training_locked_at", "created_at"),
        Index("idx_exec_log_dedupe_key", "dedupe_key"),
        UniqueConstraint("workspace_id", "dedupe_key", name="uniq_ws_dedupe_key"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    evidence_pack_id = Column(String(36), index=True, nullable=True)
    model = Column(String(128), default="")
    provider = Column(String(64), default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(32), default="completed")
    content_safety_score = Column(Float, default=1.0)
    policy_id = Column(String(128), nullable=True, index=True)
    policy_flags = Column(JSON, default=list)
    request_hash = Column(String(128), default="")
    data_tier = Column(SQLEnum(DataTier, name="data_tier_enum", create_type=False), default=DataTier.unrated)
    confidence_score = Column(Float, default=0.0)
    
    # Multi-Factor Verification Columns
    tier_score = Column(Float, default=0.0)
    policy_passed = Column(Boolean, default=False)
    schema_passed = Column(Boolean, default=False)
    quality_passed = Column(Boolean, default=False)
    evidence_complete = Column(Boolean, default=False)
    runtime_error = Column(Boolean, default=False)
    security_anomaly = Column(Boolean, default=False)
    budget_exceeded = Column(Boolean, default=False)
    
    # Execution Routing / Diversity
    route_family = Column(String(128), nullable=True, index=True)
    
    # Lifecycle & Dedupe
    dedupe_key = Column(String(128), nullable=True)
    tier_reason_codes = Column(JSON, default=list)
    tiered_at = Column(DateTime(timezone=True), nullable=True)
    eligible_for_training = Column(Boolean, default=False)
    training_locked_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    @hybrid_property
    def total_tokens(self):
        return self.input_tokens + self.output_tokens

    @hybrid_property
    def cost_usd(self):
        return self.cost

class AIAuditLog(Base):
    """immutable HMAC-SHA256 records of every AI operation"""
    __tablename__ = "ai_audit_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    operation_type = Column(String(64), default="inference")
    provider = Column(String(64), default="")
    model = Column(String(128), default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    hmac_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class CostPrediction(Base):
    __tablename__ = "cost_predictions"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    predicted_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, nullable=True)
    error_percent = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class RoutingDecision(Base):
    __tablename__ = "routing_decisions"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    decision = Column(String(256), default="")
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    factors = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class CostAllocation(Base):
    __tablename__ = "cost_allocations"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    operation_id = Column(String(36), nullable=False)
    client_project = Column(String(128), nullable=False)
    allocated_cost = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    budget_type = Column(String(64), default="monthly")
    amount = Column(Float, default=0.0)
    current_spend = Column(Float, default=0.0)
    alert_thresholds = Column(JSON, default=list)
    alert_level = Column(String(32), default="ok")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class RoutingPolicy(Base):
    __tablename__ = "routing_policies"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    strategy = Column(String(64), default="cost_optimized")
    max_cost = Column(Float, default=0.0)
    min_quality = Column(Float, default=0.8)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class ContentFilterLog(Base):
    __tablename__ = "content_filter_logs"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    content_hash = Column(String(256), nullable=False)
    allowed = Column(Boolean, default=True)
    category = Column(String(64), default="safe")
    confidence = Column(Float, default=1.0)
    action = Column(String(64), default="allow")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class AgeVerification(Base):
    __tablename__ = "age_verifications"
    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    status = Column(String(32), default="pending")
    verification_method = Column(String(64), default="self_attestation")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class AbuseLog(Base):
    __tablename__ = "abuse_logs"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(128), default="")
    ip_address = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class IncidentLog(Base):
    __tablename__ = "incident_logs"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    severity = Column(String(32), default="WARNING")
    message = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class ForecastModel(Base):
    """Persisted spend-forecast model — the Insights/Forecast heart.

    One row per (workspace_id, model_type).  `params` holds the fitted
    EWMA + linear-trend coefficients so projections are reproducible and
    explainable rather than recomputed ad-hoc.  Trained by
    `backend.services.forecast.train_and_persist` over execution_logs.
    """

    __tablename__ = "forecast_models"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    model_type = Column(String(64), default="spend", index=True)
    method = Column(String(64), default="ewma_linear")
    params = Column(JSON, default=dict)
    samples_used = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)
    window_days = Column(Integer, default=30)
    version = Column(String(32), default="v1")
    trained_at = Column(DateTime(timezone=True), default=_utcnow)


# Alias to support both ExecutionLog (manual alignment) and ExecLog (production/legacy)
ExecLog = ExecutionLog


class ChainDefinition(Base):
    __tablename__ = "chain_definitions"
    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    model = Column(String(128), default="")
    tools = Column(JSON, default=list)
    requires_gpc = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class ChainRunRecord(Base):
    __tablename__ = "chain_run_records"
    id = Column(String(36), primary_key=True, default=_uuid)
    chain_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    input_hash = Column(String(256), nullable=False)
    output_hash = Column(String(256), nullable=True)
    model = Column(String(128), default="")
    tools_used = Column(JSON, default=list)
    tokens_used = Column(Integer, default=0)
    cost_cents = Column(Float, default=0.0)
    status = Column(String(32), default="running")
    error = Column(Text, nullable=True)
    audit_hash = Column(String(256), nullable=True)
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)

class ToolDefinition(Base):
    __tablename__ = "tool_definitions"
    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    version = Column(String(64), default="1.0.0")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
