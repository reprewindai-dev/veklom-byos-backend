"""Risk Profile, Outcome Feedback, and High Performer models for Sovereign Network Intelligence."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class OrgRiskProfile(Base):
    """Tracks abuse scores and risk indicators at the organization level."""

    __tablename__ = "org_risk_profiles"

    id = Column(String(36), primary_key=True, default=_uuid)
    org_id = Column(String(64), nullable=False, unique=True, index=True)
    abuse_score = Column(Float, default=0.0)
    override_abuse_score = Column(Float, default=0.0)
    payment_risk_score = Column(Float, default=0.0)
    injection_attempts = Column(Integer, default=0)
    composite_risk = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class OutcomeFeedback(Base):
    """Captures user and evaluator feedback on governed execution outcomes."""

    __tablename__ = "outcome_feedback"

    id = Column(String(36), primary_key=True, default=_uuid)
    trace_id = Column(String(64), nullable=False, unique=True, index=True)
    accepted = Column(Boolean, default=True)
    user_rating = Column(Integer, nullable=True)
    feedback_text = Column(Text, nullable=True)
    actual_outcome = Column(JSON, nullable=True)
    predicted_outcome = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class HighPerformerEntry(Base):
    """Registers highly performing configurations and output signatures for transfer learning."""

    __tablename__ = "high_performer_entries"

    id = Column(String(36), primary_key=True, default=_uuid)
    task_type = Column(String(64), nullable=False, index=True)
    output_signature = Column(String(128), nullable=False)
    performance_score = Column(Float, default=1.0)
    genome_hash = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
