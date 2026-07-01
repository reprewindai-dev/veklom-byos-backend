import pytest
import ast
from backend.gpc.gpc_schemas import GPCPipelineGraph, GPCNode, GPCEdge, PortType, NodePort
from backend.gpc.gpc_compiler import GPCCompiler, topological_sort, TopologicalSortError


def test_topological_sort_linear():
    """Verify that linear DAG sorts in exact dependent order."""
    # n1 -> n2 -> n3
    n1 = GPCNode(id="n1", node_type="CsvFileInput", label="Load", config={})
    n2 = GPCNode(id="n2", node_type="FilterRows", label="Filter", config={})
    n3 = GPCNode(id="n3", node_type="ParquetOutput", label="Save", config={})
    
    e1 = GPCEdge(id="e1", source_node_id="n1", source_port_id="out", target_node_id="n2", target_port_id="in")
    e2 = GPCEdge(id="e2", source_node_id="n2", source_port_id="out", target_node_id="n3", target_port_id="in")
    
    graph = GPCPipelineGraph(
        pipeline_id="linear-test",
        tenant_id="test_tenant",
        nodes=[n1, n2, n3],
        edges=[e1, e2]
    )
    
    order = topological_sort(graph)
    assert order == ["n1", "n2", "n3"]


def test_topological_sort_cycle():
    """Verify that a cycle is detected and raises TopologicalSortError."""
    # n1 -> n2 -> n1
    n1 = GPCNode(id="n1", node_type="FilterRows", config={})
    n2 = GPCNode(id="n2", node_type="FilterRows", config={})
    
    e1 = GPCEdge(id="e1", source_node_id="n1", source_port_id="out", target_node_id="n2", target_port_id="in")
    e2 = GPCEdge(id="e2", source_node_id="n2", source_port_id="out", target_node_id="n1", target_port_id="in")
    
    graph = GPCPipelineGraph(
        pipeline_id="cycle-test",
        tenant_id="test_tenant",
        nodes=[n1, n2],
        edges=[e1, e2]
    )
    
    with pytest.raises(TopologicalSortError):
        topological_sort(graph)


def test_gpc_compiler_compilation():
    """Verify that GPCCompiler successfully generates structurally sound, syntax-valid Python code."""
    n1 = GPCNode(
        id="node_1",
        node_type="CsvFileInput",
        label="Load Customers",
        config={"filePath": "customers.csv", "sep": ","},
        output_ports=[NodePort(id="out", port_type=PortType.PANDAS_DF, label="DataFrame")]
    )
    n2 = GPCNode(
        id="node_2",
        node_type="FilterRows",
        label="Filter Active",
        config={"column": "status", "value": "active"},
        input_ports=[NodePort(id="in", port_type=PortType.PANDAS_DF, label="DataFrame")],
        output_ports=[NodePort(id="out", port_type=PortType.PANDAS_DF, label="DataFrame")]
    )
    n3 = GPCNode(
        id="node_3",
        node_type="Aggregate",
        label="Group by Country",
        config={"groupBy": "country", "aggregateColumn": "id", "aggregateFunction": "count"},
        input_ports=[NodePort(id="in", port_type=PortType.PANDAS_DF, label="DataFrame")],
        output_ports=[NodePort(id="out", port_type=PortType.PANDAS_DF, label="DataFrame")]
    )
    n4 = GPCNode(
        id="node_4",
        node_type="ParquetOutput",
        label="Save Parquet",
        config={"outputPath": "results.parquet"},
        input_ports=[NodePort(id="in", port_type=PortType.PANDAS_DF, label="DataFrame")]
    )
    
    edges = [
        GPCEdge(id="e1", source_node_id="node_1", source_port_id="out", target_node_id="node_2", target_port_id="in"),
        GPCEdge(id="e2", source_node_id="node_2", source_port_id="out", target_node_id="node_3", target_port_id="in"),
        GPCEdge(id="e3", source_node_id="node_3", source_port_id="out", target_node_id="node_4", target_port_id="in")
    ]
    
    graph = GPCPipelineGraph(
        pipeline_id="gpc-comp-test",
        tenant_id="test_tenant",
        nodes=[n1, n2, n3, n4],
        edges=edges
    )
    
    compiler = GPCCompiler()
    result = compiler.compile(graph)
    
    assert result.success is True
    assert result.node_count == 4
    assert len(result.python_code) > 0
    
    # Assert generated code is valid syntax
    parsed_ast = ast.parse(result.python_code)
    assert parsed_ast is not None
    
    # Check that required library imports and operations are correctly synthesized
    assert "import pandas as pd" in result.python_code
    assert "read_csv('customers.csv'" in result.python_code
    assert "status" in result.python_code
    assert "active" in result.python_code
    assert "groupby('country')" in result.python_code
    assert "to_parquet('results.parquet')" in result.python_code


def test_gpc_compiler_duckdb_query():
    """Verify code generation for DuckDB query node."""
    n1 = GPCNode(
        id="n1",
        node_type="CsvFileInput",
        config={"filePath": "input.csv"},
        output_ports=[NodePort(id="out", port_type=PortType.PANDAS_DF, label="DataFrame")]
    )
    n2 = GPCNode(
        id="n2",
        node_type="DuckDBQuery",
        config={"sqlQuery": "SELECT * FROM n1_out WHERE age > 30"},
        input_ports=[NodePort(id="in", port_type=PortType.PANDAS_DF, label="DataFrame")],
        output_ports=[NodePort(id="out", port_type=PortType.DUCKDB_REL, label="Relation")]
    )
    
    edges = [
        GPCEdge(id="e1", source_node_id="n1", source_port_id="out", target_node_id="n2", target_port_id="in")
    ]
    
    graph = GPCPipelineGraph(
        pipeline_id="gpc-duck-test",
        tenant_id="test_tenant",
        nodes=[n1, n2],
        edges=edges
    )
    
    compiler = GPCCompiler()
    result = compiler.compile(graph)
    
    assert result.success is True
    assert "import duckdb" in result.python_code
    assert "duckdb.query(" in result.python_code
    assert "to_df()" in result.python_code
