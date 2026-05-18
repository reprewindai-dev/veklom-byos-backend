"""AI execution models."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, JSON, Boolean

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class ExecLog(Base):
    __tablename__ = "exec_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="", index=True)
    model = Column(String(128), default="")
    provider = Column(String(64), default="")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(32), default="completed")
    content_safety_score = Column(Float, default=1.0)
    policy_flags = Column(JSON, default=list)
    request_hash = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
