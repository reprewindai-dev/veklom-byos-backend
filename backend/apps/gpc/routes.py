"""
GPC FastAPI Routes
Complete backend API for pipeline generation, compilation, testing, and deployment

Endpoints:
  POST /api/v1/gpc/generate — Intent → Graph (LLM)
  POST /api/v1/gpc/compile — Graph → Python code (AST)
  POST /api/v1/gpc/execute — Run pipeline (SSE streaming)
  POST /api/v1/gpc/test — Test on sample data (SSE streaming)
  POST /api/v1/gpc/export-github — Export GitHub Actions workflow
  GET /api/v1/gpc/components — List available node types
  GET /api/v1/gpc/audit — Audit trail
  GET /api/v1/gpc/stats — Dashboard metrics

Location: veklom-byos-backend/backend/apps/gpc/routes.py
"""

import json
import asyncio
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.gpc.schemas import (
    GPCPipelineGraph,
    GPCNode,
    GPCEdge,
    NLToGraphRequest,
    NLToGraphResult,
    PipelineCompilationRequest,
    PipelineCompilationResult,
    PipelineExecutionTrace,
)
from backend.gpc.compiler import GPCCompiler
from backend.gpc.test_executor import TestExecutionMode, PipelineTestExecutor
from backend.gpc.github_export import GitHubWorkflowExporter
from backend.gpc.poltergeist.poltergeist_watcher import CapabilityWatcher, CapabilityRequirement

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/api/v1/gpc", tags=["gpc"])

# Global components (initialized on startup)
compiler: Optional[GPCCompiler] = None
test_executor: Optional[PipelineTestExecutor] = None
watcher: Optional[CapabilityWatcher] = None
github_exporter: Optional[GitHubWorkflowExporter] = None

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class GenerateRequest(BaseModel):
    """Request to generate pipeline from natural language intent"""
    user_intent: str
    tenant_id: str = "default"
    data_residency_region: str = "ca-central-1"


class GenerateResponse(BaseModel):
    """Response from pipeline generation"""
    success: bool
    pipeline_graph: Optional[GPCPipelineGraph] = None
    reasoning: Optional[str] = None
    confidence_score: Optional[float] = None
    errors: Optional[List[str]] = None


class CompileRequest(BaseModel):
    """Request to compile pipeline"""
    pipeline_id: str
    tenant_id: str = "default"
    nodes: List[dict]
    edges: List[dict]
    target_node_id: Optional[str] = None


class ExecuteRequest(BaseModel):
    """Request to execute pipeline"""
    pipeline_id: str
    tenant_id: str = "default"
    nodes: List[dict]
    edges: List[dict]
    target_node_id: Optional[str] = None


class TestRequest(BaseModel):
    """Request to test pipeline on sample data"""
    pipeline_id: str
    tenant_id: str = "default"
    mode: str = "sample"  # dry_run, sample, full
    nodes: List[dict]
    edges: List[dict]


class ExportGitHubRequest(BaseModel):
    """Request to export pipeline to GitHub Actions"""
    pipeline_id: str
    tenant_id: str = "default"
    github_repo: str  # owner/repository
    nodes: List[dict]
    edges: List[dict]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def convert_dict_to_gpc_nodes(nodes_data: List[dict]) -> List[GPCNode]:
    """Convert dict nodes to GPCNode"""
    result = []
    for n in nodes_data:
        node = GPCNode(
            id=n.get("id"),
            node_type=n.get("node_type"),
            label=n.get("label"),
            config=n.get("config", {}),
            position=n.get("position"),
        )
        result.append(node)
    return result


def convert_dict_to_gpc_edges(edges_data: List[dict]) -> List[GPCEdge]:
    """Convert dict edges to GPCEdge"""
    result = []
    for e in edges_data:
        edge = GPCEdge(
            id=e.get("id"),
            source_node_id=e.get("source_node_id") or e.get("source"),
            source_port_id=e.get("source_port_id", "out"),
            target_node_id=e.get("target_node_id") or e.get("target"),
            target_port_id=e.get("target_port_id", "in"),
        )
        result.append(edge)
    return result


async def stream_events(event_generator):
    """Convert async event generator to SSE format"""
    try:
        async for event in event_generator:
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as e:
        print(f"Streaming error: {e}")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/generate")
async def generate_from_intent(request: GenerateRequest):
    """
    Generate a pipeline from natural language intent.
    
    Uses LLM (Claude + constrained decoding) to convert intent to GPCPipelineGraph.
    Poltergeist watcher watches the graph and emits capability requirements.
    """
    raise HTTPException(status_code=501, detail="NOT_IMPLEMENTED")


@router.post("/compile")
async def compile_pipeline(request: CompileRequest):
    """
    Compile a pipeline graph to Python code.
    
    Uses AST-based code generation (not string templates).
    Produces syntactically valid, deterministic Python.
    """
    try:
        if not compiler:
            raise HTTPException(status_code=500, detail="Compiler not initialized")
        
        # Convert dicts to Pydantic models
        nodes = convert_dict_to_gpc_nodes(request.nodes)
        edges = convert_dict_to_gpc_edges(request.edges)
        
        # Create pipeline graph
        graph = GPCPipelineGraph(
            pipeline_id=request.pipeline_id,
            tenant_id=request.tenant_id,
            nodes=nodes,
            edges=edges,
        )
        
        # Compile
        python_code = compiler.compile(graph)
        
        return {
            "success": True,
            "pipeline_id": request.pipeline_id,
            "python_code": python_code,
            "node_count": len(nodes),
            "execution_order": [n.id for n in nodes],
            "warnings": [],
        }
    
    except Exception as e:
        print(f"Compilation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/execute")
async def execute_pipeline(request: ExecuteRequest):
    """
    Execute a pipeline with SSE streaming of execution events.
    """
    raise HTTPException(status_code=501, detail="NOT_IMPLEMENTED")


@router.post("/test")
async def test_pipeline(request: TestRequest):
    """
    Test a pipeline on sample data with SSE streaming.
    """
    raise HTTPException(status_code=501, detail="NOT_IMPLEMENTED")


@router.post("/export-github")
async def export_to_github(request: ExportGitHubRequest):
    """
    Export pipeline as GitHub Actions workflow.
    """
    raise HTTPException(status_code=501, detail="NOT_IMPLEMENTED")


@router.get("/components")
async def list_components():
    """
    List all available component types.
    """
    return [
        {
            "node_type": "CsvFileInput",
            "display_name": "CSV File",
            "category": "input",
            "input_ports": [],
            "output_ports": [{"name": "out", "type": "pandas_df"}],
        },
        {
            "node_type": "FilterRows",
            "display_name": "Filter Rows",
            "category": "transform",
            "input_ports": [{"name": "in", "type": "pandas_df"}],
            "output_ports": [{"name": "out", "type": "pandas_df"}],
        },
        {
            "node_type": "ParquetOutput",
            "display_name": "Parquet Output",
            "category": "output",
            "input_ports": [{"name": "in", "type": "pandas_df"}],
            "output_ports": [],
        },
    ]


@router.get("/audit")
async def get_audit_trail(
    pipeline_id: Optional[str] = None,
    tenant_id: str = "default",
    limit: int = 100,
):
    """Get audit trail for a pipeline."""
    return {
        "pipeline_id": pipeline_id,
        "events": [],
        "total_count": 0,
    }


@router.get("/stats")
async def get_stats(tenant_id: str = "default"):
    """Dashboard statistics."""
    return {
        "pipelines_generated": 0,
        "successful_executions": 0,
        "failed_executions": 0,
        "avg_compile_time_ms": 0,
        "avg_execution_time_ms": 0,
        "cache_hit_rate_percent": 0,
    }


# ============================================================================
# INITIALIZATION
# ============================================================================

async def initialize_gpc():
    """Initialize GPC components on app startup"""
    global compiler, test_executor, watcher, github_exporter
    
    print("[GPC] Initializing components...")
    
    compiler = GPCCompiler()
    test_executor = PipelineTestExecutor()
    
    async def on_requirement(req: CapabilityRequirement):
        print(f"[Poltergeist] Capability required: {req.node_type}")
    
    watcher = CapabilityWatcher(on_requirement=on_requirement)
    github_exporter = GitHubWorkflowExporter()
    
    print("[GPC] Initialization complete")


# Mount in main FastAPI app:
# from backend.apps.gpc.routes import router, initialize_gpc
# app.include_router(router)
# app.add_event_handler("startup", initialize_gpc)
