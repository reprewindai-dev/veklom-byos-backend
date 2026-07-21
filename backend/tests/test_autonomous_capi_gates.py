import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import uuid
import json

from backend.core.services.autonomous_worker import (
    _evaluate_intent_with_capi,
    _execute_pipeline_node,
    run_gpc_background
)
from backend.db.models.agent import AgentIdentity, AgentTrustScore
from backend.db.models.authority import AuthorityBundle, AuthorityRun
from backend.db.models.pipelines import PipelineRun
from backend.apps.api.routers.capi import ExecutionIntent

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db

@pytest.fixture
def sample_agent():
    return AgentIdentity(
        id="agent-bg-001",
        tenant_id="test-workspace",
        name="Test Background Agent",
        created_by_pgl_id="system",
        metadata_json={"trust_score": 85}
    )

@pytest.fixture
def sample_bundle():
    return AuthorityBundle(
        id="bundle-bg-001",
        name="Default cAPI Bundle",
        version="1.0",
        workspace_id="test-workspace",
        creator_id="system",
        tool_permissions={
            "pipeline_step": "ALLOW",
            "gpc_step": "ALLOW",
            "fs.read": "ALLOW",
            "fs.write": "DENY"  # Denied to test vetoing
        },
        workspace_restrictions={},
        time_restrictions={},
        risk_level="medium",
        is_active=True
    )

@pytest.fixture
def sample_run():
    return AuthorityRun(
        id="run-bg-001",
        authority_bundle_id="bundle-bg-001",
        agent_id="agent-bg-001",
        workspace_id="test-workspace",
        executor_id="system",
        status="active",
        decisions=[],
        violations=[],
        total_actions=0,
        approved_actions=0,
        denied_actions=0,
        violation_count=0
    )

@pytest.mark.anyio
async def test_evaluate_intent_without_amphoteric_context_is_blocked(mock_db, sample_agent, sample_bundle, sample_run):
    # Mock database queries to return our test agent, bundle, and run
    async def mock_execute(query):
        mock_val = MagicMock()
        # Compile query to check table names
        q_str = str(query)
        if "agent_identities" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_agent
        elif "authority_bundles" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_bundle
        elif "authority_runs" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_run
        else:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    with pytest.raises(ValueError, match="MISSING_AMPHOTERIC_CONTEXT"):
        await _evaluate_intent_with_capi(
            agent_id="agent-bg-001",
            action="fs.read",
            target_protocol="pipeline_step",
            payload={"path": "/app/config.json"},
            workspace_id="test-workspace",
            db=mock_db,
        )

    assert sample_run.approved_actions == 0
    assert sample_run.total_actions == 1
    assert sample_run.denied_actions == 1
    assert sample_agent.metadata_json["trust_score"] == 75

@pytest.mark.anyio
async def test_evaluate_intent_with_capi_denied(mock_db, sample_agent, sample_bundle, sample_run):
    async def mock_execute(query):
        mock_val = MagicMock()
        q_str = str(query)
        if "agent_identities" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_agent
        elif "authority_bundles" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_bundle
        elif "authority_runs" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_run
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    # fs.write is configured to "DENY" in our sample_bundle
    with pytest.raises(ValueError) as exc_info:
        await _evaluate_intent_with_capi(
            agent_id="agent-bg-001",
            action="fs.write",
            target_protocol="pipeline_step",
            payload={"path": "/app/secret.txt"},
            workspace_id="test-workspace",
            db=mock_db
        )

    assert "cAPI GATING VETO" in str(exc_info.value)
    assert sample_run.denied_actions == 1
    assert sample_run.violation_count == 1
    # Check self-learning trust score penalty (degrade trust score)
    assert sample_agent.metadata_json["trust_score"] == 75

@pytest.mark.anyio
@patch("backend.core.services.autonomous_worker.get_db_session")
async def test_execute_pipeline_node_without_context_is_blocked(mock_get_db, mock_db, sample_agent, sample_bundle, sample_run):
    mock_get_db.return_value.__aenter__.return_value = mock_db
    
    async def mock_execute(query):
        mock_val = MagicMock()
        q_str = str(query)
        if "agent_identities" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_agent
        elif "authority_bundles" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_bundle
        elif "authority_runs" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_run
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    step = {
        "node_type": "input",
        "config": {"text": "Hello sovereign runtime"},
        "agent_id": "agent-bg-001"
    }
    context = {
        "workspace_id": "test-workspace",
        "text": ""
    }

    with pytest.raises(ValueError, match="MISSING_AMPHOTERIC_CONTEXT"):
        await _execute_pipeline_node(step, context)
    assert context["text"] == ""
    assert sample_run.approved_actions == 0

@pytest.mark.anyio
@patch("backend.core.services.autonomous_worker._update_job_state")
@patch("backend.core.services.autonomous_worker.run_completion")
@patch("backend.core.services.autonomous_worker.get_db_session")
async def test_run_gpc_background_gated(mock_get_db, mock_run_comp, mock_update_job, mock_db, sample_agent, sample_bundle, sample_run):
    mock_get_db.return_value.__aenter__.return_value = mock_db
    
    async def mock_execute(query):
        mock_val = MagicMock()
        q_str = str(query)
        if "agent_identities" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_agent
        elif "authority_bundles" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_bundle
        elif "authority_runs" in q_str:
            mock_val.scalar_one_or_none.return_value = sample_run
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)
    
    # Mock LLM completion
    mock_comp_res = MagicMock()
    mock_comp_res.provider = "openai"
    mock_comp_res.payload = {"choices": [{"message": {"content": "GPC dynamic evaluation success"}}]}
    mock_run_comp.return_value = mock_comp_res

    graph = {
        "nodes": [
            {"id": "node-gpc-1", "description": "Verify security checklist"}
        ]
    }

    await run_gpc_background(
        transaction_id="gpc-tx-123",
        graph=graph,
        workspace_id="test-workspace",
        user_id="user-gpc",
        provider="openai",
        model="gpt-4o"
    )

    # Missing verified transport context must prevent execution.
    assert sample_run.approved_actions == 0

    blocked_calls = [
        args[1] for args, kwargs in mock_update_job.call_args_list
        if args[0] == "gpc-tx-123" and args[1].get("status") == "FAILED"
    ]
    assert len(blocked_calls) > 0
