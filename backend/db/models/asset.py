"""Asset model for tracking S3 uploads."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from backend.core.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=_uuid)
    workspace_id = Column(String(36), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(128), default="application/octet-stream")
    file_size = Column(Integer, default=0)
    s3_key = Column(String(512), nullable=False, unique=True)
    s3_bucket = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # Marketplace Intelligence
    marketplace_status = Column(String(50), default="private") # private, pending, active, rejected
    price_usd = Column(Integer, default=0) # stored in cents or float depending on type, let's use float
    category = Column(String(128), nullable=True)
    intelligence_confidence = Column(Integer, default=0)
