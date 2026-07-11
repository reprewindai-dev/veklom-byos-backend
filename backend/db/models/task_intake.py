from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Integer, JSON
from backend.core.database.database import Base

class TaskIntake(Base):
    __tablename__ = "task_intakes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), index=True, nullable=False)
    task = Column(String, nullable=False)
    round = Column(Integer, nullable=False)
    nonce = Column(String(128), unique=True, index=True, nullable=False)
    secret = Column(String(255), nullable=False)
    brief = Column(String, nullable=True)
    checks = Column(JSON, nullable=True)
    evaluation_url = Column(String(1024), nullable=True)
    endpoint = Column(String(255), nullable=True)
    statuscode = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="PENDING")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
