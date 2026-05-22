"""Shared SQLAlchemy model mixins."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDMixin:
    id = Column(String(36), primary_key=True, default=_uuid)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
