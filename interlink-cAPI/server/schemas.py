"""Shared schemas for cAPI."""

from pydantic import BaseModel
from typing import Dict, Any, Optional

class ExecutionIntent(BaseModel):
    agent_id: str
    pgl_id: str
    target_resource: str
    action: str
    arguments: Dict[str, Any]
    context: Dict[str, Any]

class ExecutionReceipt(BaseModel):
    id: str
    type: str
    agent_id: str
    timestamp: str
    hash: Optional[str] = None
    reason: Optional[str] = None

class PolicyVerdict(BaseModel):
    allowed: bool
    reason: Optional[str] = None
