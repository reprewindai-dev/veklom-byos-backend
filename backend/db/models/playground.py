"""Playground session and prompt models."""

from sqlalchemy import Column, DateTime, String, Text, JSON

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class PlaygroundSession(Base):
    __tablename__ = "playground_sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="", index=True)
    name = Column(String(256), default="New Session")
    messages = Column(JSON, default=list)
    model = Column(String(128), default="")
    mode = Column(String(32), default="chat")
    system_prompt = Column(Text, default="")
    tools = Column(JSON, default=list)
    response_format = Column(String(32), default="text")
    policy = Column(String(128), default="")
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow)


class PlaygroundPrompt(Base):
    __tablename__ = "playground_prompts"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), default="", index=True)
    name = Column(String(256), nullable=False)
    slug = Column(String(256), default="")
    version = Column(String(32), default="v1")
    body = Column(Text, default="")
    system_prompt = Column(Text, default="")
    response_format = Column(String(32), default="text")
    policy = Column(String(128), default="")
    tools = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow)
