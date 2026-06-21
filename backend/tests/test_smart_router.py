import pytest
from backend.services.smart_router import _hard_gates, ModelCandidate, RoutingRequirement

def create_base_candidate(node_id="test_node"):
    return ModelCandidate(
        node_id=node_id,
        provider="test_provider",
        model="test_model",
        cost_per_1k=0.01,
        quality_prior=0.9,
        latency_ms_prior=1000,
        security_level=2,
        max_context=8192,
        max_complexity=8,
        is_online=True
    )

def test_hard_gates_all_viable():
    candidate1 = create_base_candidate("node1")
    candidate2 = create_base_candidate("node2")
    candidate2.security_level = 3

    fleet = [candidate1, candidate2]
    req = RoutingRequirement(
        security_clearance=1,
        estimated_tokens=4000,
        max_latency_ms=2000,
        task_complexity=5
    )

    viable, rejected = _hard_gates(fleet, req)
    assert len(viable) == 2
    assert len(rejected) == 0

def test_hard_gates_offline():
    candidate = create_base_candidate()
    candidate.is_online = False

    req = RoutingRequirement()
    viable, rejected = _hard_gates([candidate], req)

    assert len(viable) == 0
    assert len(rejected) == 1
    assert rejected[0] == {"node_id": candidate.node_id, "reason": "offline"}

def test_hard_gates_clearance_too_low():
    candidate = create_base_candidate()
    candidate.security_level = 1

    req = RoutingRequirement(security_clearance=2)
    viable, rejected = _hard_gates([candidate], req)

    assert len(viable) == 0
    assert len(rejected) == 1
    assert rejected[0] == {"node_id": candidate.node_id, "reason": "clearance_too_low"}

def test_hard_gates_context_overflow():
    candidate = create_base_candidate()
    candidate.max_context = 4096

    req = RoutingRequirement(estimated_tokens=5000)
    viable, rejected = _hard_gates([candidate], req)

    assert len(viable) == 0
    assert len(rejected) == 1
    assert rejected[0] == {"node_id": candidate.node_id, "reason": "context_overflow"}

def test_hard_gates_latency_sla():
    candidate = create_base_candidate()
    candidate.latency_ms_prior = 5000
    # Also test with observed latency
    candidate2 = create_base_candidate("node2")
    candidate2.latency_ms_prior = 1000
    candidate2.observed_latency_ms = 6000

    req = RoutingRequirement(max_latency_ms=4000)
    viable, rejected = _hard_gates([candidate, candidate2], req)

    assert len(viable) == 0
    assert len(rejected) == 2
    assert rejected[0] == {"node_id": candidate.node_id, "reason": "latency_sla"}
    assert rejected[1] == {"node_id": candidate2.node_id, "reason": "latency_sla"}

def test_hard_gates_complexity_too_low():
    candidate = create_base_candidate()
    candidate.max_complexity = 4

    req = RoutingRequirement(task_complexity=5)
    viable, rejected = _hard_gates([candidate], req)

    assert len(viable) == 0
    assert len(rejected) == 1
    assert rejected[0] == {"node_id": candidate.node_id, "reason": "complexity_too_low"}

def test_hard_gates_mixed():
    c_viable = create_base_candidate("viable")

    c_offline = create_base_candidate("offline")
    c_offline.is_online = False

    c_security = create_base_candidate("security")
    c_security.security_level = 1

    fleet = [c_viable, c_offline, c_security]
    req = RoutingRequirement(security_clearance=2)

    viable, rejected = _hard_gates(fleet, req)

    assert len(viable) == 1
    assert viable[0].node_id == "viable"

    assert len(rejected) == 2
    assert rejected[0] == {"node_id": "offline", "reason": "offline"}
    assert rejected[1] == {"node_id": "security", "reason": "clearance_too_low"}
