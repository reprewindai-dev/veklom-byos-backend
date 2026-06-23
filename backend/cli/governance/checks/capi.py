from backend.core.governance.checker_types import CheckResult


def run(ctx) -> CheckResult:
    # Control path validation only. Full compile tests can use a dedicated fixture.
    try:
        r = ctx.http.get("/api/v1/x402/config")
        r.raise_for_status()
        protected = set(r.json().get("protected_routes", []))
    except Exception as exc:
        return CheckResult("capi", False, "critical", "Unable to validate cAPI protection mapping", {"error": str(exc)})

    route = "/api/v1/governed/capi/compile"
    return CheckResult(
        name="capi",
        passed=route in protected,
        severity="critical",
        summary="cAPI compile route is payment-protected" if route in protected else "cAPI compile route missing from x402 protection map",
        details={"route": route},
    )
