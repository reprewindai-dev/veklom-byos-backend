"""SQLAlchemy models for the Veklom API Trust Leaderboard and SLA Staking Pit."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON
from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid

class BenchmarkAPI(Base):
    __tablename__ = "benchmark_apis"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    p50 = Column(Float, nullable=False)
    p95 = Column(Float, nullable=False)
    p99 = Column(Float, nullable=False)
    sla = Column(Float, nullable=False)
    drift = Column(Float, nullable=False)
    sovereign_tier = Column(Integer, nullable=False)
    compliance_labels = Column(JSON, default=list)
    gov_score = Column(Integer, nullable=False)
    dev_score = Column(Integer, nullable=False)
    endpoint_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    mcp_schema = Column(JSON, nullable=True)
    provider = Column(String(255), nullable=True)
    throughput = Column(Integer, default=0)
    uptime_24h = Column(Float, default=100.0)
    total_staked = Column(Float, default=0.0)
    status = Column(String(64), default="excellent")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

class StakingMarket(Base):
    __tablename__ = "staking_markets"

    id = Column(String(36), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    yes_price = Column(Integer, nullable=False, default=50) # price in cents
    no_price = Column(Integer, nullable=False, default=50) # price in cents
    volume = Column(Float, nullable=False, default=0.0) # in $VEK
    pool_yes = Column(Float, nullable=False, default=0.0)
    pool_no = Column(Float, nullable=False, default=0.0)
    resolution_date = Column(String(128), nullable=False)
    target_api = Column(String(255), nullable=False)
    resolved = Column(Boolean, default=False)
    outcome = Column(String(16), nullable=True) # YES or NO
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class UserStake(Base):
    __tablename__ = "user_stakes"

    id = Column(String(36), primary_key=True, default=_uuid)
    market_id = Column(String(36), nullable=False, index=True)
    outcome = Column(String(16), nullable=False) # YES or NO
    amount = Column(Float, nullable=False) # amount staked
    timestamp = Column(DateTime(timezone=True), default=_utcnow)

class SyntheticProbeLog(Base):
    __tablename__ = "synthetic_probe_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    source = Column(String(128), nullable=False)
    log_type = Column(String(32), nullable=False) # info, success, warning, error
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)

class VerifierNode(Base):
    __tablename__ = "vnp_verifier_nodes"

    address = Column(String(128), primary_key=True)
    stake = Column(Float, nullable=False)
    reputation = Column(Float, nullable=False)
    diversity_score = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    region = Column(String(64), nullable=False)
    asn = Column(String(64), nullable=False)
    measurement_count = Column(Integer, nullable=False)
    accuracy = Column(Float, nullable=False)
    active = Column(Boolean, default=True)

class ProviderBondView(Base):
    __tablename__ = "vnp_provider_bonds"

    id = Column(String(36), primary_key=True, default=_uuid)
    api_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    bond_amount_usdc = Column(Float, nullable=False)
    target_p95_ms = Column(Float, nullable=False)
    observed_p95_ms = Column(Float, nullable=False)
    sigma_ms = Column(Float, nullable=False)
    deviation_ms = Column(Float, nullable=False)
    tolerance_ms = Column(Float, nullable=False)
    excess_ms = Column(Float, nullable=False)
    penalty_usdc = Column(Float, nullable=False)
    status = Column(String(32), nullable=False) # healthy, warning, breaching, critical
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

class EpochSettlement(Base):
    __tablename__ = "vnp_epoch_settlements"

    id = Column(String(36), primary_key=True, default=_uuid)
    epoch = Column(Integer, nullable=False, index=True)
    api_id = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    observed_p95 = Column(Float, nullable=False)
    target_p95 = Column(Float, nullable=False)
    penalty_applied = Column(Float, nullable=False)
    new_bond_balance = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
