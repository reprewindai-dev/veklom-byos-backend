"""Billing, wallet, subscription models."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, JSON, Boolean

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="", index=True)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, default=0.0)
    tx_type = Column(String(32), nullable=False)  # credit, debit, topup, refund
    description = Column(String(512), default="")
    reference_id = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="", index=True)
    plan = Column(String(64), nullable=False)
    stripe_subscription_id = Column(String(255), default="")
    stripe_customer_id = Column(String(255), default="")
    status = Column(String(32), default="active")
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    activation_fee_paid = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class BudgetRule(Base):
    __tablename__ = "budget_rules"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    rule_type = Column(String(32), default="hard")  # hard, soft
    limit_usd = Column(Float, nullable=False)
    period = Column(String(32), default="monthly")
    current_spend = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="")
    stripe_invoice_id = Column(String(255), default="")
    amount = Column(Float, default=0.0)
    status = Column(String(32), default="pending")
    description = Column(String(512), default="")
    pdf_url = Column(String(512), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class Payment(Base):
    """Server-side payment tracking for on-chain transactions."""
    __tablename__ = "payments"

    order_id = Column(String(64), primary_key=True, nullable=False)
    user_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash for distinctId
    user_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="", index=True)
    expected_amount = Column(Float, nullable=False)  # in token units
    token_contract = Column(String(64), nullable=False)
    chain_id = Column(Integer, nullable=False)
    status = Column(String(32), default="pending")  # pending|confirmed|failed|expired
    tx_hash = Column(String(128), nullable=True)
    confirmations = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
