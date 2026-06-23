from backend.core.governance.checker_types import CheckResult

REQUIRED_PROTECTED_ROUTES = [
    "/api/v1/forensics/replay",
    "/api/v1/governance/simulate-policy",
    "/api/v1/pgl/quarantine",
    "/api/v1/x402/yield/predict",
    "/api/v1/pgl/identity-rag/resolve",
    "/api/v1/governed/capi/compile",
]


def run(ctx) -> CheckResult:
    try:
        response = ctx.http.get("/api/v1/x402/config")
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return CheckResult("x402", False, "critical", "Unable to query x402 config", {"error": str(exc)})

    protected = set(payload.get("protected_routes", []))
    missing = [route for route in REQUIRED_PROTECTED_ROUTES if route not in protected]

    return CheckResult(
        name="x402",
        passed=len(missing) == 0,
        severity="critical",
        summary="Protected route mapping verified" if not missing else "Missing protected routes in x402 config",
        details={"missing_routes": missing, "protected_route_count": len(protected)},
    )
