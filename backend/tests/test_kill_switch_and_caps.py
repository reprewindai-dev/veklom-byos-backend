"""Tests for Global Kill Switch and Workspace-scoped Spend Caps."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Request

from backend.core.config.settings import settings
from backend.core.security.wallet_guard import token_deduction_guard
from backend.apps.api.routers.capi import evaluate_intent_governed, ExecutionIntent

@pytest.mark.asyncio
async def test_wallet_guard_global_kill_switch():
    # Set global kill switch to True
    with patch.object(settings, "GLOBAL_KILL_SWITCH", True):
        request = MagicMock(spec=Request)
        db = AsyncMock()
        user = MagicMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await token_deduction_guard(request, user, db)
            
        assert exc_info.value.status_code == 403
        assert "Emergency Kill Switch engaged" in exc_info.value.detail

@pytest.mark.asyncio
async def test_wallet_guard_default_daily_cap_exceeded():
    # Global kill switch False
    with patch.object(settings, "GLOBAL_KILL_SWITCH", False):
        request = MagicMock(spec=Request)
        request.url.path = "/v1/exec"  # Cost is 50
        
        user = MagicMock()
        user.id = "user_test"
        user.workspace_id = "workspace_test"
        
        db = AsyncMock()
        # Mock topups sum (e.g. 500.0)
        db.scalar.return_value = 500.0
        
        # Mock budget query returning empty list to trigger default caps fallback
        mock_budget_res = MagicMock()
        mock_budget_res.scalars().all.return_value = []
        db.execute.return_value = mock_budget_res
        
        # When evaluating daily defaults:
        # Sum of debits is mocked. Let's mock the sum of debits query.
        # Since it calls db.execute() for spend sum, let's return a result exceeding the daily limit ($10.0)
        # We need a custom mock for db.execute:
        # 1. Budget rules query -> return empty list
        # 2. Spend query for daily rule -> return $9.0 (exceeds $10.0 cap with $50.0 token cost)
        # 3. Spend query for weekly rule -> return $0.0
        # 4. Spend query for monthly rule -> return $0.0
        
        async def mock_execute(query):
            mock_res = MagicMock()
            query_str = str(query)
            if "budget_rules" in query_str:
                mock_res.scalars().all.return_value = []
            elif "wallet_transactions" in query_str:
                # Sum of debits query
                mock_res.scalar_one_or_none.return_value = 9.0
            return mock_res
            
        db.execute.side_effect = mock_execute
        
        with pytest.raises(HTTPException) as exc_info:
            await token_deduction_guard(request, user, db)
            
        assert exc_info.value.status_code == 402
        assert "Budget limit exceeded (Default Daily Cap)" in exc_info.value.detail

@pytest.mark.asyncio
async def test_capi_gate_global_kill_switch():
    with patch.object(settings, "GLOBAL_KILL_SWITCH", True):
        db = AsyncMock()
        
        async def mock_execute(query):
            mock_val = MagicMock()
            query_str = str(query)
            if "authority_bundles" in query_str:
                mock_bundle = MagicMock()
                mock_bundle.tool_permissions = {"filesystem.read": "ALLOW"}
                mock_bundle.time_restrictions = None
                mock_val.scalar_one_or_none.return_value = mock_bundle
            else:
                mock_agent = MagicMock()
                mock_agent.public_key = None
                mock_agent.metadata_json = {"trust_score": 90}
                mock_val.scalar_one_or_none.return_value = mock_agent
            return mock_val
            
        db.execute.side_effect = mock_execute
        
        intent = ExecutionIntent(
            agent_id="agent_1",
            pgl_id="pgl_sig",
            target_protocol="mcp",
            action="filesystem.read",
            payload={"random": str(__import__('uuid').uuid4())}
        )
        
        is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(
            intent, db, "workspace_test"
        )
        
        assert not is_approved
        assert reason == "EMERGENCY_KILL_SWITCH_ENGAGED"
        assert failure_phase == 4
        assert phase_results["4"] == "FAILED: Emergency Kill Switch engaged"
