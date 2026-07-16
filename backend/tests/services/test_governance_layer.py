import pytest
from backend.services.governance_layer import PolicyCompositionEngine, PermissionsCalculator

def test_compose_policy():
    engine = PolicyCompositionEngine()

    system_policy = {"system_rule": "allow_all"}
    owner_policy = {"owner_rule": "restrict_sensitive"}
    runtime_policy = {"runtime_rule": "temporary_block"}
    temporal_policy = {"temporal_rule": "expire_soon"}

    result = engine.compose_policy(
        agent_id="agent_123",
        capability_id="cap_456",
        system_policy=system_policy,
        owner_policy=owner_policy,
        runtime_policy=runtime_policy,
        temporal_policy=temporal_policy
    )

    assert result["is_valid"] is True
    assert result["conflicts_detected"] == []
    assert result["system_policy"] == system_policy
    assert result["owner_policy"] == owner_policy
    assert result["runtime_policy"] == runtime_policy

def test_calculate_effective_permissions_high_trust():
    calculator = PermissionsCalculator()

    result = calculator.calculate_effective_permissions(
        agent_id="agent_123",
        capability_id="cap_456",
        effective_trust=75.0,
        system_policy={},
        owner_policy={},
        runtime_policy={}
    )

    assert result["can_execute"] is True
    assert result["requires_approval"] is False
    assert result["rate_limit"] == 100
    assert result["approval_path"] == ["admin-001", "security-lead"]

def test_calculate_effective_permissions_low_trust():
    calculator = PermissionsCalculator()

    result = calculator.calculate_effective_permissions(
        agent_id="agent_123",
        capability_id="cap_456",
        effective_trust=30.0,
        system_policy={},
        owner_policy={},
        runtime_policy={}
    )

    assert result["can_execute"] is True
    assert result["requires_approval"] is True
    assert result["rate_limit"] == 100
    assert result["approval_path"] == ["admin-001", "security-lead"]
