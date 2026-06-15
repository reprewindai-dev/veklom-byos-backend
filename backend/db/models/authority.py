"""Authority models for Veklom Runtime Authority Pack."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class AuthorityBundle(Base):
    """Immutable authority bundle defining tool permissions and constraints."""
    
    __tablename__ = "authority_bundles"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    version = Column(String(32), nullable=False, default="1.0")
    workspace_id = Column(String(36), nullable=False, index=True)
    creator_id = Column(String(36), nullable=False, index=True)
    
    # Authority configuration
    tool_permissions = Column(JSON, default=dict)
    workspace_restrictions = Column(JSON, default=dict)
    time_restrictions = Column(JSON, default=dict)
    risk_level = Column(String(32), default="medium")
    
    # Metadata
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    
    # Audit fields
    hash_chain = Column(String(128), default="")
    prev_hash = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AuthorityRun(Base):
    """Authority execution run tracking all decisions and evidence."""
    
    __tablename__ = "authority_runs"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    authority_bundle_id = Column(String(36), ForeignKey("authority_bundles.id"), nullable=False)
    agent_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), nullable=False, index=True)
    executor_id = Column(String(36), nullable=False, index=True)
    
    # Run state
    status = Column(String(32), default="active")  # active, completed, failed, revoked
    start_time = Column(DateTime(timezone=True), default=_utcnow)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Decision tracking
    decisions = Column(JSON, default=list)  # List of authority decisions
    violations = Column(JSON, default=list)  # List of violations detected
    approvals = Column(JSON, default=list)  # List of approved actions
    
    # SEKED Integration
    seked_state_id = Column(String(36), nullable=True)  # Reference to SEKED state for this run
    seked_policy_applied = Column(String(36), nullable=True)  # SEKED policy that governed this run
    seked_initial_measurement = Column(JSON, default=dict)  # Initial SEKED measurement for run
    seked_final_directive = Column(JSON, default=dict)  # Final SEKED directive for run
    
    # Evidence linking
    evidence_pack_id = Column(String(36), nullable=True)
    memory_entries = Column(JSON, default=list)  # Memory entry IDs for this run
    
    # Metrics
    total_actions = Column(Integer, default=0)
    approved_actions = Column(Integer, default=0)
    denied_actions = Column(Integer, default=0)
    violation_count = Column(Integer, default=0)
    
    # Audit fields
    hash_chain = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    authority_bundle = relationship("AuthorityBundle", backref="runs")


class AuthorityDecision(Base):
    """Individual authority decision for a tool call."""
    
    __tablename__ = "authority_decisions"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    authority_run_id = Column(String(36), ForeignKey("authority_runs.id"), nullable=False)
    tool_name = Column(String(128), nullable=False)
    tool_parameters = Column(JSON, default=dict)
    
    # Decision
    decision = Column(String(32), nullable=False)  # approve, deny, escalate
    reason = Column(Text, default="")
    confidence_score = Column(Float, default=1.0)
    
    # SEKED Integration
    seked_measurement = Column(JSON, default=dict)  # {E, R, C, D, S, timestamp}
    seked_ratios = Column(JSON, default=dict)  # {sigma, ci, si}
    seked_directive = Column(JSON, default=dict)  # {ratio, directive, action_type, confidence, reasoning}
    seked_policy_id = Column(String(36), nullable=True)  # Reference to SEKED policy used
    seked_proof_id = Column(String(36), nullable=True)  # Reference to SEKED proof
    
    # Context
    agent_context = Column(JSON, default=dict)
    workspace_context = Column(JSON, default=dict)
    risk_assessment = Column(JSON, default=dict)
    
    # Timing
    decision_time = Column(DateTime(timezone=True), default=_utcnow)
    execution_time = Column(DateTime(timezone=True), nullable=True)
    
    # Evidence
    evidence_refs = Column(JSON, default=list)  # References to evidence artifacts
    
    # Audit fields
    hash_chain = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
