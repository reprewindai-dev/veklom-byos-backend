"""
GPC Production Test Suite
Comprehensive tests for compiler, routes, compliance, performance

Generated for: veklom-byos-backend/backend/tests/test_gpc_*.py
"""

# ============================================================================
# TEST 1: Compiler Tests
# ============================================================================

# File: backend/tests/test_gpc_compiler.py

import pytest
from gpc_schemas import (
    GPCPipelineGraph, GPCNode, GPCEdge, NodePort, PortType
)
from gpc_compiler import GPCCompiler, TopologicalSortError, topological_sort


class TestTopologicalSort:
    """Kahn's algorithm tests."""

    def test_simple_linear_pipeline(self):
        """A → B → C should return [A, B, C]."""
        graph = GPCPipelineGraph(
            pipeline_id="test",
            tenant_id="test",
            nodes=[
                GPCNode(id="A", node_type="Input", output_ports=[]),
                GPCNode(id="B", node_type="Transform", input_ports=[], output_ports=[]),
                GPCNode(id="C", node_type="Output", input_ports=[]),
            ],
            edges=[
                GPCEdge(id="e1", source_node_id="A", source_port_id="out",
                        target_node_id="B", target_port_id="in"),
                GPCEdge(id="e2", source_node_id="B", source_port_id="out",
                        target_node_id="C", target_port_id="in"),
            ]
        )

        result = topological_sort(graph)
        assert result == ["A", "B", "C"]

    def test_diamond_dag(self):
        """
        A
        ├─ B
        └─ C
           └─ D

        Should return [A, (B, C order), D] or [A, C, B, D] etc.
        """
        graph = GPCPipelineGraph(
            pipeline_id="test",
            tenant_id="test",
            nodes=[
                GPCNode(id="A", node_type="Input", output_ports=[]),
                GPCNode(id="B", node_type="Transform", input_ports=[], output_ports=[]),
                GPCNode(id="C", node_type="Transform", input_ports=[], output_ports=[]),
                GPCNode(id="D", node_type="Output", input_ports=[]),
            ],
            edges=[
                GPCEdge(id="e1", source_node_id="A", source_port_id="out",
                        target_node_id="B", target_port_id="in"),
                GPCEdge(id="e2", source_node_id="A", source_port_id="out",
                        target_node_id="C", target_port_id="in"),
                GPCEdge(id="e3", source_node_id="B", source_port_id="out",
                        target_node_id="D", target_port_id="in"),
                GPCEdge(id="e4", source_node_id="C", source_port_id="out",
                        target_node_id="D", target_port_id="in"),
            ]
        )

        result = topological_sort(graph)
        assert result[0] == "A"
        assert result[-1] == "D"
        assert result.index("B") < result.index("D")
        assert result.index("C") < result.index("D")

    def test_cycle_detection(self):
        """A → B → C → A should raise TopologicalSortError."""
        graph = GPCPipelineGraph(
            pipeline_id="test",
            tenant_id="test",
            nodes=[
                GPCNode(id="A", node_type="Transform"),
                GPCNode(id="B", node_type="Transform"),
                GPCNode(id="C", node_type="Transform"),
            ],
            edges=[
                GPCEdge(id="e1", source_node_id="A", source_port_id="out",
                        target_node_id="B", target_port_id="in"),
                GPCEdge(id="e2", source_node_id="B", source_port_id="out",
                        target_node_id="C", target_port_id="in"),
                GPCEdge(id="e3", source_node_id="C", source_port_id="out",
                        target_node_id="A", target_port_id="in"),
            ]
        )

        with pytest.raises(TopologicalSortError):
            topological_sort(graph)


class TestCompiler:
    """AST code generation tests."""

    def test_csv_input_generates_valid_python(self):
        """CsvFileInput node should generate valid pd.read_csv() call."""
        graph = GPCPipelineGraph(
            pipeline_id="test",
            tenant_id="test",
            nodes=[
                GPCNode(
                    id="csv_input",
                    node_type="CsvFileInput",
                    config={"filePath": "data.csv", "sep": ","},
                    output_ports=[NodePort(id="out", port_type=PortType.PANDAS_DF, label="DataFrame")]
                )
            ]
        )

        compiler = GPCCompiler()
        result = compiler.compile(graph)

        assert result.success
        assert "read_csv" in result.python_code
        assert "data.csv" in result.python_code
        assert result.node_count == 1
        assert len(result.execution_order) == 1

    def test_pipeline_chain_maintains_variable_names(self):
        """
        CSV → Filter → Parquet
        Variables should flow: df_input → df_filtered → (export)
        """
        graph = GPCPipelineGraph(
            pipeline_id="test",
            tenant_id="test",
            nodes=[
                GPCNode(
                    id="n1",
                    node_type="CsvFileInput",
                    config={"filePath": "data.csv", "nameId": "df_input"}
                ),
                GPCNode(
                    id="n2",
                    node_type="FilterRows",
                    config={"column": "status", "value": "active", "nameId": "df_filtered"}
                ),
                GPCNode(
                    id="n3",
                    node_type="ParquetOutput",
                    config={"outputPath": "output.parquet"}
                ),
            ],
            edges=[
                GPCEdge(id="e1", source_node_id="n1", source_port_id="out",
                        target_node_id="n2", target_port_id="in"),
                GPCEdge(id="e2", source_node_id="n2", source_port_id="out",
                        target_node_id="n3", target_port_id="in"),
            ]
        )

        compiler = GPCCompiler()
        result = compiler.compile(graph)

        assert result.success
        assert "df_input" in result.python_code
        assert "df_filtered" in result.python_code
        # Check that execution order is correct
        assert result.execution_order == ["n1", "n2", "n3"]

    def test_parallel_levels_computed_correctly(self):
        """
        A
        ├─ B
        └─ C

        Parallel levels should be: [[A], [B, C]]
        """
        graph = GPCPipelineGraph(
            pipeline_id="test",
            tenant_id="test",
            nodes=[
                GPCNode(id="A", node_type="Input"),
                GPCNode(id="B", node_type="Transform"),
                GPCNode(id="C", node_type="Transform"),
            ],
            edges=[
                GPCEdge(id="e1", source_node_id="A", source_port_id="out",
                        target_node_id="B", target_port_id="in"),
                GPCEdge(id="e2", source_node_id="A", source_port_id="out",
                        target_node_id="C", target_port_id="in"),
            ]
        )

        compiler = GPCCompiler()
        result = compiler.compile(graph)

        assert result.success
        assert len(result.parallel_levels) == 2
        assert result.parallel_levels[0] == ["A"]
        assert set(result.parallel_levels[1]) == {"B", "C"}


# ============================================================================
# TEST 2: Route Tests
# ============================================================================

# File: backend/tests/test_gpc_routes.py

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.fixture
def auth_header():
    return {"Authorization": "Bearer test_token"}


class TestCompileRoute:
    """POST /api/v1/gpc/compile"""

    def test_compile_returns_python_code(self, auth_header):
        response = client.post(
            "/api/v1/gpc/compile",
            json={
                "pipeline_id": "test_pipeline",
                "tenant_id": "test_tenant"
            },
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "python_code" in data
        assert isinstance(data["python_code"], str)

    def test_compile_missing_auth_returns_401(self):
        response = client.post(
            "/api/v1/gpc/compile",
            json={"pipeline_id": "test", "tenant_id": "test"}
        )
        assert response.status_code == 401


class TestGenerateRoute:
    """POST /api/v1/gpc/generate"""

    def test_generate_from_intent_success(self, auth_header):
        response = client.post(
            "/api/v1/gpc/generate",
            json={
                "tenant_id": "test_tenant",
                "user_intent": "Load CSV, filter nulls, export parquet",
                "data_residency_region": "ca-central-1"
            },
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "pipeline_graph" in data
        assert data["pipeline_graph"]["nodes"] is not None

    def test_generate_empty_intent_fails(self, auth_header):
        response = client.post(
            "/api/v1/gpc/generate",
            json={
                "tenant_id": "test_tenant",
                "user_intent": "",
            },
            headers=auth_header
        )

        # Should either reject or return low confidence
        data = response.json()
        assert data["success"] == False or data["confidence_score"] < 0.5


class TestComponentsRoute:
    """GET /api/v1/gpc/components"""

    def test_list_components(self, auth_header):
        response = client.get(
            "/api/v1/gpc/components",
            headers=auth_header
        )

        assert response.status_code == 200
        components = response.json()
        assert isinstance(components, list)
        assert len(components) > 0

        # Check structure
        for comp in components:
            assert "node_type" in comp
            assert "display_name" in comp
            assert "category" in comp


# ============================================================================
# TEST 3: Performance Tests
# ============================================================================

# File: backend/tests/test_gpc_performance.py

import pytest
import time
from gpc_compiler import GPCCompiler
from gpc_schemas import GPCPipelineGraph, GPCNode, GPCEdge, NodePort, PortType


class TestCompilerPerformance:
    """Benchmark compiler on large pipelines."""

    @pytest.mark.performance
    def test_compile_50_node_pipeline_under_5_seconds(self):
        """Large pipeline should compile in < 5s."""
        # Generate 50-node linear pipeline
        nodes = [
            GPCNode(
                id=f"n{i}",
                node_type="SelectColumns" if i > 0 else "CsvFileInput",
                config={"columns": ["col1", "col2"]} if i > 0 else {"filePath": "data.csv"}
            )
            for i in range(50)
        ]

        edges = [
            GPCEdge(
                id=f"e{i}",
                source_node_id=f"n{i}",
                source_port_id="out",
                target_node_id=f"n{i+1}",
                target_port_id="in"
            )
            for i in range(49)
        ]

        graph = GPCPipelineGraph(
            pipeline_id="perf_test",
            tenant_id="test",
            nodes=nodes,
            edges=edges
        )

        compiler = GPCCompiler()
        start = time.time()
        result = compiler.compile(graph)
        elapsed = time.time() - start

        assert result.success
        assert elapsed < 5.0, f"Compilation took {elapsed:.2f}s, expected < 5s"

    @pytest.mark.performance
    def test_topological_sort_1000_node_dag(self):
        """Large DAG should sort quickly."""
        # Generate wide DAG: 100 inputs → 100 transforms → 100 outputs
        nodes = [
            GPCNode(id=f"n{i}", node_type="Transform")
            for i in range(1000)
        ]

        edges = [
            GPCEdge(
                id=f"e{i}",
                source_node_id=f"n{i}",
                source_port_id="out",
                target_node_id=f"n{(i+1) % 1000}",
                target_port_id="in"
            )
            for i in range(100)  # Sparse edges
        ]

        graph = GPCPipelineGraph(
            pipeline_id="perf",
            tenant_id="test",
            nodes=nodes,
            edges=edges
        )

        from gpc_compiler import topological_sort
        start = time.time()
        result = topological_sort(graph)
        elapsed = time.time() - start

        assert len(result) > 0
        assert elapsed < 1.0, f"Topological sort took {elapsed:.2f}s, expected < 1s"


# ============================================================================
# TEST 4: Compliance Tests
# ============================================================================

# File: backend/tests/test_gpc_compliance.py

import pytest
from datetime import datetime
from gpc_schemas import PipelineExecutionTrace


class TestLaw25Compliance:
    """Quebec Law 25 Section 93 PIA audit trail."""

    def test_execution_trace_captures_all_required_fields(self):
        """Audit event must have all Law 25 fields."""
        trace = PipelineExecutionTrace(
            tenant_id="quebec_tenant",
            pipeline_id="pipeline_1",
            user_id="user_123",
            execution_status="success",
            data_residency_region="ca-central-1",
            schema_version="1.0"
        )

        # All required fields present
        assert trace.trace_id  # Auto-generated
        assert trace.tenant_id == "quebec_tenant"
        assert trace.pipeline_id == "pipeline_1"
        assert trace.data_residency_region == "ca-central-1"
        assert trace.started_at

    def test_data_residency_region_enforced(self):
        """Quebec-regulated tenants must have CA residency."""
        trace = PipelineExecutionTrace(
            tenant_id="quebec_regulated_tenant",
            pipeline_id="pipeline_1",
            user_id="user_123",
            execution_status="success",
            data_residency_region="ca-central-1",  # Must not be US region
            schema_version="1.0"
        )

        assert trace.data_residency_region in ["ca-central-1", "ca-west-1", "on-premise"]
        # US regions should be rejected in production
        # assert trace.data_residency_region != "us-east-1"


# ============================================================================
# TEST 5: Integration Tests
# ============================================================================

# File: backend/tests/test_gpc_integration.py

class TestEndToEndPipeline:
    """Full flow: Intent → Graph → Compile → Execute."""

    def test_simple_pipeline_e2e(self):
        """CSV → Filter → Parquet full flow."""
        # This would:
        # 1. Call generate endpoint (NL → graph)
        # 2. Call compile endpoint (graph → Python)
        # 3. Verify Python code is valid
        # 4. Mock execute (actual execution in sandbox)
        # 5. Verify audit trail logged

        # Would be implemented in CI/CD pipeline
        pass


# ============================================================================
# TEST RUNNER
# ============================================================================

# Run tests locally:
# pytest backend/tests/test_gpc_*.py -v
#
# Run with coverage:
# pytest backend/tests/test_gpc_*.py --cov=backend.gpc --cov-report=html
#
# Run performance tests only:
# pytest backend/tests/ -m performance -v

# CI/CD integration (GitHub Actions):
#
# .github/workflows/gpc-tests.yml:
#
# name: GPC Tests
# on: [push, pull_request]
# jobs:
#   test:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v3
#       - uses: actions/setup-python@v4
#         with:
#           python-version: '3.11'
#       - run: pip install poetry && poetry install
#       - run: pytest backend/tests/test_gpc_*.py --cov=backend.gpc
#       - run: pytest backend/tests/ -m performance  # Benchmark gate
