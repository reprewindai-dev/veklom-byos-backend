import uuid

import pytest

from backend.core.ml.tiering import EventForTiering, classify_event
from backend.security.mcp_gateway import EnhancedMCPAPIRuntime


@pytest.mark.asyncio
async def test_ambient_to_gold_loop():
    """
    E2E Test simulating the Grand Unified Loop:
    Bronze Failure -> Edge Intervention (VNP Inject) -> Execution Resumes -> Gold Event Stamped.
    """
    from unittest.mock import MagicMock

    # 1. Setup the Mesh Gateway
    gateway = EnhancedMCPAPIRuntime()
    gateway.redis_client = None
    gateway.permissions_calculator = MagicMock()
    gateway.permissions_calculator.calculate_effective_permissions.return_value = {
        "can_execute": True
    }

    gateway.anomaly_detection = MagicMock()
    gateway.anomaly_detection.detect_anomalies.return_value = []

    agent_id = "agent-alpha-001"
    capability_id = "cap_db_write"
    connection_id = str(uuid.uuid4())

    # 2. The Trap (Phase 4): Attempt to run with 0 VNP
    gateway.cost_attribution.vnp_ledger[agent_id] = 0.0

    request_payload = {
        "connection_id": connection_id,
        "nonce": f"nonce-{uuid.uuid4()}",
        "agent_id": agent_id,
        "capability_id": capability_id,
        "payload": {"data": "test_data"},
        "vnp_signature": "valid-sig-123",
        "upstream_evidence_hash": "mock-upstream-hash-abc",
    }

    # Execute the request
    bronze_response = await gateway.process_request(request_payload)

    # Assert Phase 4 blocked it
    assert bronze_response["status"] == "error"
    assert bronze_response["error"]["code"] == "402"
    assert "Payment Required" in bronze_response["error"]["message"]

    # 3. Classify the Failure Event
    bronze_event = EventForTiering(
        confidence_score=0.96,
        policy_passed=True,
        evidence_complete=False,
        schema_passed=True,
        quality_passed=False,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=True,
    )

    bronze_decision = classify_event(bronze_event)
    assert bronze_decision.data_tier.value == "bronze"
    assert bronze_decision.eligible_for_training is False
    assert "bronze_budget_exceeded" in bronze_decision.reason_codes

    # 4. The Ambient Save: Edge UI Intervenes and Injects VNP
    # (Simulating the user authorizing a micro-stake via AmbientIntervention.tsx)
    gateway.cost_attribution.vnp_ledger[agent_id] += 15.0

    # 5. The Transformation: Re-run the request
    gold_response = await gateway.process_request(request_payload)

    # Assert Phase 7 and 9 completed successfully
    assert gold_response["status"] == "authorized"
    assert "evidence_hash" in gold_response  # Cryptographic proof generated
    assert (
        gold_response["result"]["output"]["data"] == "Capability executed successfully"
    )
    assert gold_response["metadata"]["cost_attributed"] > 0

    # 6. Classify the Successful Event
    gold_event = EventForTiering(
        confidence_score=0.96,
        policy_passed=True,
        evidence_complete=True,
        schema_passed=True,
        quality_passed=True,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=False,
    )

    gold_decision = classify_event(gold_event)
    assert gold_decision.data_tier.value == "gold"
    assert gold_decision.eligible_for_training is True
    assert "quality_passed" in gold_decision.reason_codes
    assert "evidence_complete" in gold_decision.reason_codes
