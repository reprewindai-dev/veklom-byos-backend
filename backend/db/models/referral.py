"""Referral system models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    status = Column(String(32), default="active")  # active, disabled, expired
    reward_type = Column(String(32), default="percentage")  # percentage, fixed, credits
    reward_value = Column(Float, default=10.0)  # 10% or $10
    max_uses = Column(Integer, default=100)
    current_uses = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    user = relationship("User", back_populates="referral_codes")
    referrals = relationship("Referral", back_populates="referral_code")


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(String(36), primary_key=True, default=_uuid)
    referral_code_id = Column(String(36), ForeignKey("referral_codes.id"), nullable=False, index=True)
    referrer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)  # User who made the referral
    referred_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)  # User who was referred
    status = Column(String(32), default="pending")  # pending, completed, expired, cancelled
    reward_amount = Column(Float, default=0.0)
    reward_currency = Column(String(8), default="USD")
    reward_paid = Column(Boolean, default=False)
    reward_paid_at = Column(DateTime(timezone=True), nullable=True)
    conversion_event = Column(String(64), default="signup")  # signup, first_purchase, subscription
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    referral_code = relationship("ReferralCode", back_populates="referrals")
    referrer = relationship("User", foreign_keys=[referrer_id])
    referred = relationship("User", foreign_keys=[referred_id])


class ReferralPayout(Base):
    __tablename__ = "referral_payouts"

    id = Column(String(36), primary_key=True, default=_uuid)
    referral_id = Column(String(36), ForeignKey("referrals.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)  # User receiving payout
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    status = Column(String(32), default="pending")  # pending, processed, failed
    payment_method = Column(String(32), default="wallet")  # wallet, bank, stripe
    reference_id = Column(String(128), default="")  # Transaction reference
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    referral = relationship("Referral")
    user = relationship("User")
