import pytest

from backend.apps.gpc.routes import validate_gpc_request
from backend.apps.gpc.schemas import (
    GPCNode,
    GPCPipelineGraph,
    PipelineCompilationRequest,
)


def _graph(tenant_id: str = "workspace-1", pipeline_id: str = "pipeline-1"):
    return GPCPipelineGraph(
        pipeline_id=pipeline_id,
        tenant_id=tenant_id,
        nodes=[GPCNode(id="node-1", node_type="CsvFileInput")],
        edges=[],
    )


def test_compile_request_carries_the_active_graph_and_identity():
    graph = _graph()
    request = PipelineCompilationRequest(
        pipeline_id=graph.pipeline_id,
        tenant_id=graph.tenant_id,
        graph=graph,
    )

    assert request.graph == graph
    assert request.pipeline_id == graph.pipeline_id
    assert request.tenant_id == graph.tenant_id


def test_gpc_request_rejects_tenant_or_pipeline_identity_mismatch():
    request = PipelineCompilationRequest(
        pipeline_id="pipeline-1",
        tenant_id="workspace-1",
        graph=_graph(tenant_id="workspace-2", pipeline_id="pipeline-2"),
    )

    with pytest.raises(ValueError, match="tenant_id"):
        validate_gpc_request(request, authenticated_tenant_id="workspace-1")


def test_gpc_request_rejects_empty_graph_instead_of_compiling_successfully():
    graph = GPCPipelineGraph(
        pipeline_id="pipeline-1",
        tenant_id="workspace-1",
        nodes=[],
        edges=[],
    )
    request = PipelineCompilationRequest(
        pipeline_id=graph.pipeline_id,
        tenant_id=graph.tenant_id,
        graph=graph,
    )

    with pytest.raises(ValueError, match="at least one node"):
        validate_gpc_request(request, authenticated_tenant_id="workspace-1")
