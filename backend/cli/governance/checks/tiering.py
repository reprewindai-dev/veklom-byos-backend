from decimal import Decimal
from sqlalchemy import text
from backend.core.governance.checker_types import CheckResult
from backend.core.ml.tiering import classify_event, EventForTiering


def run(ctx) -> CheckResult:
    if ctx.db_engine is None or not ctx.config.tenant_id:
        return CheckResult("tiering", False, "high", "DB connection or tenant_id not configured")

    mismatches = 0
    sampled = 0
    with ctx.db_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, tenant_id, agent_id, route_family, confidence_score, policy_passed,
                   schema_passed, quality_passed, evidence_complete, runtime_error,
                   security_anomaly, budget_exceeded, dedupe_key, data_tier, eligible_for_training
            FROM exec_log
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC
            LIMIT 50
        """), {"tenant_id": ctx.config.tenant_id}).mappings().all()

    for row in rows:
        sampled += 1
        decision = classify_event(EventForTiering(
            confidence_score=float(row["confidence_score"]),
            policy_passed=row["policy_passed"],
            schema_passed=row["schema_passed"],
            quality_passed=row["quality_passed"],
            evidence_complete=row["evidence_complete"],
            runtime_error=row["runtime_error"],
            security_anomaly=row["security_anomaly"],
            budget_exceeded=row["budget_exceeded"],
        ))
        if decision.data_tier.value != row["data_tier"] or decision.eligible_for_training != row["eligible_for_training"]:
            mismatches += 1

    return CheckResult(
        name="tiering",
        passed=mismatches == 0,
        severity="critical",
        summary="Stored tier decisions match deterministic classifier" if mismatches == 0 else "Tiering drift detected",
        details={"sampled_rows": sampled, "mismatches": mismatches},
    )
