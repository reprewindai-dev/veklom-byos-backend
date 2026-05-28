from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from backend.db.base_class import Base

class AgentCall(Base):
    __tablename__ = "agent_calls"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    tenant_id = Column(String(255), index=True, nullable=False)
    route = Column(String(512), index=True, nullable=False)
    model_key = Column(String(255), index=True, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    http_status = Column(Integer, nullable=False)
    policy_result = Column(String(50), nullable=False)  # 'allow' | 'deny' | 'error'
    policy_error_code = Column(String(255), nullable=True)
    context_tokens = Column(Integer, nullable=False, default=0)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
