from backend.services.uacp.core import UACPDecisionKernel


def test_budget_limit_accepts_measured_budget_with_headroom():
    kernel = UACPDecisionKernel()

    passed, details = kernel._check_budget_limit(
        {"estimated_cost": 50},
        {"budget_remaining": 100},
        "test-workspace",
    )

    assert passed is True
    assert details == {"cost": 50, "budget": 100}


def test_budget_limit_denies_when_budget_is_missing():
    kernel = UACPDecisionKernel()

    passed, details = kernel._check_budget_limit(
        {"estimated_cost": 50},
        {},
        "test-workspace",
    )

    assert passed is False
    assert details["reason"] == "budget_remaining_missing"


def test_budget_limit_denies_when_estimated_cost_is_missing():
    kernel = UACPDecisionKernel()

    passed, details = kernel._check_budget_limit(
        {},
        {"budget_remaining": 100},
        "test-workspace",
    )

    assert passed is False
    assert details["reason"] == "estimated_cost_missing"


def test_budget_limit_denies_invalid_negative_or_non_numeric_values():
    kernel = UACPDecisionKernel()

    for policy_frame, context, expected_reason in (
        ({"estimated_cost": -1}, {"budget_remaining": 100}, "estimated_cost_invalid"),
        ({"estimated_cost": "50"}, {"budget_remaining": 100}, "estimated_cost_invalid"),
        ({"estimated_cost": True}, {"budget_remaining": 100}, "estimated_cost_invalid"),
        ({"estimated_cost": False}, {"budget_remaining": 100}, "estimated_cost_invalid"),
        ({"estimated_cost": float("inf")}, {"budget_remaining": 100}, "estimated_cost_invalid"),
        ({"estimated_cost": float("-inf")}, {"budget_remaining": 100}, "estimated_cost_invalid"),
        ({"estimated_cost": float("nan")}, {"budget_remaining": 100}, "estimated_cost_invalid"),
        ({"estimated_cost": 50}, {"budget_remaining": -1}, "budget_remaining_invalid"),
        ({"estimated_cost": 50}, {"budget_remaining": "100"}, "budget_remaining_invalid"),
        ({"estimated_cost": 50}, {"budget_remaining": True}, "budget_remaining_invalid"),
        ({"estimated_cost": 50}, {"budget_remaining": False}, "budget_remaining_invalid"),
        ({"estimated_cost": 50}, {"budget_remaining": float("inf")}, "budget_remaining_invalid"),
        ({"estimated_cost": 50}, {"budget_remaining": float("-inf")}, "budget_remaining_invalid"),
        ({"estimated_cost": 50}, {"budget_remaining": float("nan")}, "budget_remaining_invalid"),
    ):
        passed, details = kernel._check_budget_limit(policy_frame, context, "test-workspace")
        assert passed is False
        assert details["reason"] == expected_reason


def test_full_kernel_denies_when_budget_evidence_is_missing():
    kernel = UACPDecisionKernel()

    result = kernel.evaluate(
        intent={"action": "test"},
        v2_plan={
            "policy_checkable_frame": {
                "estimated_cost": 10,
                "risk_tier": "low",
                "tools": [],
                "constitutional_violations": [],
            }
        },
        v3_context={"tool_allowlist": [], "max_risk_tier": "high"},
        workspace_id="test-workspace",
    )

    assert result.decision == "DENIED"
    budget_evaluation = next(
        item for item in result.policy_evaluations if item["policy"] == "budget_limit"
    )
    assert budget_evaluation["passed"] is False
    assert budget_evaluation["details"]["reason"] == "budget_remaining_missing"
