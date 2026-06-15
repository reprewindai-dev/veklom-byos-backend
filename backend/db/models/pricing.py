"""Pricing tier system models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class PricingTier(Base):
    __tablename__ = "pricing_tiers"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    tier_level = Column(Integer, nullable=False, unique=True)  # 1=Basic, 2=Pro, 3=Enterprise, etc.
    monthly_price = Column(Float, nullable=False)
    annual_price = Column(Float, nullable=True)
    currency = Column(String(8), default="USD")
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)
    features = Column(JSON, default=dict)  # List of included features
    limits = Column(JSON, default=dict)  # Usage limits
    tier_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="pricing_tier")
    tier_upgrades = relationship("TierUpgrade", foreign_keys="[TierUpgrade.to_tier_id]", back_populates="target_tier")


class TierFeature(Base):
    __tablename__ = "tier_features"

    id = Column(String(36), primary_key=True, default=_uuid)
    tier_id = Column(String(36), ForeignKey("pricing_tiers.id"), nullable=False, index=True)
    feature_name = Column(String(128), nullable=False)
    feature_type = Column(String(64), default="boolean")  # boolean, number, text, list
    feature_value = Column(JSON, default=True)  # The actual feature value
    description = Column(Text, default="")
    is_included = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    
    # Relationships
    pricing_tier = relationship("PricingTier")


class TierUpgrade(Base):
    __tablename__ = "tier_upgrades"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    from_tier_id = Column(String(36), ForeignKey("pricing_tiers.id"), nullable=True, index=True)
    to_tier_id = Column(String(36), ForeignKey("pricing_tiers.id"), nullable=False, index=True)
    status = Column(String(32), default="pending")  # pending, completed, failed, cancelled
    upgrade_type = Column(String(32), default="immediate")  # immediate, scheduled, at_billing_cycle
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(String(64), default="stripe")  # stripe, wallet, invoice
    prorated_amount = Column(Float, default=0.0)
    currency = Column(String(8), default="USD")
    stripe_subscription_id = Column(String(255), nullable=True)
    tier_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    target_tier = relationship("PricingTier", foreign_keys=[to_tier_id], back_populates="tier_upgrades")
    from_tier = relationship("PricingTier", foreign_keys=[from_tier_id])


class UsageMetric(Base):
    __tablename__ = "usage_metrics"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    metric_name = Column(String(128), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(32), default="count")  # count, requests, storage, users, etc.
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    tier_limit = Column(Float, nullable=True)  # The limit for the current tier
    usage_percentage = Column(Float, default=0.0)  # Percentage of limit used
    tier_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    
    # Create composite index
    __table_args__ = (
        Index('idx_usage_workspace_metric_period', 'workspace_id', 'metric_name', 'period_start', 'period_end'),
    )


class BillingEvent(Base):
    __tablename__ = "pricing_billing_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)  # subscription_created, payment_failed, limit_exceeded, etc.
    event_data = Column(JSON, default=dict)
    amount = Column(Float, nullable=True)
    currency = Column(String(8), default="USD")
    status = Column(String(32), default="pending")  # pending, processed, failed
    processed_at = Column(DateTime(timezone=True), nullable=True)
    tier_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    
    # Create composite index
    __table_args__ = (
        Index('idx_billing_workspace_type_time', 'workspace_id', 'event_type', 'created_at'),
    )
