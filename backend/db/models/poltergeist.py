"""Poltergeist capability registry and state tracking."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON, ForeignKey

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class CapabilityHauntState(Base):
    """
    Atomic state tracking for active capability resolution processes.
    Represents an ongoing 'haunt' (intent to build/resolve).
    """
    __tablename__ = "capability_haunt_states"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    fingerprint = Column(String(255), nullable=False, index=True, unique=True)
    
    # idle, resolving, building, testing, verifying, fresh, failed
    status = Column(String(32), default="idle")
    
    heartbeat = Column(Integer, default=0)
    queued_revision = Column(Integer, default=1)
    freshest_artifact_revision = Column(Integer, default=0)
    manifest = Column(JSON, default=dict)
    
    # Store dynamic validation outcomes like RepoGate & PGL
    verification_results = Column(JSON, default=dict)
    
    error_log = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class CapabilityGhost(Base):
    """
    Permanent system-of-record for successfully built capabilities.
    Points to Cloudflare R2 artifacts and stores the original capability manifest.
    """
    __tablename__ = "capability_ghosts"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    fingerprint = Column(String(255), nullable=False, index=True)
    
    revision = Column(Integer, nullable=False)
    manifest = Column(JSON, default=dict)
    
    # Cloudflare R2 pointers
    artifact_pointer = Column(String(1024), default="")
    evidence_pointer = Column(String(1024), default="")
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


import enum
from sqlalchemy import Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

class JobStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    VALIDATED = "VALIDATED"
    BOUND = "BOUND"
    FAILED = "FAILED"

class ManufacturingJob(Base):
    __tablename__ = "manufacturing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    target_repository = Column(String, nullable=False, index=True)
    target_commit = Column(String, nullable=False)
    status = Column(Enum(JobStatus, native_enum=False), nullable=False, default=JobStatus.DETECTED, index=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transitions = relationship(
        "ManufacturingTransition",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="ManufacturingTransition.created_at"
    )

class ManufacturingTransition(Base):
    __tablename__ = "manufacturing_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("manufacturing_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("ManufacturingJob", back_populates="transitions")
