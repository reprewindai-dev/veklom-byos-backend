import pytest
from backend.services.uacp.core import UACPDecisionKernel

def test_check_budget_limit_within_budget():
    kernel = UACPDecisionKernel()
    policy_frame = {"estimated_cost": 50}
    context = {"budget_remaining": 100}
    workspace_id = "test_workspace"

    passed, details = kernel._check_budget_limit(policy_frame, context, workspace_id)

    assert passed is True
    assert details == {"cost": 50, "budget": 100}

def test_check_budget_limit_exceeds_budget():
    kernel = UACPDecisionKernel()
    policy_frame = {"estimated_cost": 150}
    context = {"budget_remaining": 100}
    workspace_id = "test_workspace"

    passed, details = kernel._check_budget_limit(policy_frame, context, workspace_id)

    assert passed is False
    assert details == {"cost": 150, "budget": 100}

def test_check_budget_limit_equal_budget():
    kernel = UACPDecisionKernel()
    policy_frame = {"estimated_cost": 100}
    context = {"budget_remaining": 100}
    workspace_id = "test_workspace"

    passed, details = kernel._check_budget_limit(policy_frame, context, workspace_id)

    assert passed is True
    assert details == {"cost": 100, "budget": 100}

def test_check_budget_limit_no_estimated_cost():
    kernel = UACPDecisionKernel()
    policy_frame = {}
    context = {"budget_remaining": 100}
    workspace_id = "test_workspace"

    passed, details = kernel._check_budget_limit(policy_frame, context, workspace_id)

    assert passed is True
    assert details == {"cost": 0, "budget": 100}

def test_check_budget_limit_no_budget_remaining():
    kernel = UACPDecisionKernel()
    policy_frame = {"estimated_cost": 50}
    context = {}
    workspace_id = "test_workspace"

    passed, details = kernel._check_budget_limit(policy_frame, context, workspace_id)

    assert passed is True
    assert details == {"cost": 50, "budget": float('inf')}
