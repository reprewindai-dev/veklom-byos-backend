"""Benchmark API Trust Leaderboard & Staking Prediction Market models."""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSON

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class BenchmarkAPI(Base):
    """Tracked API in the Trust Leaderboard."""
    __tablename__ = "benchmark_apis"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(64), default="payments")
    sovereign_tier = Column(String(32), default="Tier-1")
    sla_success = Column(Float, default=99.9)
    p50_latency = Column(Float, default=45.0)
    p95_latency = Column(Float, default=120.0)
    p99_latency = Column(Float, default=250.0)
    drift_index = Column(Float, default=0.02)
    endpoint_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    mcp_schema = Column(JSON, nullable=True)
    provider = Column(String(255), nullable=True)
    throughput = Column(Integer, default=0)
    uptime_24h = Column(Float, default=100.0)
    total_staked = Column(Float, default=0.0)
    status = Column(String(32), default="excellent")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class StakingMarket(Base):
    """Polymarket-style prediction pool on API SLA outcomes."""
    __tablename__ = "staking_markets"

    id = Column(String(36), primary_key=True, default=_uuid)
    api_id = Column(String(36), nullable=False, index=True)
    question = Column(String(512), nullable=False)
    yes_price = Column(Integer, default=65)
    no_price = Column(Integer, default=35)
    volume = Column(Float, default=0.0)
    total_pool = Column(Float, default=0.0)
    resolution_date = Column(String(32), default="")
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class UserStake(Base):
    """Individual YES/NO staking transaction."""
    __tablename__ = "user_stakes"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    market_id = Column(String(36), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # YES / NO
    amount = Column(Float, nullable=False)
    price_at_stake = Column(Integer, default=50)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class SyntheticProbeLog(Base):
    """Chronological log of synthetic observability checks."""
    __tablename__ = "synthetic_probe_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    api_id = Column(String(36), nullable=False, index=True)
    probe_type = Column(String(64), default="latency_check")
    result = Column(String(32), default="pass")
    latency_ms = Column(Float, default=0.0)
    details = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
