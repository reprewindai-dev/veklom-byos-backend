import os
from typing import Dict, Any, List
from dataclasses import dataclass
from backend.db.models.ai import DataTier

@dataclass(frozen=True)
class TieringDecision:
    data_tier: DataTier
    confidence_score: float
    tier_score: float
    eligible_for_training: bool
    reason_codes: List[str]

@dataclass
class EventForTiering:
    confidence_score: float
    policy_passed: bool
    evidence_complete: bool
    schema_passed: bool
    quality_passed: bool
    runtime_error: bool
    security_anomaly: bool
    budget_exceeded: bool

def classify_event(event: EventForTiering) -> TieringDecision:
    """
    Evaluates an execution event using multi-factor hard gates and weighted scoring.
    """
    reason_codes = []
    
    # 1. HARD GATES (Immediate Bronze)
    is_bronze = False
    if event.runtime_error:
        reason_codes.append("bronze_runtime_error")
        is_bronze = True
    if event.security_anomaly:
        reason_codes.append("bronze_security_anomaly")
        is_bronze = True
    if event.budget_exceeded:
        reason_codes.append("bronze_budget_exceeded")
        is_bronze = True
    if not event.policy_passed:
        reason_codes.append("bronze_policy_failed")
        is_bronze = True
    if not event.evidence_complete:
        reason_codes.append("bronze_evidence_incomplete")
        is_bronze = True
    if not event.schema_passed:
        reason_codes.append("bronze_schema_failed")
        is_bronze = True

    # 2. CALCULATE TIER SCORE
    # TierScore = 0.40*Confidence + 0.20*Policy + 0.15*Evidence + 0.10*Schema + 0.10*Quality + 0.05*RuntimeHealth
    conf_val = max(0.0, min(1.0, event.confidence_score))
    pol_val = 1.0 if event.policy_passed else 0.0
    ev_val = 1.0 if event.evidence_complete else 0.0
    sch_val = 1.0 if event.schema_passed else 0.0
    qual_val = 1.0 if event.quality_passed else 0.0
    rt_health = 1.0 if (not event.runtime_error and not event.budget_exceeded) else 0.0
    
    tier_score = (0.40 * conf_val) + (0.20 * pol_val) + (0.15 * ev_val) + (0.10 * sch_val) + (0.10 * qual_val) + (0.05 * rt_health)
    
    # 3. TIER RESOLUTION
    if is_bronze:
        data_tier = DataTier.bronze
        eligible = False
    elif conf_val < 0.80:
        reason_codes.append("bronze_low_confidence")
        data_tier = DataTier.bronze
        eligible = False
    elif conf_val <= 0.95:
        reason_codes.append("silver_mid_confidence")
        data_tier = DataTier.silver
        eligible = False
    else:
        # Confidence > 0.95
        if event.quality_passed:
            reason_codes.append("gold_high_confidence_and_quality")
            data_tier = DataTier.gold
            eligible = True
        else:
            reason_codes.append("silver_quality_failed")
            data_tier = DataTier.silver
            eligible = False
            
    # Add positive reason codes for completeness
    if event.policy_passed: reason_codes.append("policy_passed")
    if event.evidence_complete: reason_codes.append("evidence_complete")
    if event.schema_passed: reason_codes.append("schema_passed")
    if event.quality_passed: reason_codes.append("quality_passed")
    if rt_health == 1.0: reason_codes.append("runtime_clean")

    return TieringDecision(
        data_tier=data_tier,
        confidence_score=conf_val,
        tier_score=tier_score,
        eligible_for_training=eligible,
        reason_codes=list(set(reason_codes))
    )
