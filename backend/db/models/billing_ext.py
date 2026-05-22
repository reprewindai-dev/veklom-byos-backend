from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base


class BillingUsage(Base):
    """Metered usage record per account per billing period.

    The Mint worker reads these rows when translating demand and workflow
    pressure into monetization recommendations.  The metric column uses
    free-form strings (e.g. 'llm_tokens', 'agent_runs', 'storage_gb').
    """

    __tablename__ = "billing_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["Account"] = relationship()  # noqa: F821


class BillingEvent(Base):
    """Raw inbound Stripe webhook event store.

    Idempotency key: stripe_event_id (unique).  The billing router
    de-dupes on this column before processing any webhook.
    """

    __tablename__ = "billing_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stripe_event_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalyticsEvent(Base):
    """Lightweight funnel and product analytics event stream.

    account_id is nullable to support pre-auth / anonymous events (e.g.
    landing-page visits tracked by the Welcome worker before signup).
    """

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["Account | None"] = relationship()  # noqa: F821
