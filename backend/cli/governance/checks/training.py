from sqlalchemy import text
from backend.core.governance.checker_types import CheckResult


def run(ctx) -> CheckResult:
    if ctx.db_engine is None or not ctx.config.tenant_id:
        return CheckResult("training", False, "high", "DB connection or tenant_id not configured")

    with ctx.db_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, data_tier, eligible_for_training
            FROM exec_log
            WHERE tenant_id = :tenant_id
              AND data_tier = 'gold'
              AND eligible_for_training = TRUE
              AND training_locked_at IS NULL
            ORDER BY created_at ASC
            LIMIT 25
        """), {"tenant_id": ctx.config.tenant_id}).mappings().all()

        violations = conn.execute(text("""
            SELECT COUNT(*)
            FROM exec_log
            WHERE tenant_id = :tenant_id
              AND eligible_for_training = TRUE
              AND data_tier <> 'gold'
        """), {"tenant_id": ctx.config.tenant_id}).scalar()

    return CheckResult(
        name="training",
        passed=violations == 0,
        severity="critical",
        summary="Gold-only training invariant holds" if violations == 0 else "Non-Gold rows marked training-eligible",
        details={"candidate_rows": len(rows), "training_eligibility_violations": violations},
    )
