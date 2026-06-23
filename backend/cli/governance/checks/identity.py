from sqlalchemy import text
from backend.core.governance.checker_types import CheckResult


def run(ctx) -> CheckResult:
    if ctx.db_engine is None:
        return CheckResult("identity", False, "high", "DB connection not configured")

    with ctx.db_engine.connect() as conn:
        pgl_count = conn.execute(text("SELECT COUNT(*) FROM pgl_identity")).scalar()
        orphan_count = conn.execute(text("""
            SELECT COUNT(*)
            FROM exec_log e
            LEFT JOIN pgl_identity p ON p.id = e.agent_id
            WHERE p.id IS NULL
        """)).scalar()

    passed = pgl_count > 0 and orphan_count == 0
    return CheckResult(
        name="identity",
        passed=passed,
        severity="critical",
        summary="Canonical PGL identity wiring validated" if passed else "Orphaned governed records detected",
        details={"pgl_identity_count": pgl_count, "orphan_exec_log_rows": orphan_count},
    )
