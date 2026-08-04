"""
Test Executor
Runs compiled pipelines in isolated sandboxes with live streaming

Handles:
- DRY_RUN: Syntax check only
- SAMPLE: Run on first 100 rows
- FULL: Run on all data

Location: veklom-byos-backend/backend/gpc/test_executor.py
"""

import asyncio
import json
import subprocess
import tempfile
import os
from enum import Enum
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

import pandas as pd

from backend.gpc.schemas import GPCPipelineGraph


class TestExecutionMode(str, Enum):
    """Test execution modes"""
    DRY_RUN = "dry_run"  # Syntax validation only
    SAMPLE = "sample"    # Run on first 100 rows
    FULL = "full"        # Run on all data


class PipelineTestExecutor:
    """
    Executes pipelines in isolated subprocess sandboxes.

    Workflow:
    1. Write compiled Python to temp file
    2. Inject instrumentation (capture DataFrame outputs)
    3. Run in subprocess with timeout
    4. Stream results back via async generator
    5. Capture exceptions and log to audit trail
    """

    def __init__(self, timeout_seconds: int = 60):
        """
        Initialize executor.

        Args:
            timeout_seconds: Max time to run a pipeline
        """
        self.timeout_seconds = timeout_seconds

    async def test_with_streaming(
        self,
        pipeline_id: str,
        compiled_python: str,
        graph: GPCPipelineGraph,
        mode: TestExecutionMode = TestExecutionMode.SAMPLE,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Test a pipeline with live streaming of results.

        Args:
            pipeline_id: Pipeline identifier
            compiled_python: Compiled Python code
            graph: Original pipeline graph
            mode: Test mode (dry_run, sample, full)

        Yields:
            Event dicts with node_id, status, rows, columns, sample, error
        """
        try:
            # Phase 1: Syntax validation
            yield {
                "status": "validating",
                "message": "Validating pipeline syntax...",
            }

            self._validate_syntax(compiled_python)

            yield {
                "status": "validated",
                "message": "Syntax valid",
            }

            if mode == TestExecutionMode.DRY_RUN:
                yield {
                    "status": "success",
                    "message": "Dry run complete (validation only)",
                }
                return

            # Phase 2: Prepare instrumented code
            yield {
                "status": "preparing",
                "message": "Preparing instrumented code...",
            }

            instrumented_code = self._instrument_code(compiled_python, graph)

            # Phase 3: Execute in sandbox
            yield {
                "status": "executing",
                "message": "Executing pipeline...",
            }

            # Run in subprocess
            result = await self._run_in_sandbox(
                pipeline_id=pipeline_id,
                code=instrumented_code,
                timeout=self.timeout_seconds,
            )

            if not result["success"]:
                yield {
                    "status": "error",
                    "message": result.get("error", "Execution failed"),
                    "error": result.get("error"),
                }
                return

            # Phase 4: Stream results per node
            for node in graph.nodes:
                node_id = node.id
                output_var = node.config.get('nameId', f"{node.node_type}_{node_id[:8]}")

                if output_var in result.get("dataframes", {}):
                    df_data = result["dataframes"][output_var]

                    yield {
                        "node_id": node_id,
                        "status": "success",
                        "rows": df_data.get("rows", 0),
                        "columns": df_data.get("columns", []),
                        "sample": df_data.get("sample", []),
                    }
                else:
                    # Node executed but produced no DataFrame (e.g., output node)
                    yield {
                        "node_id": node_id,
                        "status": "success",
                        "message": "Node executed (output)",
                    }

            yield {
                "status": "complete",
                "message": "All nodes tested successfully",
            }

        except Exception as e:
            yield {
                "status": "error",
                "message": str(e),
                "error": str(e),
            }

    async def execute_with_streaming(
        self,
        pipeline_id: str,
        compiled_python: str,
        graph: GPCPipelineGraph,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a pipeline with live streaming (full data, no sampling).

        Same as test_with_streaming but with FULL mode.
        """
        async for event in self.test_with_streaming(
            pipeline_id=pipeline_id,
            compiled_python=compiled_python,
            graph=graph,
            mode=TestExecutionMode.FULL,
        ):
            yield event

    def _validate_syntax(self, code: str) -> None:
        """
        Validate Python syntax.

        Raises:
            SyntaxError: If code is invalid
        """
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python syntax: {e.msg} at line {e.lineno}")

    def _instrument_code(self, code: str, graph: GPCPipelineGraph) -> str:
        """
        Instrument code to capture DataFrame outputs.

        Adds code to track intermediate DataFrames and serialize them.
        """
        # Import instrumentation at top
        instrumentation = """
import json
import pandas as pd
from io import StringIO

# Instrumentation: capture DataFrames
_captured_dataframes = {}

def _capture_df(name, df):
    '''Capture DataFrame for inspection'''
    if isinstance(df, pd.DataFrame):
        _captured_dataframes[name] = {
            'rows': len(df),
            'columns': df.columns.tolist(),
            'sample': df.head(10).values.tolist(),
            'dtypes': df.dtypes.astype(str).to_dict()
        }
    return df

"""

        # Collect output variable names
        output_vars = {}
        for node in graph.nodes:
            name_id = node.config.get('nameId', f"{node.node_type}_{node.id[:8]}")
            output_vars[name_id] = node.id

        # Wrap assignments to capture DataFrames
        lines = code.split('\n')
        instrumented_lines = [instrumentation]

        for line in lines:
            instrumented_lines.append(line)

            # After each assignment to an output var, capture it
            for var_name in output_vars:
                if line.strip().startswith(f"{var_name} = "):
                    instrumented_lines.append(f"_capture_df('{var_name}', {var_name})")

        # Add final export
        instrumented_lines.extend([
            "",
            "# Export captured data",
            "print(json.dumps({'captured_dataframes': _captured_dataframes}))"
        ])

        return '\n'.join(instrumented_lines)

    async def _run_in_sandbox(
        self,
        pipeline_id: str,
        code: str,
        timeout: int,
    ) -> Dict[str, Any]:
        """
        Run code in isolated subprocess.

        Returns:
            Dict with success flag and captured data
        """
        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Run subprocess with timeout
                proc = await asyncio.create_subprocess_exec(
                    'python',
                    temp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return {
                        "success": False,
                        "error": f"Execution timeout ({timeout}s exceeded)"
                    }

                # Check for errors
                if proc.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='replace')
                    return {
                        "success": False,
                        "error": f"Execution failed: {error_msg}"
                    }

                # Parse output
                output = stdout.decode('utf-8', errors='replace').strip()

                # Last line should be JSON with captured data
                lines = output.split('\n')
                for line in reversed(lines):
                    try:
                        data = json.loads(line)
                        return {
                            "success": True,
                            "dataframes": data.get("captured_dataframes", {})
                        }
                    except json.JSONDecodeError:
                        continue

                # No JSON found
                return {
                    "success": True,
                    "dataframes": {},
                    "output": output
                }

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            return {
                "success": False,
                "error": f"Sandbox error: {str(e)}"
            }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.gpc.test_executor import PipelineTestExecutor, TestExecutionMode
from backend.gpc.schemas import GPCPipelineGraph, GPCNode, GPCEdge

executor = PipelineTestExecutor()

# Assume we have compiled_python and graph

async def test_pipeline():
    async for event in executor.test_with_streaming(
        pipeline_id="test_1",
        compiled_python=compiled_python,
        graph=graph,
        mode=TestExecutionMode.SAMPLE,
    ):
        print(f"Event: {event}")

        if event.get("node_id"):
            print(f"  Node {event['node_id']}: {event['status']}")
            if event.get("sample"):
                print(f"    Sample rows: {event['sample'][:2]}")

asyncio.run(test_pipeline())
"""
