"""
MCPAPI v2.0 Governance Specification Models.
Aligned with interlink-mcpapi (Rust prototype).
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class RiskLevel(str, Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"

class TransportType(str, Enum):
    Mcp = "Mcp"
    Http = "Http"
    Grpc = "Grpc"

class ElicitationStatus(str, Enum):
    Pending = "Pending"
    Approved = "Approved"
    Denied = "Denied"
    TimedOut = "TimedOut"

class Capability(BaseModel):
    id: str
    title: str
    description: str
    tags: List[str]
    risk: RiskLevel
    scopes: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    toolset: str

class CapabilityContext(BaseModel):
    tenant_id: str
    actor_id: str
    transport: TransportType
    trace_id: str
    environment: str # dev, staging, prod
    is_untrusted_content: bool
    enabled_toolsets: List[str]
    approval_status: Optional[ElicitationStatus] = None

class InvocationRequest(BaseModel):
    capability_id: str
    arguments: Dict[str, Any]
    context: CapabilityContext

class RuntimeResponse(BaseModel):
    type: str
    result: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    elicitation_id: Optional[UUID] = None
    trace_id: Optional[str] = None
    pgl_hash: Optional[str] = None
    links: Dict[str, Dict[str, str]] = Field(default_factory=dict, alias="_links")
