from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Enum, Float
from sqlalchemy.dialects.postgresql import JSONB
from backend.core.database.database import Base
import enum

class VeklomRunStatus(str, enum.Enum):
    INTENT_CAPTURED = "INTENT_CAPTURED"
    COMPILED = "COMPILED"
    CONTEXTUALIZED = "CONTEXTUALIZED"
    GOVERNED = "GOVERNED"
    HELD = "HELD"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    COMMITTED = "COMMITTED"
    ROUTED = "ROUTED"
    EXECUTING = "EXECUTING"
    ATTESTED = "ATTESTED"
    BILLED = "BILLED"
    SEALED = "SEALED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"

class VeklomRun(Base):
    __tablename__ = "veklom_runs"

    run_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), index=True, nullable=False)
    tenant_id = Column(String(36), index=True, nullable=False)
    actor_id = Column(String(36), index=True, nullable=False)

    intent = Column(JSONB, nullable=False)
    v2_plan = Column(JSONB, nullable=True)
    v3_context = Column(JSONB, nullable=True)
    seked_state = Column(JSONB, nullable=True)
    v4_decision = Column(JSONB, nullable=True)
    pgl_identity = Column(JSONB, nullable=True)
    execution_identity = Column(JSONB, nullable=True)
    route = Column(JSONB, nullable=True)
    tools = Column(JSONB, nullable=True)
    agents = Column(JSONB, nullable=True)
    budget = Column(JSONB, nullable=True)
    evidence = Column(JSONB, nullable=True)

    status = Column(String(32), nullable=False, default=VeklomRunStatus.INTENT_CAPTURED.value)
    execution_mode = Column(String(32), nullable=False, default="live")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
