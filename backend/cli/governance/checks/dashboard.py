from backend.core.governance.checker_types import CheckResult


def run(ctx) -> CheckResult:
    # Lightweight availability + contract check. Deep browser tests belong elsewhere.
    try:
        r = ctx.http.get("/api/v1/autonomous/training/readiness", params={"tenant_id": ctx.config.tenant_id, "model_family": ctx.config.model_family})
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:
        return CheckResult("dashboard", False, "medium", "Dashboard backing contracts unavailable", {"error": str(exc)})

    required_keys = {"eligible_gold_count", "route_diversity", "threshold_met", "cooldown_active", "training_job_running"}
    missing = sorted(required_keys - set(payload.keys()))
    return CheckResult(
        name="dashboard",
        passed=not missing,
        severity="medium",
        summary="Dashboard governance contract available" if not missing else "Dashboard contract incomplete",
        details={"missing_keys": missing},
    )
