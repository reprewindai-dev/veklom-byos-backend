"""
GPC FastAPI Routes
REST API for GPC pipeline system.

Endpoints:
- POST /api/v1/gpc/compile — Compile graph to Python
- POST /api/v1/gpc/generate — NL intent to graph (AI)
- POST /api/v1/gpc/execute — Run compiled pipeline
- GET /api/v1/gpc/components — List available components
- GET /api/v1/gpc/audit — Query audit trail
- GET /api/v1/gpc/stats — GPC statistics

Generated for: veklom-byos-backend/backend/apps/gpc/
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
import uuid

from backend.apps.gpc.schemas import (
    GPCPipelineGraph, PipelineCompilationRequest, PipelineCompilationResult, PipelineExecutionRequest,
    NLToGraphRequest, NLToGraphResult, PipelineExecutionTrace,
    GPCComponentDefinition, PortType
)
from backend.apps.gpc.compiler import GPCCompiler, DEFAULT_COMPONENTS, TopologicalSortError
from backend.core.security.auth import get_current_user
from backend.core.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.pipelines import PipelineRun
from backend.core.services.autonomous_worker import run_pipeline_background
from backend.compliance.gpc_gate import enforce_gpc_graph_compliance

logger = logging.getLogger("gpc")

router = APIRouter(prefix="/api/v1/gpc", tags=["gpc"])


# ============================================================================
# DEPENDENCIES & AUTH
# ============================================================================

async def get_tenant_id(user=Depends(get_current_user)) -> str:
    """Return the authenticated workspace as the GPC tenant identity."""
    tenant_id = getattr(user, "workspace_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Authenticated user has no tenant workspace")
    return str(tenant_id)



def validate_gpc_request(request: PipelineCompilationRequest, authenticated_tenant_id: str) -> None:
    """Validate client-supplied graph identity before compilation."""
    if request.tenant_id != authenticated_tenant_id:
        raise ValueError("tenant_id does not match the authenticated workspace")
    if request.graph is not None:
        if request.graph.tenant_id != authenticated_tenant_id:
            raise ValueError("graph tenant_id does not match the authenticated workspace")
        if request.graph.pipeline_id != request.pipeline_id:
            raise ValueError("graph pipeline_id does not match the request")
        if not request.graph.nodes:
            raise ValueError("graph must contain at least one node")
        compliance = enforce_gpc_graph_compliance(request.graph)
        if not compliance.allowed:
            raise ValueError(f"GPC compliance gate blocked graph: {compliance.message}")


# ============================================================================
# COMPILATION ENDPOINT
# ============================================================================

@router.post("/compile", response_model=PipelineCompilationResult)
async def compile_pipeline(
    request: PipelineCompilationRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> PipelineCompilationResult:
    """
    Compile a pipeline graph into executable Python code.
    
    Expects:
        - pipeline_id: ID of the pipeline to compile
        - tenant_id: Tenant making request
    
    Returns:
        Compilation result with Python code, execution order, parallel levels
    """
    try:
        validate_gpc_request(request, tenant_id)
        if request.graph is None:
            raise HTTPException(status_code=422, detail="graph is required for GPC compilation")
        pipeline_graph = request.graph
        
        compiler = GPCCompiler(component_registry=DEFAULT_COMPONENTS)
        result = compiler.compile(pipeline_graph)
        
        logger.info(
            f"Pipeline {request.pipeline_id} compiled successfully",
            extra={
                "tenant_id": tenant_id,
                "nodes": result.node_count,
                "levels": len(result.parallel_levels)
            }
        )
        
        return result
    
    except TopologicalSortError as e:
        logger.error(f"Cycle detected in pipeline {request.pipeline_id}: {e}")
        return PipelineCompilationResult(
            success=False,
            python_code="",
            node_count=0,
            execution_order=[],
            parallel_levels=[],
            warnings=[str(e)],
            pipeline_id=request.pipeline_id,
            tenant_id=tenant_id,
        )
    
    except Exception as e:
        logger.exception(f"Compilation failed for pipeline {request.pipeline_id}")
        return PipelineCompilationResult(
            success=False,
            python_code="",
            node_count=0,
            execution_order=[],
            parallel_levels=[],
            warnings=[f"Compilation error: {str(e)}"],
            pipeline_id=request.pipeline_id,
            tenant_id=tenant_id,
        )


# ============================================================================
# NL-TO-GRAPH GENERATION ENDPOINT
# ============================================================================

@router.post("/generate", response_model=NLToGraphResult)
async def generate_pipeline_from_intent(
    request: NLToGraphRequest,
    tenant_id: str = Depends(get_tenant_id),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> NLToGraphResult:
    """
    Convert natural language intent into a pipeline graph using LLM.
    
    Expects:
        - user_intent: Messy natural language description
        - available_components: Optional list of component types to use
        - data_residency_region: Where data will be processed (ca-central-1, ca-west-1, on-premise)
    
    Returns:
        Generated pipeline graph + reasoning
    """
    raise HTTPException(
        status_code=501,
        detail="GPC natural-language generation is unavailable: no approved generation provider is configured",
    )


# ============================================================================
# EXECUTION ENDPOINT
# ============================================================================

@router.post("/execute")
async def execute_pipeline(
    request: PipelineExecutionRequest,
    tenant_id: str = Depends(get_tenant_id),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue the compiled graph through the existing governed pipeline worker."""
    if request.tenant_id != tenant_id or request.graph.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_id does not match the authenticated workspace")
    if request.graph.pipeline_id != request.pipeline_id:
        raise HTTPException(status_code=422, detail="graph pipeline_id does not match the request")
    if not request.graph.nodes:
        raise HTTPException(status_code=422, detail="graph must contain at least one node")
    compliance = enforce_gpc_graph_compliance(request.graph)
    if not compliance.allowed:
        raise HTTPException(status_code=422, detail={"message": "GPC compliance gate blocked graph", "reason": compliance.message})

    compilation = GPCCompiler(component_registry=DEFAULT_COMPONENTS).compile(request.graph)
    if not compilation.success:
        raise HTTPException(status_code=422, detail={"message": "Compilation failed", "warnings": compilation.warnings})

    run_id = str(uuid.uuid4())
    steps = {"graph": request.graph.model_dump(mode="json")}
    run = PipelineRun(
        id=run_id,
        pipeline_id=request.pipeline_id,
        workspace_id=tenant_id,
        user_id=str(user.id),
        status="queued",
        progress=0.0,
        steps=steps,
    )
    db.add(run)
    await db.commit()
    asyncio.create_task(run_pipeline_background(run_id, steps, tenant_id, str(user.id)))

    async def event_generator():
        yield f"data: {json.dumps({'event': 'start', 'pipeline_id': request.pipeline_id, 'tenant_id': tenant_id, 'run_id': run_id, 'node_count': compilation.node_count})}\n\n"
        yield f"data: {json.dumps({'event': 'queued', 'run_id': run_id, 'status': 'queued'})}\n\n"
        for _ in range(120):
            await asyncio.sleep(0.5)
            await db.refresh(run)
            if run.status in {"completed", "success"}:
                yield f"data: {json.dumps({'event': 'complete', 'success': True, 'run_id': run_id, 'pipeline_id': request.pipeline_id, 'tenant_id': tenant_id})}\n\n"
                return
            if run.status in {"failed", "failure", "error"}:
                yield f"data: {json.dumps({'event': 'error', 'success': False, 'run_id': run_id, 'message': run.error or 'Governed execution failed'})}\n\n"
                return
        yield f"data: {json.dumps({'event': 'error', 'success': False, 'run_id': run_id, 'message': 'Execution status timeout'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============================================================================
# COMPONENTS ENDPOINT
# ============================================================================

@router.get("/components", response_model=List[Dict[str, Any]])
async def list_components(
    tenant_id: str = Depends(get_tenant_id)
):
    """
    List all available node components.
    Returns both global and tenant-private components.
    """
    components = []
    
    # Canonical component catalog exposed by the compiler registry
    base_components = [
        {
            "node_type": "CsvFileInput",
            "display_name": "CSV File Input",
            "category": "input",
            "description": "Load data from a CSV file",
            "icon": "FileText",
            "output_ports": [{"id": "out", "port_type": "pandas_df", "label": "DataFrame"}]
        },
        {
            "node_type": "FilterRows",
            "display_name": "Filter Rows",
            "category": "transform",
            "description": "Filter DataFrame rows based on condition",
            "icon": "Filter",
            "input_ports": [{"id": "in", "port_type": "pandas_df", "label": "Input"}],
            "output_ports": [{"id": "out", "port_type": "pandas_df", "label": "Filtered"}]
        },
        {
            "node_type": "Aggregate",
            "display_name": "Aggregate",
            "category": "transform",
            "description": "Group and aggregate data",
            "icon": "Layers",
            "input_ports": [{"id": "in", "port_type": "pandas_df", "label": "Input"}],
            "output_ports": [{"id": "out", "port_type": "pandas_df", "label": "Aggregated"}]
        },
        {
            "node_type": "SelectColumns",
            "display_name": "Select Columns",
            "category": "transform",
            "description": "Select specific columns",
            "icon": "Columns",
            "input_ports": [{"id": "in", "port_type": "pandas_df", "label": "Input"}],
            "output_ports": [{"id": "out", "port_type": "pandas_df", "label": "Selected"}]
        },
        {
            "node_type": "ParquetOutput",
            "display_name": "Parquet Output",
            "category": "output",
            "description": "Save data to Parquet file",
            "icon": "Download",
            "input_ports": [{"id": "in", "port_type": "pandas_df", "label": "Input"}]
        },
        {
            "node_type": "DuckDBQuery",
            "display_name": "DuckDB Query",
            "category": "transform",
            "description": "Execute SQL query via DuckDB",
            "icon": "Database",
            "input_ports": [{"id": "in", "port_type": "pandas_df", "label": "Input"}],
            "output_ports": [{"id": "out", "port_type": "duckdb_rel", "label": "Result"}]
        }
    ]
    
    return base_components


# ============================================================================
# AUDIT ENDPOINT
# ============================================================================

@router.get("/audit")
async def query_audit_log(
    tenant_id: str = Depends(get_tenant_id),
    pipeline_id: Optional[str] = None,
    user_id: Optional[str] = None,
    days: int = 7
):
    """
    Query audit trail for compliance (Law 25 Section 93).
    
    Filters:
        - pipeline_id: Specific pipeline
        - user_id: Specific user
        - days: Lookback window (default 7)
    """
    raise HTTPException(status_code=501, detail="GPC audit storage is not configured")


# ============================================================================
# STATS ENDPOINT
# ============================================================================

@router.get("/stats")
async def get_gpc_statistics(
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get GPC system statistics for dashboard.
    """
    raise HTTPException(status_code=501, detail="GPC statistics storage is not configured")
