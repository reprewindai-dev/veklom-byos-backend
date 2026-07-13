"""
GPC Pipeline System — Core Schemas
Pydantic models for all GPC data structures.
Production-ready, schema-versioned, tenant-isolated.

Generated for: veklom-byos-backend/backend/gpc/
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal, Optional, Any, Dict, List, Set
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4


# ============================================================================
# PORT TYPES — Semantic Connection Validation
# ============================================================================

class PortType(str, Enum):
    """Semantic port types for connection compatibility checking."""
    PANDAS_DF = "pandas_df"
    DUCKDB_REL = "duckdb_rel"
    DOCUMENTS = "documents"
    SCALAR = "scalar"
    ANY = "any"


# ============================================================================
# NODE DEFINITIONS
# ============================================================================

class NodePort(BaseModel):
    """Input or output port on a node."""
    id: str = Field(..., description="Unique port ID within the node")
    port_type: PortType = Field(..., description="Semantic type of data flowing through this port")
    label: str = Field(..., description="Display label in UI")
    required: bool = Field(default=True, description="Whether this port must have a connection")

    model_config = ConfigDict(frozen=True)


class GPCNode(BaseModel):
    """Single node in the pipeline graph."""
    id: str = Field(..., description="Unique node ID (uuid4 or custom)")
    node_type: str = Field(..., description="Registry lookup key (e.g., 'CsvFileInput', 'FilterRows')")
    label: Optional[str] = Field(default=None, description="Display label override")
    config: Dict[str, Any] = Field(default_factory=dict, description="Component-specific configuration")
    
    # Connectivity
    input_ports: List[NodePort] = Field(default_factory=list, description="Incoming ports")
    output_ports: List[NodePort] = Field(default_factory=list, description="Outgoing ports")
    
    # Viewport state — excluded from code generation
    position: Optional[Dict[str, float]] = Field(default=None, description="Canvas position {x, y}")
    selected: bool = Field(default=False, description="UI selection state")
    hidden: bool = Field(default=False, description="Collapsed in tree view")
    
    # Execution tracking
    last_updated: float = Field(default=0.0, description="Epoch timestamp of last config change")
    last_executed: float = Field(default=0.0, description="Epoch timestamp of last successful execution")
    
    model_config = ConfigDict(extra='forbid')

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError("Node ID must be at least 3 characters")
        return v


class GPCEdge(BaseModel):
    """Connection between two node ports."""
    id: str = Field(..., description="Unique edge ID")
    source_node_id: str = Field(..., description="ID of source node")
    source_port_id: str = Field(..., description="ID of source port")
    target_node_id: str = Field(..., description="ID of target node")
    target_port_id: str = Field(..., description="ID of target port")
    
    model_config = ConfigDict(extra='forbid')


# ============================================================================
# PIPELINE GRAPH — The Canonical DAG Definition
# ============================================================================

class GPCPipelineGraph(BaseModel):
    """Complete pipeline graph definition. Schema-versioned, immutable after creation."""
    
    pipeline_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique pipeline ID")
    tenant_id: str = Field(..., description="Owning tenant")
    
    # Graph structure
    nodes: List[GPCNode] = Field(default_factory=list, description="All nodes in the graph")
    edges: List[GPCEdge] = Field(default_factory=list, description="All edges in the graph")
    
    # Metadata
    name: Optional[str] = Field(default=None, description="User-friendly pipeline name")
    description: Optional[str] = Field(default=None, description="Purpose of this pipeline")
    
    # Versioning and lineage
    schema_version: str = Field(default="1.0", description="GPC schema version")
    prompt_version: Optional[str] = Field(default=None, description="NL→Graph prompt version if AI-generated")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Compliance
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    data_residency_region: Literal["ca-central-1", "ca-west-1", "on-premise"] = Field(
        default="ca-central-1",
        description="Data residency requirement"
    )
    
    model_config = ConfigDict(extra='forbid')

    @field_validator('tenant_id')
    @classmethod
    def validate_tenant(cls, v):
        if not v:
            raise ValueError("tenant_id is required")
        return v


# ============================================================================
# COMPONENT REGISTRY — Node Type Definitions
# ============================================================================

class FormField(BaseModel):
    """Schema for a form input in the property panel."""
    name: str = Field(..., description="Config key")
    label: str = Field(..., description="Display label")
    type: Literal["text", "number", "select", "textarea", "checkbox"] = Field(..., description="Input type")
    required: bool = Field(default=False, description="Whether field must be filled")
    default: Optional[Any] = Field(default=None, description="Default value")
    options: Optional[List[Dict[str, str]]] = Field(default=None, description="For select: [{label, value}]")
    description: Optional[str] = Field(default=None, description="Help text")


class GPCComponentDefinition(BaseModel):
    """Definition of a node type that can be added to a pipeline."""
    
    node_type: str = Field(..., description="Registry key (e.g., 'CsvFileInput')")
    display_name: str = Field(..., description="Display name in UI")
    description: str = Field(default="", description="What this node does")
    category: Literal["input", "transform", "output", "ai", "custom"] = Field(..., description="Node category")
    
    # UI configuration
    icon: str = Field(default="Database", description="Lucide icon name")
    form_schema: List[FormField] = Field(default_factory=list, description="Property panel fields")
    
    # Port definitions
    input_ports: List[NodePort] = Field(default_factory=list, description="Expected input ports")
    output_ports: List[NodePort] = Field(default_factory=list, description="Guaranteed output ports")
    
    # Code generation
    code_generator_class: str = Field(..., description="Python class name implementing code generation")
    required_imports: List[str] = Field(default_factory=list, description="Python imports needed")
    
    # Tenant scope
    tenant_id: Optional[str] = Field(default=None, description="If set, private to this tenant; None = global")
    
    model_config = ConfigDict(extra='forbid')


# ============================================================================
# COMPILATION & EXECUTION
# ============================================================================

class PipelineCompilationRequest(BaseModel):
    """Request to compile a pipeline graph into Python code."""
    pipeline_id: str = Field(..., description="Pipeline to compile")
    tenant_id: str = Field(..., description="Executing tenant")
    target_node_id: Optional[str] = Field(default=None, description="If set, compile only this node and ancestors")


class PipelineCompilationResult(BaseModel):
    """Result of successful compilation."""
    success: bool = Field(default=True)
    python_code: str = Field(..., description="Generated, executable Python script")
    node_count: int = Field(..., description="Number of nodes in compiled pipeline")
    execution_order: List[str] = Field(..., description="Node IDs in topological sort order")
    parallel_levels: List[List[str]] = Field(..., description="Parallel execution levels")
    compilation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")


class PipelineExecutionTrace(BaseModel):
    """Audit event for each pipeline execution (Law 25 Section 93 compliance)."""
    trace_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique execution ID")
    tenant_id: str = Field(..., description="Owning tenant")
    pipeline_id: str = Field(..., description="Executed pipeline")
    user_id: str = Field(..., description="User who triggered execution")
    
    # Execution context
    execution_status: Literal["running", "success", "failure", "partial"] = Field(
        ...,
        description="Overall execution status"
    )
    node_id: Optional[str] = Field(default=None, description="Current/failed node")
    node_index: Optional[int] = Field(default=None, description="Position in execution order")
    
    # Timestamps and performance
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: float = Field(default=0.0, description="Total execution time")
    
    # Data lineage
    data_residency_region: Literal["ca-central-1", "ca-west-1", "on-premise"] = Field(
        ...,
        description="Where data was processed"
    )
    rows_processed: Optional[int] = Field(default=None, description="Rows transformed")
    tokens_consumed: Optional[int] = Field(default=None, description="LLM tokens used")
    
    # Versioning
    schema_version: str = Field(..., description="Graph schema version")
    prompt_version: Optional[str] = Field(default=None, description="NL→Graph prompt version")
    
    # Compliance metadata
    error_details: Optional[str] = Field(default=None, description="Failure reason if applicable")
    compliance_checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="PIPEDA/Law25 checks: {pipeda_consent: True, law25_pia_reference: ...}"
    )
    
    model_config = ConfigDict(extra='forbid')


# ============================================================================
# NL-TO-GRAPH GENERATION (LLM Output)
# ============================================================================

class NLToGraphRequest(BaseModel):
    """Request to convert natural language to a pipeline graph."""
    tenant_id: str = Field(..., description="Tenant making request")
    user_intent: str = Field(..., description="Messy natural language description of intent")
    available_components: Optional[List[str]] = Field(
        default=None,
        description="If set, LLM only generates from these node types"
    )
    data_residency_region: Literal["ca-central-1", "ca-west-1", "on-premise"] = Field(
        default="ca-central-1",
        description="Where data will be processed"
    )


class NLToGraphResult(BaseModel):
    """Result of NL→Graph generation."""
    success: bool = Field(default=True)
    pipeline_graph: GPCPipelineGraph = Field(..., description="Generated graph")
    reasoning: str = Field(..., description="LLM's reasoning for the graph structure")
    retry_count: int = Field(default=0, description="Number of repair-retry attempts needed")
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0, description="Confidence in generation")
    errors: List[str] = Field(default_factory=list, description="Validation errors (if not success)")


# ============================================================================
# CANVAS STATE (Frontend — NOT persisted to backend)
# ============================================================================

class CanvasViewportState(BaseModel):
    """Ephemeral canvas viewport state. Not persisted."""
    zoom: float = Field(default=1.0, ge=0.1, le=4.0)
    pan_x: float = Field(default=0.0)
    pan_y: float = Field(default=0.0)
    selected_node_ids: Set[str] = Field(default_factory=set)


# ============================================================================
# EXPORT / IMPORT
# ============================================================================

class PipelineExportPackage(BaseModel):
    """Complete, portable pipeline package for export/import."""
    version: str = Field(default="1.0")
    pipeline: GPCPipelineGraph = Field(..., description="The graph")
    components: List[GPCComponentDefinition] = Field(..., description="Component definitions used")
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    exported_by: str = Field(..., description="User who exported")
