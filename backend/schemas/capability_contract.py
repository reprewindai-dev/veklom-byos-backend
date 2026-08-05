from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CapabilityContract(BaseModel):
    """
    Defines the governance and data-shaping contract for a capability.
    The reasoning engine requests capabilities, and the Control Plane enforces this contract.
    """
    capability_id: str = Field(..., description="Unique identifier for the capability, e.g., 'blueprint.generate'")
    description: str = Field(..., description="Human-readable description of what the capability does")
    
    requires: List[str] = Field(default_factory=list, description="Required context fields (e.g., 'tenant_id', 'repository_url')")
    
    allows_pii: List[str] = Field(default_factory=list, description="Specific PII fields permitted to pass through to execution")
    denies_pii: List[str] = Field(default_factory=list, description="Specific PII fields explicitly stripped before execution")
    
    secret_injections: List[str] = Field(default_factory=list, description="Secrets injected by the control plane (not the reasoning engine)")
    outputs: List[str] = Field(default_factory=list, description="Expected outputs or artifacts produced by the capability")

class CapabilityManifest(BaseModel):
    """
    The full manifest of all capabilities hosted by this service.
    Exposed via /.well-known/capabilities.json
    """
    version: str = "1.0.0"
    service_name: str
    capabilities: List[CapabilityContract]
