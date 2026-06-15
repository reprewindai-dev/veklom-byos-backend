"""Execution Certificate model for PGL Governance."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class ExecutionCertificate(Base):
    """Post-execution signed attestation binding output to the exact governed configuration."""

    __tablename__ = "execution_certificates"

    id = Column(String(36), primary_key=True, default=_uuid)
    trace_id = Column(String(64), nullable=False, index=True, unique=True)
    genome_hash = Column(String(128), nullable=False, index=True)
    input_hash = Column(String(128), nullable=False)
    output_hash = Column(String(128), nullable=False)
    watchtower_results = Column(JSON, nullable=False, default=list)
    governance_tier = Column(String(32), nullable=False)
    governance_overhead_ms = Column(Integer, nullable=False, default=0)
    policy_version = Column(String(32), nullable=True)
    constitution_version = Column(String(32), nullable=True)
    certificate_jwt = Column(Text, nullable=False)
    issued_at = Column(DateTime(timezone=True), default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
