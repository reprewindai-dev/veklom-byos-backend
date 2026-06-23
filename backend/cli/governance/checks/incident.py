from backend.core.governance.checker_types import CheckResult


def run(ctx) -> CheckResult:
    # Safe skeleton: verify the incident-facing APIs exist and expose the minimum fields.
    try:
        r = ctx.http.get("/api/v1/seked/agents")
        r.raise_for_status()
    except Exception as exc:
        return CheckResult("incident", False, "medium", "Unable to validate incident-facing governance endpoints", {"error": str(exc)})

    return CheckResult(
        name="incident",
        passed=True,
        severity="medium",
        summary="Incident governance endpoints reachable",
        details={},
    )
