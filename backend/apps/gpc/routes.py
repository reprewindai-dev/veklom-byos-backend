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

from backend.gpc.gpc_schemas import (
    GPCPipelineGraph, PipelineCompilationRequest, PipelineCompilationResult,
    NLToGraphRequest, NLToGraphResult, PipelineExecutionTrace,
    GPCComponentDefinition, PortType
)
from backend.gpc.gpc_compiler import GPCCompiler, DEFAULT_COMPONENTS, TopologicalSortError

logger = logging.getLogger("gpc")

router = APIRouter(prefix="/api/v1/gpc", tags=["gpc"])


# ============================================================================
# DEPENDENCIES & AUTH
# ============================================================================

async def get_tenant_id(authorization: str = None) -> str:
    """Extract tenant_id from JWT bearer token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # In production: validate JWT, extract tenant_id
    # For now: mock implementation
    try:
        token = authorization.replace("Bearer ", "")
        # Parse JWT and extract tenant_id claim
        # This is a placeholder; use PyJWT in production
        return "tenant_" + token[:16]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


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
        # In production: load pipeline from database
        # For now: mock load
        pipeline_graph = GPCPipelineGraph(
            pipeline_id=request.pipeline_id,
            tenant_id=tenant_id
        )
        
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
            warnings=[str(e)]
        )
    
    except Exception as e:
        logger.exception(f"Compilation failed for pipeline {request.pipeline_id}")
        return PipelineCompilationResult(
            success=False,
            python_code="",
            node_count=0,
            execution_order=[],
            parallel_levels=[],
            warnings=[f"Compilation error: {str(e)}"]
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
    try:
        # In production: call vLLM + XGrammar or Claude API with structured output
        # Placeholder: mock LLM response
        intent_lower = request.user_intent.lower()
        
        # Mock logic: detect CSV input → parsing → output
        has_csv_input = "csv" in intent_lower or "file" in intent_lower
        has_filter = "filter" in intent_lower or "where" in intent_lower
        has_output = "save" in intent_lower or "export" in intent_lower or "parquet" in intent_lower
        
        nodes = []
        edges = []
        node_id_counter = 0
        
        # Input node
        if has_csv_input:
            input_node_id = f"node_{node_id_counter}"
            node_id_counter += 1
            nodes.append({
                "id": input_node_id,
                "node_type": "CsvFileInput",
                "label": "Load CSV",
                "config": {"filePath": "input.csv", "sep": ","},
                "output_ports": [{"id": "out", "port_type": "pandas_df", "label": "DataFrame"}]
            })
        
        # Filter node
        prev_node_id = input_node_id if has_csv_input else None
        if has_filter and prev_node_id:
            filter_node_id = f"node_{node_id_counter}"
            node_id_counter += 1
            nodes.append({
                "id": filter_node_id,
                "node_type": "FilterRows",
                "label": "Filter Rows",
                "config": {"column": "status", "value": "active"},
                "input_ports": [{"id": "in", "port_type": "pandas_df", "label": "Input DataFrame"}],
                "output_ports": [{"id": "out", "port_type": "pandas_df", "label": "Filtered DataFrame"}]
            })
            edges.append({
                "id": f"edge_{len(edges)}",
                "source_node_id": prev_node_id,
                "source_port_id": "out",
                "target_node_id": filter_node_id,
                "target_port_id": "in"
            })
            prev_node_id = filter_node_id
        
        # Output node
        if has_output and prev_node_id:
            output_node_id = f"node_{node_id_counter}"
            nodes.append({
                "id": output_node_id,
                "node_type": "ParquetOutput",
                "label": "Export Parquet",
                "config": {"outputPath": "output.parquet"},
                "input_ports": [{"id": "in", "port_type": "pandas_df", "label": "Input DataFrame"}]
            })
            edges.append({
                "id": f"edge_{len(edges)}",
                "source_node_id": prev_node_id,
                "source_port_id": "out",
                "target_node_id": output_node_id,
                "target_port_id": "in"
            })
        
        # Construct graph
        graph_dict = {
            "pipeline_id": f"pipeline_{tenant_id[:8]}_{datetime.utcnow().timestamp()}",
            "tenant_id": tenant_id,
            "nodes": nodes,
            "edges": edges,
            "data_residency_region": request.data_residency_region,
            "prompt_version": "gpc-v1-mock"
        }
        
        pipeline_graph = GPCPipelineGraph(**graph_dict)
        
        # Log generation event
        logger.info(
            f"Pipeline generated from intent",
            extra={
                "tenant_id": tenant_id,
                "nodes": len(nodes),
                "intent_length": len(request.user_intent)
            }
        )
        
        return NLToGraphResult(
            success=True,
            pipeline_graph=pipeline_graph,
            reasoning="Generated nodes for CSV input, filtering, and Parquet export based on intent analysis",
            retry_count=0,
            confidence_score=0.85
        )
    
    except ValidationError as e:
        return NLToGraphResult(
            success=False,
            pipeline_graph=None,
            reasoning="",
            errors=[str(e)]
        )
    except Exception as e:
        logger.exception(f"Pipeline generation failed for tenant {tenant_id}")
        return NLToGraphResult(
            success=False,
            pipeline_graph=None,
            reasoning="",
            errors=[f"Generation error: {str(e)}"]
        )


# ============================================================================
# EXECUTION ENDPOINT
# ============================================================================

@router.post("/execute")
async def execute_pipeline(
    pipeline_id: str,
    tenant_id: str = Depends(get_tenant_id),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Execute a compiled pipeline in isolated sandbox.
    
    Streams execution status + preview data via Server-Sent Events.
    """
    
    async def event_generator():
        try:
            # Load pipeline
            pipeline_graph = GPCPipelineGraph(
                pipeline_id=pipeline_id,
                tenant_id=tenant_id
            )
            
            # Compile
            compiler = GPCCompiler()
            compilation = compiler.compile(pipeline_graph)
            
            if not compilation.success:
                yield f"data: {json.dumps({'error': 'Compilation failed', 'warnings': compilation.warnings})}\n\n"
                return
            
            # Emit start event
            yield f"data: {json.dumps({'event': 'start', 'node_count': compilation.node_count})}\n\n"
            
            # Execute nodes in order (mock)
            for i, node_id in enumerate(compilation.execution_order):
                yield f"data: {json.dumps({'event': 'node_start', 'node_id': node_id, 'index': i})}\n\n"
                
                # Mock: sleep to simulate execution
                await asyncio.sleep(0.5)
                
                # Mock preview data
                preview = {
                    "rows": 100 + i * 50,
                    "columns": ["id", "name", "value"],
                    "sample": [[i, f"row_{i}", f"val_{i}"] for i in range(3)]
                }
                
                yield f"data: {json.dumps({'event': 'node_complete', 'node_id': node_id, 'preview': preview})}\n\n"
            
            # Emit completion
            yield f"data: {json.dumps({'event': 'complete', 'success': True})}\n\n"
            
            # Log execution trace
            trace = PipelineExecutionTrace(
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                user_id="system",
                execution_status="success",
                data_residency_region="ca-central-1",
                schema_version="1.0"
            )
            logger.info(f"Pipeline execution completed", extra=trace.model_dump())
        
        except Exception as e:
            logger.exception(f"Pipeline execution failed: {e}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


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
    
    # Mock component definitions
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
    # In production: query audit log database
    # Mock response
    start_date = datetime.utcnow() - timedelta(days=days)
    
    events = [
        {
            "trace_id": f"trace_{i}",
            "tenant_id": tenant_id,
            "pipeline_id": pipeline_id or f"pipeline_{i}",
            "user_id": user_id or f"user_{i}",
            "execution_status": "success" if i % 2 == 0 else "failure",
            "started_at": (start_date + timedelta(hours=i)).isoformat(),
            "duration_ms": 1000 + i * 100,
            "nodes_executed": 5,
            "data_residency_region": "ca-central-1"
        }
        for i in range(10)
    ]
    
    return {
        "total": len(events),
        "events": events,
        "query_date": datetime.utcnow().isoformat(),
        "tenant_id": tenant_id
    }


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
    # In production: query metrics database
    # Mock response
    return {
        "plans_total": 42,
        "runs_total": 156,
        "decisions": {
            "approved": 148,
            "blocked": 8
        },
        "avg_compile_time_ms": 234,
        "avg_execution_time_ms": 2890,
        "success_rate": 0.945
    }
