from datetime import datetime, timezone
from sqlalchemy import (
    Column, DateTime, Float, Integer, String, BigInteger, Numeric, Index, UniqueConstraint
)
from backend.core.database.database import Base
from backend.db.models.user import _utcnow

class Payment(Base):
    __tablename__ = "banker_payments"

    id                  = Column(BigInteger, primary_key=True, autoincrement=True)
    payment_object_type = Column(String(64), nullable=False)
    payment_object_id   = Column(BigInteger, nullable=False)
    
    from_address        = Column(String(42), nullable=False)
    to_address          = Column(String(42), nullable=False)
    
    asset               = Column(String(16), nullable=False)
    amount              = Column(Numeric(38, 18), nullable=False)
    
    tx_hash             = Column(String(66), nullable=True, index=True)
    chain_id            = Column(BigInteger, nullable=True)
    block_number        = Column(BigInteger, nullable=True)
    gas_used            = Column(BigInteger, nullable=True)
    settled_at          = Column(DateTime(timezone=True), nullable=True)
    
    status              = Column(String(32), nullable=False, default='pending')

    created_at          = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("payment_object_type", "payment_object_id", name="uq_banker_payment_object"),
        Index("ix_banker_payments_from_status", "from_address", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_object_type": self.payment_object_type,
            "payment_object_id": self.payment_object_id,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "asset": self.asset,
            "amount": float(self.amount),
            "tx_hash": self.tx_hash,
            "chain_id": self.chain_id,
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
