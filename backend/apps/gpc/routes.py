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
from uuid import uuid4

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
from backend.core.services.provider_routing_service import execute_governed_inference

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



def _extract_json_object(content: str) -> Dict[str, Any]:
    """Extract one JSON object from a provider response, including fenced JSON."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    raise ValueError("generation provider did not return a JSON object")


def _build_generated_result(content: str, request: NLToGraphRequest, tenant_id: str) -> NLToGraphResult:
    """Validate provider output as a real GPC graph before returning it to the client."""
    payload = _extract_json_object(content)
    graph_data = payload.get("pipeline_graph") or payload.get("graph")
    if not isinstance(graph_data, dict):
        raise ValueError("generation response did not contain pipeline_graph")

    graph_data = dict(graph_data)
    graph_data["tenant_id"] = tenant_id
    graph_data["pipeline_id"] = f"gpc_{uuid4().hex}"
    graph_data["data_residency_region"] = request.data_residency_region
    graph = GPCPipelineGraph.model_validate(graph_data)
    if not graph.nodes:
        raise ValueError("generation response produced an empty graph")

    allowed = set(request.available_components or DEFAULT_COMPONENTS.keys())
    unsupported = sorted({node.node_type for node in graph.nodes} - allowed)
    if unsupported:
        raise ValueError(f"generation response used unsupported components: {', '.join(unsupported)}")
    GPCCompiler(component_registry=DEFAULT_COMPONENTS).compile(graph)

    reasoning = payload.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("generation response did not contain reasoning")
    confidence = payload.get("confidence_score", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    return NLToGraphResult(
        success=True,
        pipeline_graph=graph,
        reasoning=reasoning,
        retry_count=int(payload.get("retry_count", 0) or 0),
        confidence_score=max(0.0, min(1.0, float(confidence))),
        errors=[],
    )

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
    
    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

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
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NLToGraphResult:
    """Generate and validate a GPC graph through the existing governed provider router."""
    if request.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_id does not match the authenticated workspace")
    components = sorted(request.available_components or DEFAULT_COMPONENTS.keys())
    prompt = {
        "role": "system",
        "content": (
            "You generate GPC pipeline graphs. Return only JSON with keys "
            "pipeline_graph, reasoning, confidence_score, retry_count. The graph must "
            "contain nodes and edges using only these component types: " + ", ".join(components) + ". "
            "Do not invent component types, tenant IDs, or pipeline IDs. "
            "Each node must include id and node_type; each edge must reference existing node IDs."
        ),
    }
    user_message = {
        "role": "user",
        "content": json.dumps({
            "intent": request.user_intent,
            "data_residency_region": request.data_residency_region,
            "available_components": components,
        }),
    }
    try:
        result, _, _, _ = await execute_governed_inference(
            db,
            tenant_id,
            str(user.id),
            {
                "model": "llama3.2:latest",
                "messages": [prompt, user_message],
                "temperature": 0.1,
                "max_tokens": 4096,
            },
        )
        content = result.payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _build_generated_result(content, request, tenant_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("GPC generation provider failed")
        raise HTTPException(status_code=502, detail="GPC generation provider unavailable") from exc

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
