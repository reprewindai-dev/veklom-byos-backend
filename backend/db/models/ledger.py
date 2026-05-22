from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base


class LedgerEvent(Base):
    """Tamper-evident, append-only event log for a governed agent.

    Chain integrity: each row stores the hash of the previous event
    (prev_event_hash) plus a hash of its own content (event_hash).  The
    Ledger worker validates the chain on every scheduled run via
    POST /audit/verify/{id}.

    Veto condition that fires if chain breaks: regulatory_breach.
    """

    __tablename__ = "ledger_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prev_event_hash: Mapped[str | None] = mapped_column(String(128))
    event_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="ledger_events")  # noqa: F821
