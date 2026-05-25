"""Repo Risk Gate models.

Stores governed repo-review runs and the immutable event chain that drives
the Playground tool.  Every event is signed into a SHA-256 hash chain so
the ledger endpoint can return verifiable evidence.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class RepoRiskGateRun(Base):
    __tablename__ = "repo_risk_gate_runs"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), default="", index=True)
    user_id = Column(String(36), default="", index=True)
    repo_url = Column(String(512), nullable=False)
    repo_owner = Column(String(255), default="")
    repo_name = Column(String(255), default="")
    status = Column(String(32), default="created", index=True)
    decision = Column(String(32), default="", index=True)
    decision_reason = Column(Text, default="")
    decision_user_id = Column(String(36), default="")
    findings_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, default=dict)


class RepoRiskGateEvent(Base):
    __tablename__ = "repo_risk_gate_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    run_id = Column(String(36), ForeignKey("repo_risk_gate_runs.id"), index=True, nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(64), default="system")
    actor_id = Column(String(36), default="")
    payload = Column(JSON, default=dict)
    prev_hash = Column(String(64), default="")
    event_hash = Column(String(64), default="", index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
