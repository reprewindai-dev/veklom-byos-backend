"""Tests for Governance Engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.core.services.governance_engine import GovernanceEngine
from backend.db.models.agent import Agent
from backend.db.models.genome import GenomeVersion
from backend.db.models.ledger import LedgerEvent
from backend.db.models.execution_certificate import ExecutionCertificate
from backend.db.models.risk_profile import OrgRiskProfile


@pytest.mark.asyncio
@patch("backend.core.services.governance_engine.run_completion")
@patch("backend.core.services.governance_engine.guardrail_service")
async def test_run_governed_execution_success(mock_guard, mock_run):
    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[100.0, 0.0])
    
    # 1. Setup mocks
    agent = Agent(id=1, status="registered")
    genome = GenomeVersion(
        id=1,
        agent_id=1,
        version=1,
        payload={
            "model_layer": {"model": "gpt-4o-mini"},
            "prompt_layer": {"system_prompt": "Prompt system"},
            "task_profile": {"task_type": "general"}
        },
        merkle_root="root_hash_abc"
    )
    
    risk_profile = OrgRiskProfile(org_id="test_org", abuse_score=0.0, override_abuse_score=0.0, payment_risk_score=0.0, injection_attempts=0, composite_risk=0.0)
    
    # Database calls mock setup
    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query)
        if "agents" in query_str:
            mock_val.scalar_one_or_none.return_value = agent
        elif "genome_versions" in query_str:
            mock_val.scalars().first.return_value = genome
        elif "ledger_events" in query_str:
            mock_val.scalars().first.return_value = None
        elif "org_risk_profiles" in query_str:
            mock_val.scalar_one_or_none.return_value = risk_profile
        elif "policy_versions" in query_str:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val
        
    db.execute.side_effect = mock_execute
    
    # LLM completion mock
    completion_res = MagicMock()
    completion_res.payload = {
        "choices": [{"message": {"role": "assistant", "content": "Hello governed world"}}]
    }
    mock_run.return_value = completion_res
    
    # Guardrail service mock (pass validation)
    mock_guard.run_watchtowers = AsyncMock(return_value=[{"name": "pii", "passed": True}])
    mock_guard.check_tier_pass.return_value = True
    
    # 2. Run governed execution
    req = {
        "agent_id": 1,
        "prompt": "Hello",
        "role": "admin",
        "task_type": "general",
        "org_id": "test_org"
    }
    
    res = await GovernanceEngine.runGovernedExecution(db, 1, req)
    
    assert res["status"] == "completed"
    assert res["output"] == "Hello governed world"
    assert res["governance_tier"] == "T0"
    assert not res["rewrite_applied"]
    assert res["execution_certificate_jwt"] is not None


@pytest.mark.asyncio
@patch("backend.core.services.governance_engine.run_completion")
@patch("backend.core.services.governance_engine.guardrail_service")
async def test_run_governed_execution_rewrite_once_then_success(mock_guard, mock_run):
    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[100.0, 0.0])
    
    agent = Agent(id=1, status="registered")
    genome = GenomeVersion(
        id=1, agent_id=1, version=1,
        payload={"task_profile": {"task_type": "general"}},
        merkle_root="root_hash_abc"
    )
    
    risk_profile = OrgRiskProfile(org_id="test_org", abuse_score=0.0, override_abuse_score=0.0, payment_risk_score=0.0, injection_attempts=0, composite_risk=0.0)
    
    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query)
        if "agents" in query_str:
            mock_val.scalar_one_or_none.return_value = agent
        elif "genome_versions" in query_str:
            mock_val.scalars().first.return_value = genome
        elif "ledger_events" in query_str:
            mock_val.scalars().first.return_value = None
        elif "org_risk_profiles" in query_str:
            mock_val.scalar_one_or_none.return_value = risk_profile
        elif "policy_versions" in query_str:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val
        
    db.execute.side_effect = mock_execute
    
    # First and second LLM outputs
    completion_res_1 = MagicMock()
    completion_res_1.payload = {"choices": [{"message": {"role": "assistant", "content": "First output (failed)"}}]}
    
    completion_res_2 = MagicMock()
    completion_res_2.payload = {"choices": [{"message": {"role": "assistant", "content": "Second output (passed)"}}]}
    
    mock_run.side_effect = [completion_res_1, completion_res_2]
    
    # Guardrail mock outputs (fail first, pass second)
    mock_guard.run_watchtowers = AsyncMock(side_effect=[
        [{"name": "pii", "passed": False, "reason": "found PII"}],
        [{"name": "pii", "passed": True}]
    ])
    mock_guard.check_tier_pass.side_effect = [False, True]
    mock_guard.build_corrections.return_value = {
        "failed_watchtowers": ["pii"],
        "reasons": ["found PII"],
        "prompt_instructions": "Remove PII"
    }
    
    req = {
        "agent_id": 1,
        "prompt": "Hello",
        "role": "admin"
    }
    
    res = await GovernanceEngine.runGovernedExecution(db, 1, req)
    
    assert res["status"] == "completed"
    assert res["output"] == "Second output (passed)"
    assert res["rewrite_applied"] is True


@pytest.mark.asyncio
@patch("backend.core.services.governance_engine.run_completion")
@patch("backend.core.services.governance_engine.guardrail_service")
async def test_run_governed_execution_block_on_double_failure(mock_guard, mock_run):
    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[100.0, 0.0])
    
    agent = Agent(id=1, status="registered")
    genome = GenomeVersion(
        id=1, agent_id=1, version=1,
        payload={"task_profile": {"task_type": "general"}},
        merkle_root="root_hash_abc"
    )
    
    risk_profile = OrgRiskProfile(org_id="test_org", abuse_score=0.0, override_abuse_score=0.0, payment_risk_score=0.0, injection_attempts=0, composite_risk=0.0)
    
    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query)
        if "agents" in query_str:
            mock_val.scalar_one_or_none.return_value = agent
        elif "genome_versions" in query_str:
            mock_val.scalars().first.return_value = genome
        elif "ledger_events" in query_str:
            mock_val.scalars().first.return_value = None
        elif "org_risk_profiles" in query_str:
            mock_val.scalar_one_or_none.return_value = risk_profile
        elif "policy_versions" in query_str:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val
        
    db.execute.side_effect = mock_execute
    
    # Both completions return failing content
    res_mock = MagicMock()
    res_mock.payload = {"choices": [{"message": {"role": "assistant", "content": "Failed content"}}]}
    mock_run.return_value = res_mock
    
    # Both fail validation
    mock_guard.run_watchtowers = AsyncMock(return_value=[{"name": "pii", "passed": False, "reason": "found PII"}])
    mock_guard.check_tier_pass.return_value = False
    mock_guard.build_corrections.return_value = {
        "failed_watchtowers": ["pii"],
        "reasons": ["found PII"],
        "prompt_instructions": "Remove PII"
    }
    
    req = {"agent_id": 1, "prompt": "Hello", "role": "admin"}
    
    with pytest.raises(HTTPException) as exc_info:
        await GovernanceEngine.runGovernedExecution(db, 1, req)
        
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_commit_constitutional_write_blocked_and_overridden():
    db = AsyncMock()
    
    agent = Agent(id=1, status="registered")
    genome = GenomeVersion(id=1, agent_id=1, payload={}, merkle_root="root_xyz")
    
    risk_profile = OrgRiskProfile(org_id="test_org", abuse_score=0.0, override_abuse_score=0.0, payment_risk_score=0.0, injection_attempts=0, composite_risk=0.0)
    
    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query)
        if "agents" in query_str:
            mock_val.scalar_one_or_none.return_value = agent
        elif "genome_versions" in query_str:
            mock_val.scalars().first.return_value = genome
        elif "ledger_events" in query_str:
            mock_val.scalars().first.return_value = None
        elif "org_risk_profiles" in query_str:
            mock_val.scalar_one_or_none.return_value = risk_profile
        elif "policy_versions" in query_str:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val
        
    db.execute.side_effect = mock_execute
    
    # Viewer tries protected action -> Blocked without override
    with pytest.raises(HTTPException) as exc_info:
        await GovernanceEngine.commitConstitutionalWrite(
            db=db,
            agent_id=1,
            action="UPDATE_GENOME",
            write_payload={"new_config": {}},
            user_id="viewer_user",
            org_id="test_org",
            role="viewer"
        )
    assert exc_info.value.status_code == 403
    
    # Admin tries but is blocked (e.g. state check fails)
    agent.status = "revoked"
    with pytest.raises(HTTPException) as exc_info:
         await GovernanceEngine.commitConstitutionalWrite(
            db=db,
            agent_id=1,
            action="REVOKE_AGENT",
            write_payload={},
            user_id="admin_user",
            org_id="test_org",
            role="admin"
        )
    assert exc_info.value.status_code == 400
    assert "already revoked" in exc_info.value.detail
    
    # Admin executes UPDATE_GENOME with override
    agent.status = "registered"
    res = await GovernanceEngine.commitConstitutionalWrite(
        db=db,
        agent_id=1,
        action="UPDATE_GENOME",
        write_payload={"new_config": {}},
        user_id="admin_user",
        org_id="test_org",
        role="operator",
        override_requested=True,
        override_reason="Authorized upgrade"
    )
    
    assert res["status"] == "committed"
    assert res["override_applied"] is True
