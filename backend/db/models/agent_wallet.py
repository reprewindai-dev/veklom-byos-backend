"""
Agent Wallet Ledger — Immutable on-chain spend record for the Banker Agent.

Every USDC transfer executed autonomously by BankerAgentService is persisted
here before broadcast and updated with on-chain confirmation data.
This table is append-only: records are never deleted or updated after 'confirmed'.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Text, Index
)
from backend.core.database.database import Base
from backend.db.models.user import _uuid, _utcnow


class AgentWalletLedger(Base):
    """
    Immutable ledger of every on-chain payment made by the Banker Agent.

    Lifecycle: pending → confirmed | failed
    Records in 'confirmed' state must never be modified.
    """
    __tablename__ = "agent_wallet_ledger"

    id              = Column(String(36),  primary_key=True, default=_uuid)

    # On-chain identity
    tx_hash         = Column(String(66),  unique=True, nullable=True, index=True)
    from_address    = Column(String(42),  nullable=False, index=True)
    to_address      = Column(String(42),  nullable=False)

    # Payment value
    amount_usdc     = Column(Float,       nullable=False)
    amount_micro    = Column(Integer,     nullable=False)   # amount_usdc * 1_000_000

    # Context: what was this payment for?
    route_paid_for  = Column(String(256), nullable=False)   # e.g. /api/v1/x402/score
    purpose         = Column(String(128), nullable=False, default="x402_payment")
    receipt_id      = Column(String(64),  nullable=True)    # linked x402 receipt

    # Settlement state
    status          = Column(String(32),  nullable=False, default="pending")
    # status values: pending | broadcast | confirmed | failed

    # On-chain confirmation data (populated after receipt is fetched)
    block_number    = Column(Integer,     nullable=True)
    gas_used        = Column(Integer,     nullable=True)
    confirmed_at    = Column(DateTime(timezone=True), nullable=True)

    # Error detail if status=failed
    error_detail    = Column(Text,        nullable=True)

    # Audit timestamps
    created_at      = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_awl_from_status", "from_address", "status"),
        Index("ix_awl_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "tx_hash":      self.tx_hash,
            "from_address": self.from_address,
            "to_address":   self.to_address,
            "amount_usdc":  self.amount_usdc,
            "route_paid_for": self.route_paid_for,
            "purpose":      self.purpose,
            "receipt_id":   self.receipt_id,
            "status":       self.status,
            "block_number": self.block_number,
            "gas_used":     self.gas_used,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "error_detail": self.error_detail,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }
