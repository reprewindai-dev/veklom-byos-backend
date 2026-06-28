from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from backend.core.database.database import Base

class QuarantinedIntent(Base):
    """
    MCPAPI v2.0 Quarantined Intents Table
    Stores execution intents that failed Phase 3 (Safety & Anomaly Gate)
    and are awaiting Phase 5 (Approval Workflow Quorum) resolution.
    """
    __tablename__ = "quarantined_intents"

    id = Column(String, primary_key=True, index=True) # Typically QZ-hash
    agent_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=False)
    
    target_protocol = Column(String, nullable=False)
    action = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    
    failure_phase = Column(Integer, nullable=False)
    failure_reason = Column(String, nullable=False)
    
    status = Column(String, default="pending", index=True) # pending, approved, rejected
    resolution_reason = Column(String, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
