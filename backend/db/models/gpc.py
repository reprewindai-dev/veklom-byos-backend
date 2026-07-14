from sqlalchemy import Column, String, JSON, DateTime, Float, Integer
from datetime import datetime, timezone
from backend.core.database.database import Base

class GpcPipelineAudit(Base):
    """
    Audit log for pipeline executions (Law 25 Section 93 compliance).
    """
    __tablename__ = "gpc_audit"

    trace_id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True)
    pipeline_id = Column(String, index=True)
    user_id = Column(String, index=True)
    execution_status = Column(String)  # running, success, failure, partial
    node_id = Column(String, nullable=True)
    node_index = Column(Integer, nullable=True)
    
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float)
    
    data_residency_region = Column(String)
    rows_processed = Column(Integer, nullable=True)
    tokens_consumed = Column(Integer, nullable=True)
    
    schema_version = Column(String)
    prompt_version = Column(String, nullable=True)
    error_details = Column(String, nullable=True)
    compliance_checks = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
