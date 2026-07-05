import sys
import os
import pytest
from importlib import util

# Define the local Node 4 tiering engine
from backend.core.ml.tiering import classify_event as node4_classify, EventForTiering

def load_node3_tiering():
    """Dynamically loads the cappo-backend (Node 3) tiering engine if available."""
    # Assuming cappo-backend is checked out as a sibling directory in CI
    node3_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../cappo-backend/cappo_backend/core/ml/tiering.py"))
    
    if not os.path.exists(node3_path):
        pytest.skip(f"cappo-backend not found at {node3_path}. Skipping parity test.")
        
    spec = util.spec_from_file_location("node3_tiering", node3_path)
    module = util.module_from_spec(spec)
    sys.modules["node3_tiering"] = module
    spec.loader.exec_module(module)
    return module.classify_event

def test_tiering_engine_parity():
    """
    Contract Test: Ensures that the exact same EventForTiering payload
    produces the exact same TieringDecision across both Node 3 and Node 4.
    """
    node3_classify = load_node3_tiering()
    
    scenarios = [
        # 1. Perfect Event -> Gold
        EventForTiering(
            confidence_score=0.99,
            policy_passed=True,
            evidence_complete=True,
            schema_passed=True,
            quality_passed=True,
            runtime_error=False,
            security_anomaly=False,
            budget_exceeded=False
        ),
        # 2. Perfect Event but Low Quality -> Silver
        EventForTiering(
            confidence_score=0.99,
            policy_passed=True,
            evidence_complete=True,
            schema_passed=True,
            quality_passed=False,
            runtime_error=False,
            security_anomaly=False,
            budget_exceeded=False
        ),
        # 3. Budget Exceeded -> Bronze
        EventForTiering(
            confidence_score=0.99,
            policy_passed=True,
            evidence_complete=True,
            schema_passed=True,
            quality_passed=True,
            runtime_error=False,
            security_anomaly=False,
            budget_exceeded=True
        ),
        # 4. Low Confidence -> Bronze
        EventForTiering(
            confidence_score=0.50,
            policy_passed=True,
            evidence_complete=True,
            schema_passed=True,
            quality_passed=True,
            runtime_error=False,
            security_anomaly=False,
            budget_exceeded=False
        )
    ]
    
    for i, event in enumerate(scenarios):
        node4_decision = node4_classify(event)
        
        # We must construct a Node3-specific event object to pass to the dynamically loaded module
        # since it uses its own EventForTiering dataclass
        import node3_tiering
        node3_event = node3_tiering.EventForTiering(
            confidence_score=event.confidence_score,
            policy_passed=event.policy_passed,
            evidence_complete=event.evidence_complete,
            schema_passed=event.schema_passed,
            quality_passed=event.quality_passed,
            runtime_error=event.runtime_error,
            security_anomaly=event.security_anomaly,
            budget_exceeded=event.budget_exceeded
        )
        
        node3_decision = node3_classify(node3_event)
        
        assert node4_decision.data_tier.value == node3_decision.data_tier.value, f"Scenario {i} Failed: Tier mismatch"
        assert node4_decision.eligible_for_training == node3_decision.eligible_for_training, f"Scenario {i} Failed: Eligibility mismatch"
        assert set(node4_decision.reason_codes) == set(node3_decision.reason_codes), f"Scenario {i} Failed: Reason code mismatch"
