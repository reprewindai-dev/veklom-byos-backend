from sqlalchemy import text
from backend.core.governance.checker_types import CheckResult

REQUIRED_TABLES = ["exec_log", "settlement_ledger", "evidence_pack"]


def run(ctx) -> CheckResult:
    if ctx.db_engine is None:
        return CheckResult("rls", False, "high", "DB connection not configured")

    rows = []
    with ctx.db_engine.connect() as conn:
        for table in REQUIRED_TABLES:
            row = conn.execute(text("""
                SELECT c.relrowsecurity AS rls_enabled
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = :table
            """), {"table": table}).mappings().first()
            rows.append((table, bool(row and row["rls_enabled"])))

    missing = [table for table, enabled in rows if not enabled]
    return CheckResult(
        name="rls",
        passed=len(missing) == 0,
        severity="critical",
        summary="RLS enabled on required tenant tables" if not missing else f"RLS missing on: {', '.join(missing)}",
        details={table: enabled for table, enabled in rows},
    )
