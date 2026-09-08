from sqlalchemy import Boolean, Column, DateTime, String, ForeignKey
from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid

class VLinkBinding(Base):
    __tablename__ = "vlink_bindings"

    id = Column(String(36), primary_key=True, default=_uuid)
    vlink_id = Column(String(64), nullable=False, unique=True, index=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, unique=True)
    workspace_id = Column(String(36), nullable=False, index=True)
    connection_ref = Column(String(64), nullable=False) # Projected connection reference
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
