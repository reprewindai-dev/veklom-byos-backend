from backend.apps.api.routers.vnp import build_vnp_verification_stack


def _status(stack, section):
    return next(item["status"] for item in stack if item["section"] == section)


def test_vnp_verification_stack_does_not_claim_signed_telemetry_without_signed_rows():
    stack = build_vnp_verification_stack(
        {
            "total_physical_measurements": 10,
            "total_signed_telemetry": 0,
            "active_api_routes": 1,
        }
    )

    assert _status(stack, "Physical measurements") == "Live"
    assert _status(stack, "Signed telemetry") == "Disconnected"
    assert _status(stack, "Route beacons") == "Connected"


def test_vnp_verification_stack_marks_signed_telemetry_live_from_signed_evidence():
    stack = build_vnp_verification_stack(
        {
            "total_physical_measurements": 10,
            "total_signed_telemetry": 4,
            "active_api_routes": 1,
        }
    )

    assert _status(stack, "Signed telemetry") == "Live"


def test_vnp_verification_stack_does_not_claim_live_x402_without_settlement_evidence():
    stack = build_vnp_verification_stack(
        {
            "total_physical_measurements": 10,
            "total_signed_telemetry": 4,
            "active_api_routes": 1,
            "x402_settlement_evidence": 0,
        }
    )

    assert _status(stack, "x402 settlement evidence") == "Connected"


def test_vnp_verification_stack_marks_x402_live_from_settlement_evidence():
    stack = build_vnp_verification_stack(
        {
            "total_physical_measurements": 10,
            "total_signed_telemetry": 4,
            "active_api_routes": 1,
            "x402_settlement_evidence": 2,
        }
    )

    assert _status(stack, "x402 settlement evidence") == "Live"
