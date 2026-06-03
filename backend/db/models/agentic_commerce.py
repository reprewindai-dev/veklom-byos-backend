"""Agentic Commerce Protocol (ACP) persistence.

Stores agentic checkout sessions and the resulting orders created when an AI
agent buys a Veklom product on a buyer's behalf — across every revenue rail
(marketplace listings, governed x402 runs, subscriptions, reserve credits).
The full ACP CheckoutSession object is kept in `data_json` so the API can
return a spec-shaped response without re-deriving it on every read.
"""

from sqlalchemy import Column, DateTime, Integer, JSON, String

from backend.core.database.database import Base
from backend.db.models.user import _utcnow


class AgenticCheckoutSession(Base):
    __tablename__ = "agentic_checkout_sessions"

    id = Column(String(64), primary_key=True)  # acs_xxx
    workspace_id = Column(String(36), default="", index=True)
    buyer_email = Column(String(255), default="")
    agent_id = Column(String(128), default="")
    status = Column(String(40), default="not_ready_for_payment", index=True)
    currency = Column(String(8), default="usd")
    amount_total = Column(Integer, default=0)  # minor units (cents)
    payment_intent_id = Column(String(128), default="")
    order_id = Column(String(64), default="", index=True)
    data_json = Column(JSON, default=dict)  # full ACP CheckoutSession object
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
