from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime

class NodeState(BaseModel):
    node_id: str = Field(..., description="Unique identifier for the failing node")
    node_type: str = Field(..., description="The type of the node (e.g., IngestNode, SovereignLLMNode)")
    inputs: Dict[str, Any] = Field(..., description="The exact payload or configuration passed into the node")
    outputs: Optional[Dict[str, Any]] = Field(None, description="Partial outputs if the node failed mid-execution")

class PipelineErrorLog(BaseModel):
    error_id: str = Field(..., description="Unique ID for this error event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the failure")
    pipeline_id: str = Field(..., description="ID of the pipeline being executed")
    failing_node: NodeState = Field(..., description="State of the node at the time of failure")
    error_reason: str = Field(..., description="Detailed exception message or validation failure reason")
    retry_count: int = Field(default=0, description="Current number of retry attempts for this node")
    max_retries: int = Field(default=3, description="Maximum bounded retry limits before escalating")
    human_handoff_status: str = Field(
        default="not_triggered", 
        description="Status of human intervention: 'not_triggered', 'pending', or 'resolved'"
    )
    suggested_fix: Optional[str] = Field(
        None, 
        description="LLM-generated hypothesis for self-healing to be applied on the next retry"
    )
