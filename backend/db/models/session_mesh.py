"""PostgreSQL models for Global Enforcer Mesh & Session Layer."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean, JSON, ForeignKey, Text
from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class VeklomAgentSession(Base):
    """Sovereign enforcer session state."""
    __tablename__ = "veklom_agent_sessions"

    session_id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    agent_id = Column(String(128), index=True)
    agent_name = Column(String(128))
    model = Column(String(128))
    transport = Column(String(64))
    credentials_ref = Column(String(128))
    owner = Column(String(128))
    policy_id = Column(String(128), index=True)
    status = Column(String(32), default="active", index=True)
    cost_usd = Column(Float, default=0.0)
    max_cost_usd = Column(Float, default=10.0)
    rules = Column(JSON, default=list)
    require_approval = Column(JSON, default=list)
    deny = Column(JSON, default=list)
    jurisdiction = Column(String(128), default="GLOBAL")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class VeklomSessionTransition(Base):
    """Cryptographically chained log of actions & transitions within an enforcer session."""
    __tablename__ = "veklom_session_transitions"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("veklom_agent_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)
    action_type = Column(String(64), nullable=False)
    action_data = Column(JSON, default=dict)
    allowed = Column(Boolean, nullable=False)
    new_status = Column(String(32), nullable=False)
    prev_hash = Column(String(128), nullable=False)
    entry_hash = Column(String(128), nullable=False)
    signature = Column(String(256), nullable=False)


class VeklomMeshIncident(Base):
    """Asymmetrically signed mesh enforcer incident."""
    __tablename__ = "veklom_mesh_incidents"

    incident_id = Column(String(36), primary_key=True, default=_uuid)
    source_zone = Column(String(64), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    agent_id = Column(String(128), nullable=False, index=True)
    rule_id = Column(String(128), nullable=False)
    intervention = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)
    pattern = Column(String(128), nullable=False, index=True)
    context = Column(JSON, default=dict)
    timestamp = Column(Float, nullable=False)
    signature = Column(String(256), nullable=False)


class VeklomLedgerEntry(Base):
    """Global federated, append-only, chained audit ledger entry."""
    __tablename__ = "veklom_ledger_entries"

    seq = Column(Integer, primary_key=True)
    incident_id = Column(String(36), nullable=False, index=True)
    source_zone = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(128), nullable=False, index=True)
    pattern = Column(String(128), nullable=False, index=True)
    severity = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)
    timestamp = Column(Float, nullable=False)
    prev_hash = Column(String(128), nullable=False)
    entry_hash = Column(String(128), nullable=False)
