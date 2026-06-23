import pytest
from backend.core.ml.tiering import classify_event, EventForTiering, TieringDecision
from backend.db.models.ai import DataTier

def test_low_confidence_valid_event():
    """Low confidence but otherwise valid event -> Bronze."""
    event = EventForTiering(
        confidence_score=0.75,
        policy_passed=True,
        evidence_complete=True,
        schema_passed=True,
        quality_passed=True,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=False
    )
    decision = classify_event(event)
    assert decision.data_tier == DataTier.bronze
    assert not decision.eligible_for_training
    assert "bronze_low_confidence" in decision.reason_codes

def test_high_confidence_schema_failure():
    """High confidence with schema failure -> Bronze."""
    event = EventForTiering(
        confidence_score=0.98,
        policy_passed=True,
        evidence_complete=True,
        schema_passed=False,
        quality_passed=True,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=False
    )
    decision = classify_event(event)
    assert decision.data_tier == DataTier.bronze
    assert not decision.eligible_for_training
    assert "bronze_schema_failed" in decision.reason_codes

def test_mid_confidence_clean_execution():
    """Mid confidence with clean execution -> Silver."""
    event = EventForTiering(
        confidence_score=0.90,
        policy_passed=True,
        evidence_complete=True,
        schema_passed=True,
        quality_passed=True,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=False
    )
    decision = classify_event(event)
    assert decision.data_tier == DataTier.silver
    assert not decision.eligible_for_training
    assert "silver_mid_confidence" in decision.reason_codes

def test_high_confidence_full_evidence():
    """High confidence with full evidence and quality pass -> Gold."""
    event = EventForTiering(
        confidence_score=0.98,
        policy_passed=True,
        evidence_complete=True,
        schema_passed=True,
        quality_passed=True,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=False
    )
    decision = classify_event(event)
    assert decision.data_tier == DataTier.gold
    assert decision.eligible_for_training
    assert "gold_high_confidence_and_quality" in decision.reason_codes
    assert "runtime_clean" in decision.reason_codes

def test_high_confidence_budget_exceeded():
    """High confidence with budget exceeded -> Bronze."""
    event = EventForTiering(
        confidence_score=0.99,
        policy_passed=True,
        evidence_complete=True,
        schema_passed=True,
        quality_passed=True,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=True
    )
    decision = classify_event(event)
    assert decision.data_tier == DataTier.bronze
    assert not decision.eligible_for_training
    assert "bronze_budget_exceeded" in decision.reason_codes

def test_gold_demotion_quality_fail():
    """High confidence but quality failure -> Silver."""
    event = EventForTiering(
        confidence_score=0.99,
        policy_passed=True,
        evidence_complete=True,
        schema_passed=True,
        quality_passed=False,
        runtime_error=False,
        security_anomaly=False,
        budget_exceeded=False
    )
    decision = classify_event(event)
    assert decision.data_tier == DataTier.silver
    assert not decision.eligible_for_training
    assert "silver_quality_failed" in decision.reason_codes
