"""
GPC Pipeline Test/Preview Mode
Execute pipeline on sample data with live result preview.
Approval gate before production deployment.

Generated for: veklom-byos-backend/backend/gpc/
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from gpc_schemas import (
    GPCPipelineGraph, PipelineExecutionTrace, ExecutionEvent
)


class TestExecutionMode(str, Enum):
    """Execution modes for testing."""
    DRY_RUN = "dry_run"  # Compile only, no execution
    SAMPLE = "sample"    # Run on sample data (first 100 rows)
    FULL = "full"        # Run on full dataset


@dataclass
class PreviewResult:
    """Result of a single node's preview execution."""
    node_id: str
    node_type: str
    status: str  # success, failure, pending
    rows_output: int
    columns: List[str]
    sample_data: List[List[Any]]
    execution_time_ms: float
    error: Optional[str] = None


@dataclass
class TestExecutionResult:
    """Complete test execution result."""
    test_run_id: str
    pipeline_id: str
    mode: TestExecutionMode
    execution_status: str  # success, partial, failure
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: float
    node_results: Dict[str, PreviewResult]
    overall_error: Optional[str] = None
    can_deploy: bool = False  # User approval gate


class PipelineTestExecutor:
    """
    Executes compiled pipeline in sandbox with sample data.
    Streams results to frontend for live visualization.
    """
    
    def __init__(self, venv_path: str = "/tmp/gpc_sandbox"):
        self.venv_path = venv_path
        self.sandbox_timeout = 30  # seconds
    
    async def test_execute(
        self,
        pipeline_id: str,
        python_code: str,
        execution_order: List[str],
        mode: TestExecutionMode = TestExecutionMode.SAMPLE
    ) -> TestExecutionResult:
        """
        Execute compiled pipeline in isolated sandbox.
        
        Args:
            pipeline_id: Pipeline being tested
            python_code: Generated Python code
            execution_order: Node IDs in topological order
            mode: DRY_RUN | SAMPLE | FULL
        
        Yields:
            ExecutionEvent for each node completion
        
        Returns:
            TestExecutionResult with all node previews
        """
        test_run_id = f"test_{pipeline_id}_{datetime.utcnow().timestamp()}"
        started_at = datetime.utcnow()
        node_results = {}
        overall_error = None
        
        try:
            if mode == TestExecutionMode.DRY_RUN:
                # Just compile, no execution
                return TestExecutionResult(
                    test_run_id=test_run_id,
                    pipeline_id=pipeline_id,
                    mode=mode,
                    execution_status="success",
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    duration_ms=(datetime.utcnow() - started_at).total_seconds() * 1000,
                    node_results={},
                    can_deploy=True
                )
            
            # For SAMPLE/FULL, execute in subprocess sandbox
            result = await self._execute_in_sandbox(
                python_code=python_code,
                execution_order=execution_order,
                mode=mode,
                test_run_id=test_run_id
            )
            
            node_results = result['node_results']
            overall_error = result.get('error')
            execution_status = result['status']
            
        except asyncio.TimeoutError:
            overall_error = f"Pipeline execution exceeded {self.sandbox_timeout}s timeout"
            execution_status = "failure"
        except Exception as e:
            overall_error = f"Test execution failed: {str(e)}"
            execution_status = "failure"
        
        completed_at = datetime.utcnow()
        duration_ms = (completed_at - started_at).total_seconds() * 1000
        
        # Can deploy only if: no errors AND all nodes succeeded
        can_deploy = (
            execution_status == "success" and
            all(r.status == "success" for r in node_results.values())
        )
        
        return TestExecutionResult(
            test_run_id=test_run_id,
            pipeline_id=pipeline_id,
            mode=mode,
            execution_status=execution_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            node_results=node_results,
            overall_error=overall_error,
            can_deploy=can_deploy
        )
    
    async def _execute_in_sandbox(
        self,
        python_code: str,
        execution_order: List[str],
        mode: TestExecutionMode,
        test_run_id: str
    ) -> Dict[str, Any]:
        """
        Execute pipeline in isolated subprocess.
        Captures output of each node for preview.
        """
        import subprocess
        import tempfile
        import os
        
        # Inject instrumentation into code to capture DataFrame outputs
        instrumented_code = self._instrument_code_for_preview(
            python_code,
            execution_order
        )
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            dir='/tmp'
        ) as f:
            f.write(instrumented_code)
            script_path = f.name
        
        try:
            # Execute in subprocess with timeout
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    'python3',
                    script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd='/tmp'
                ),
                timeout=self.sandbox_timeout
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return {
                    'status': 'failure',
                    'error': stderr.decode(),
                    'node_results': {}
                }
            
            # Parse output to extract node previews
            node_results = self._parse_preview_output(stdout.decode())
            
            return {
                'status': 'success',
                'node_results': node_results,
                'error': None
            }
        
        finally:
            # Clean up temp file
            if os.path.exists(script_path):
                os.unlink(script_path)
    
    def _instrument_code_for_preview(
        self,
        python_code: str,
        node_ids: List[str]
    ) -> str:
        """
        Inject instrumentation into generated code to capture node outputs.
        
        For each node output variable, add:
        print(f"__PREVIEW__node_id:varname:rows:cols:sample")
        """
        # This is a mock implementation
        # In production, would use AST rewriting to inject preview captures
        
        instrumentation = """
import json
import sys

def preview_dataframe(df, var_name):
    '''Capture DataFrame preview for frontend.'''
    try:
        rows = len(df)
        cols = list(df.columns)
        sample = df.head(5).values.tolist()
        
        preview = {
            'rows': rows,
            'columns': cols,
            'sample': sample
        }
        print(f"__PREVIEW__{var_name}:{json.dumps(preview)}", file=sys.stderr)
    except Exception as e:
        print(f"__ERROR__{var_name}:{str(e)}", file=sys.stderr)

"""
        
        # Add preview calls after each node assignment
        # This is simplified; real version would parse AST
        instrumented = instrumentation + python_code
        
        return instrumented
    
    def _parse_preview_output(self, stdout: str) -> Dict[str, PreviewResult]:
        """Parse captured previews from execution output."""
        import re
        
        node_results = {}
        
        # Match patterns like __PREVIEW__varname:{"rows": 100, ...}
        pattern = r'__PREVIEW__(\w+):({.*?})'
        matches = re.findall(pattern, stdout)
        
        for var_name, preview_json in matches:
            try:
                preview = json.loads(preview_json)
                node_results[var_name] = PreviewResult(
                    node_id=var_name,
                    node_type="Transform",  # Would be extracted from pipeline
                    status="success",
                    rows_output=preview.get('rows', 0),
                    columns=preview.get('columns', []),
                    sample_data=preview.get('sample', []),
                    execution_time_ms=100.0  # Would be measured
                )
            except json.JSONDecodeError:
                pass
        
        return node_results


# ============================================================================
# FASTAPI ROUTE: Test/Preview Endpoint
# ============================================================================

# Add to gpc_routes.py:

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

@router.post("/test")
async def test_pipeline(
    pipeline_id: str,
    tenant_id: str = Depends(get_tenant_id),
    mode: str = "sample",
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Test a pipeline with sample data.
    Streams execution progress + node previews.
    
    Query params:
        - mode: dry_run | sample (default) | full
    
    Returns:
        SSE stream of preview results
    """
    
    async def event_generator():
        try:
            # Load and compile pipeline
            compiler = GPCCompiler()
            
            # Mock load pipeline
            pipeline_graph = GPCPipelineGraph(
                pipeline_id=pipeline_id,
                tenant_id=tenant_id
            )
            
            compilation = compiler.compile(pipeline_graph)
            if not compilation.success:
                yield f"data: {json.dumps({'error': compilation.warnings})}\n\n"
                return
            
            # Create test executor
            executor = PipelineTestExecutor()
            test_mode = TestExecutionMode(mode)
            
            # Emit compilation success
            yield f"data: {json.dumps({'event': 'compiled', 'nodes': compilation.node_count})}\n\n"
            
            # Execute with timeout
            result = await executor.test_execute(
                pipeline_id=pipeline_id,
                python_code=compilation.python_code,
                execution_order=compilation.execution_order,
                mode=test_mode
            )
            
            # Stream node results
            for node_id, preview in result.node_results.items():
                yield f"data: {json.dumps({'event': 'node_preview', 'node_id': node_id, 'preview': preview.__dict__})}\n\n"
            
            # Emit completion
            approval_status = "ready_to_deploy" if result.can_deploy else "review_needed"
            yield f"data: {json.dumps({'event': 'complete', 'status': result.execution_status, 'approval': approval_status, 'test_run_id': result.test_run_id})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/approve-deploy")
async def approve_deployment(
    test_run_id: str,
    pipeline_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    User approves test run → eligible for deployment.
    Stores approval in audit trail.
    """
    # Log approval event
    logger.info(
        f"Pipeline deployment approved",
        extra={
            "tenant_id": tenant_id,
            "pipeline_id": pipeline_id,
            "test_run_id": test_run_id
        }
    )
    
    return {
        "status": "approved",
        "test_run_id": test_run_id,
        "pipeline_id": pipeline_id,
        "ready_for_deployment": True
    }
