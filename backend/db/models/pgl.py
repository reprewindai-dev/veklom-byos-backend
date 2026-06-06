"""PGL (Provenance / Genome Ledger) persistence — the identity substrate.

This backs the keystone invariant: *no governed action executes anonymously*.
Every `commit_intent` / `attest_outcome` / `register_rollback` from the
orchestrator writes a real, SHA-256 hash-chained event here instead of returning
a throwaway UUID.

Unlike `LedgerEvent` (which is FK-bound to `agents.id`), this ledger is keyed by
workspace_id + actor_id (strings) so it can record provenance for ANY governed
moving part — VeklomRuns, agents, deployments, pipeline runs — not only registered
Agent rows.  That is exactly the "PGL for every moving part" requirement.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, JSON, String

from backend.core.database.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PGLCertificate(Base):
    """A pre- or post-execution certificate issued by the PGL ledger."""

    __tablename__ = "pgl_certificates"

    certificate_id = Column(String(64), primary_key=True)
    kind = Column(String(16), nullable=False, index=True)        # 'pre' | 'post'
    workspace_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False, index=True)
    genome_hash = Column(String(128), nullable=True)
    constitution_hash = Column(String(128), nullable=True)
    plan_hash = Column(String(128), nullable=True)
    output_hash = Column(String(128), nullable=True)
    outcome_hash = Column(String(128), nullable=True)
    pre_certificate_id = Column(String(64), nullable=True, index=True)  # post -> pre link
    status = Column(String(32), nullable=False, default="committed")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class PGLLedgerEvent(Base):
    """Hash-chained provenance event.

    The chain is per (workspace_id): each new event's `event_hash` is
    SHA-256 over its canonical payload + `prev_event_hash`, so any auditor can
    replay and verify integrity.  A broken link is a regulatory-breach signal.
    """

    __tablename__ = "pgl_ledger_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False, index=True)
    certificate_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)   # commit_intent | attest_outcome | rollback
    payload = Column(JSON, nullable=False, default=dict)
    prev_event_hash = Column(String(128), nullable=True)
    event_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
