from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Enum as SQLEnum, BigInteger, CheckConstraint, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value

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
    
    # Enhanced governance columns from migration 002
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    constitution_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    override_applied: Mapped[bool] = mapped_column(nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    genome_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="ledger_events")  # noqa: F821


class SettlementState(str, enum.Enum):
    quoted = "quoted"
    locked = "locked"
    released = "released"
    rejected = "rejected"
    failed = "failed"
    debt_pending = "debt_pending"
    refunded = "refunded"


class SettlementLedger(Base):
    __tablename__ = "settlement_ledger"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)

    payer_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    payee_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)

    asc_channel_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    protected_route: Mapped[str] = mapped_column(String(255), nullable=False)
    service_name: Mapped[str] = mapped_column(String(128), nullable=False)

    currency_code: Mapped[str] = mapped_column(String(16), nullable=False, default="USDC")
    network_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    quoted_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    locked_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    released_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    payment_proof_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    execution_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    settlement_state: Mapped[SettlementState] = mapped_column(
        SQLEnum(SettlementState, name="settlement_state_enum"),
        nullable=False,
        default=SettlementState.locked,
        index=True,
    )

    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "dedupe_key", name="uq_settlement_ledger_tenant_dedupe_key"),
        UniqueConstraint("execution_hash", name="uq_settlement_ledger_execution_hash"),
        CheckConstraint("quoted_amount_minor >= 0", name="ck_settlement_quoted_nonnegative"),
        CheckConstraint("locked_amount_minor >= 0", name="ck_settlement_locked_nonnegative"),
        CheckConstraint("released_amount_minor >= 0", name="ck_settlement_released_nonnegative"),
        CheckConstraint(
            "released_amount_minor <= locked_amount_minor",
            name="ck_settlement_released_lte_locked",
        ),
        Index("ix_settlement_tenant_state_created", "tenant_id", "settlement_state", "created_at"),
        Index("ix_settlement_payer_state_created", "payer_id", "settlement_state", "created_at"),
        Index("ix_settlement_payee_state_created", "payee_id", "settlement_state", "created_at"),
        Index("ix_settlement_route_created", "protected_route", "created_at"),
    )
