import asyncio

from backend.apps.api.routers.health import health_check


def test_shallow_health_is_process_only_not_dependency_verification():
    payload = asyncio.run(health_check())

    assert payload["status"] == "alive"
    assert payload["verification_scope"] == "PROCESS_ONLY"
    assert payload["dependencies"] == "NOT_VERIFIED"
    assert payload["status"] != "healthy"
