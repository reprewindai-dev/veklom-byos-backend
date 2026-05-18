"""Marketplace, pipeline, deployment models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id = Column(String(36), primary_key=True, default=_uuid)
    vendor_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="")
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    category = Column(String(64), default="tool")
    price = Column(Float, default=0.0)
    pricing_model = Column(String(32), default="per_use")
    icon_url = Column(String(512), default="")
    status = Column(String(32), default="draft")
    tags = Column(JSON, default=list)
    config_json = Column(JSON, default=dict)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    steps = Column(JSON, default=list)
    config_json = Column(JSON, default=dict)
    status = Column(String(32), default="draft")
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(String(36), primary_key=True, default=_uuid)
    pipeline_id = Column(String(36), nullable=False, index=True)
    status = Column(String(32), default="running")
    progress = Column(Float, default=0.0)
    current_step = Column(String(128), default="")
    output = Column(JSON, default=dict)
    error = Column(Text, default="")
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    deployment_type = Column(String(64), default="private")
    endpoint_url = Column(String(512), default="")
    status = Column(String(32), default="pending")
    config_json = Column(JSON, default=dict)
    health_status = Column(String(32), default="unknown")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    business_name = Column(String(255), default="")
    stripe_account_id = Column(String(255), default="")
    status = Column(String(32), default="pending")
    onboarding_complete = Column(Boolean, default=False)
    total_revenue = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
