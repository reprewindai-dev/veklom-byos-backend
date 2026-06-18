"""GovernedRun — the CAPPO governed-run entity.

Forward-constructed from ``VeklomRun`` but owns the *pre-execution* lifecycle
rather than being a post-hoc projection. It carries the proven hash columns
as first-class typed JSON, the run state machine's current ``state``, the
governance context produced before execution, and the minted ``execution_identity``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GovernedRun(Base):
    __tablename__ = "governed_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String, index=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    delegation_depth: Mapped[int] = mapped_column(Integer, default=0)

    state: Mapped[str] = mapped_column(String)

    # Governance context (set by govern_run, never status-derived).
    governance_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_tier: Mapped[str | None] = mapped_column(String, nullable=True)

    # PGL linkage: {"ledger_event_id": ..., "agent_id": ..., "ubc_id": ..., "source": "gnomledger"}
    # UBC ID (Universal Blockchain Connection ID) is the tracking ID from GnomLedger
    pgl_identity: Mapped[dict] = mapped_column(JSON, default=dict)
    seked_state: Mapped[dict] = mapped_column(JSON, default=dict)
    v4_decision: Mapped[dict] = mapped_column(JSON, default=dict)

    # Canonical hashes referenced/produced by the run.
    hashes: Mapped[dict] = mapped_column(JSON, default=dict)

    # Budget / scope context.
    approved_budget_cents: Mapped[int] = mapped_column(Integer, default=0)
    reserve_cents: Mapped[int] = mapped_column(Integer, default=0)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)

    # The minted ExecutionIdentityV1 object carried through routing/execution.
    execution_identity: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # The minted Execution Authorization Token (EAT) — authorization to execute.
    eat: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
