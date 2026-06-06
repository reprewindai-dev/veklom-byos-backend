"""Agency / Memory layer — durable agent state, memory, and notifications.

This is the `MEMORY_SCHEMA` from the architecture research and the "Passport /
posture" concept from SYSTEM_MAP. It is the os_metadata + durable user_memory
that lets a governed agent actually be *run*: it has identity-state (rank,
privileges, posture), earned memory, and a persistent notification feed.

Complements (does NOT duplicate) `internal_operators.py` (operator-committee KV
memory/budgets) and the Redis 24h conversation buffer (hot cache). This is the
durable, cold tier.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


# Posture bands (from SYSTEM_MAP passport) and their execution consequence.
POSTURE_TRUSTED = "trusted"
POSTURE_CAUTIONED = "cautioned"
POSTURE_RESTRICTED = "restricted"
POSTURE_SUSPENDED = "suspended"


def compute_posture(violations: int, clean_streak: int, demotion_locked: bool) -> str:
    """Deterministic posture from behavior — the agent's earned trust band."""
    if demotion_locked or violations >= 5:
        return POSTURE_SUSPENDED
    if violations >= 3:
        return POSTURE_RESTRICTED
    if violations >= 1:
        return POSTURE_CAUTIONED
    return POSTURE_TRUSTED


def posture_allows_autonomy(band: str) -> bool:
    return band in (POSTURE_TRUSTED, POSTURE_CAUTIONED)


class AgentState(Base):
    """os_metadata: protected, governed identity-state for a runnable agent.

    One row per (workspace_id, agent_id). Rank/privileges/posture decide what the
    agent is allowed to do; demotion_lock forbids autonomous execution.
    """

    __tablename__ = "agent_states"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False, index=True)
    codename = Column(String(128), default="")
    rank = Column(String(32), default="recruit", index=True)   # recruit|operator|senior|elite|council
    memory_tokens = Column(Integer, default=0)                 # earned durable-memory budget
    privileges = Column(JSON, default=list)                    # granted capability ids
    violations = Column(Integer, default=0)
    clean_streak = Column(Integer, default=0)
    demotion_locked = Column(Boolean, default=False)
    posture_band = Column(String(32), default=POSTURE_TRUSTED, index=True)
    execution_eligible = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def recompute(self) -> None:
        self.posture_band = compute_posture(self.violations, self.clean_streak, self.demotion_locked)
        self.execution_eligible = posture_allows_autonomy(self.posture_band)


class AgentMemoryEntry(Base):
    """Durable user_memory: distilled, long-lived agent memory (vs the 24h Redis buffer)."""

    __tablename__ = "agent_memory_entries"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(32), default="note", index=True)   # note|lesson|decision|fact
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5)                  # 0..1, for curation/eviction
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class Notification(Base):
    """Durable operator notification / alarm (replaces the in-memory _alerts dict).

    The agency feed: milestones, signals, escalations, and alarms that must
    survive a restart. Severity drives UI prominence; `requires_action` flags the
    human-in-the-loop items.
    """

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(48), default="signal", index=True)   # signal|alarm|milestone|escalation
    severity = Column(String(16), default="info", index=True)  # info|warning|critical
    title = Column(String(256), nullable=False)
    message = Column(Text, default="")
    source = Column(String(64), default="system")              # which subsystem raised it
    agent_id = Column(String(64), nullable=True, index=True)
    requires_action = Column(Boolean, default=False)
    read = Column(Boolean, default=False, index=True)
    resolved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
