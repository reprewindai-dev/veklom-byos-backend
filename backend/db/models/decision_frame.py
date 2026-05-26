"""
Decision Frame — the core governed-execution proof object.

Every governed run (GPC compile, pipeline trigger, agent action, AI inference
with policy) SHOULD create a Decision Frame. This is the "show us" artifact:
a machine-readable record of what the model saw, what policy checked, and
what happened — sufficient to reconstruct and audit the decision later.

Decision Frames power: GPC, Pipelines, Compliance, Monitoring, Archives,
Command Center, and the 30-day proof dashboard.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from backend.core.database.database import Base


class DecisionFrame(Base):
    __tablename__ = "decision_frames"

    id              = Column(String, primary_key=True, default=lambda: f"df_{uuid.uuid4().hex[:20]}")
    workspace_id    = Column(String, index=True, nullable=False)

    # Actor
    actor_user_id   = Column(String, index=True)
    actor_type      = Column(String, default="user")          # user | agent | system | api
    actor_name      = Column(String)

    # Objective & classification
    objective       = Column(Text)                             # high-level intent string
    input_classification = Column(String, default="unclassified")  # public | internal | confidential | phi | pii
    risk_tier       = Column(String, default="standard")       # low | standard | high | critical

    # Execution
    model           = Column(String)
    provider        = Column(String)
    policy_pack     = Column(String, default="outbound.public.v3")
    tool_calls      = Column(JSONB, default=list)
    retrieved_context = Column(JSONB, default=dict)
    plan_id         = Column(String, index=True)
    run_id          = Column(String, index=True)
    pipeline_id     = Column(String, index=True)

    # Economics
    cost_estimate_usd   = Column(Float, default=0.0)
    actual_cost_usd     = Column(Float, default=0.0)
    tokens_used         = Column(Float, default=0)

    # Governance gates
    approval_required   = Column(Boolean, default=False)
    approval_status     = Column(String, default="not_required")  # not_required | pending | approved | denied
    approved_by         = Column(String)
    evidence_required   = Column(Boolean, default=True)

    # Outcome
    final_action        = Column(String, default="pending")    # pending | executed | blocked | escalated | cancelled
    policy_result       = Column(String, default="pending")    # passed | failed | blocked | escalated
    block_reason        = Column(Text)

    # Proof
    proof_hash          = Column(String)                       # SHA-256 of (objective + output + timestamp)
    evidence_id         = Column(String, index=True)           # links to AuditLog / evidence export
    replay_status       = Column(String, default="replayable") # replayable | partial | not_replayable
    replay_inputs       = Column(JSONB, default=dict)          # all inputs needed for replay

    # Metadata
    tags                = Column(JSONB, default=list)
    source              = Column(String, default="api")        # api | workspace | agent | pipeline
    created_at          = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at          = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
