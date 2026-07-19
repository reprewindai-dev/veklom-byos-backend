import json
import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import uuid4

class CapabilityRequirement(BaseModel):
    """A required capability for a plan step (e.g., specific API access, MCP tool)."""
    name: str = Field(..., description="Name of the required capability")
    version: Optional[str] = Field(default=None, description="Minimum version required")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context or parameters required")
    
class PlanStep(BaseModel):
    """A single deterministic step in the canonical plan."""
    step_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique step identifier")
    action: str = Field(..., description="Action to perform (e.g., run_tool, call_api)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Bound parameters for this step")
    capabilities_required: List[CapabilityRequirement] = Field(default_factory=list, description="Capabilities needed to execute this step")

class CanonicalPlanIR(BaseModel):
    """
    Canonical Plan Intermediate Representation (IR).
    This is the typed, deterministic output of the Governed Plan Compiler.
    It is designed to be hashed, signed, and passed through the Policy Decision Point (PDP).
    """
    plan_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique plan identifier")
    tenant_id: str = Field(..., description="Owning tenant ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    # Core Plan Definition
    steps: List[PlanStep] = Field(default_factory=list, description="Ordered execution steps")
    
    # Governance & Policy Context
    risk_flags: List[str] = Field(default_factory=list, description="Identified risk flags requiring policy evaluation")
    budget_constraints: Dict[str, float] = Field(default_factory=dict, description="Budget limits (e.g., max_tokens, max_cost)")
    expected_evidence: List[str] = Field(default_factory=list, description="Types of evidence required to be emitted (e.g., dsse_attestation)")
    
    model_config = ConfigDict(extra='forbid')

    def deterministic_json(self) -> str:
        """
        Serialize the plan deterministically for hashing.
        Excludes ephemeral fields like timestamps if they shouldn't affect the hash (or we enforce strict ordering).
        Here we serialize everything sorted by keys.
        """
        data = self.model_dump(mode='json')
        return json.dumps(data, sort_keys=True, separators=(',', ':'))

    def compute_hash(self) -> str:
        """
        Compute the SHA-256 hash of the deterministic JSON representation.
        This hash becomes the cryptographic anchor for the evidence pipeline.
        """
        payload = self.deterministic_json().encode('utf-8')
        return hashlib.sha256(payload).hexdigest()
