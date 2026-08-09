import asyncio

from backend.apps.api.routers import security_posture


def test_static_posture_components_do_not_claim_verification():
    proxy = security_posture.get_proxy_status()
    supply_chain = security_posture.get_supply_chain_status()
    ollama = security_posture.get_ollama_sanitization_status()

    assert proxy["status"] == security_posture.NOT_VERIFIED
    assert proxy["traefik_routing_verified"] is False
    assert supply_chain["status"] == security_posture.NOT_VERIFIED
    assert supply_chain["codeql_verified"] is False
    assert ollama["status"] == security_posture.NOT_VERIFIED
    assert ollama["keep_alive_zero_verified"] is False


def test_lockerphycer_without_config_is_unconfigured(monkeypatch):
    monkeypatch.delenv("LOCKERPHYCER_URL", raising=False)

    result = asyncio.run(security_posture.check_lockerphycer_health())

    assert result["status"] == security_posture.UNCONFIGURED
    assert result["reachable"] is False
    assert result["protocol_identity_verified"] is False
    assert result["ids_active"] == security_posture.NOT_VERIFIED


def test_posture_endpoint_never_promotes_runtime_state_without_evidence(monkeypatch):
    monkeypatch.delenv("LOCKERPHYCER_URL", raising=False)

    result = asyncio.run(security_posture.get_security_posture())

    assert result["overall_status"] == security_posture.NOT_VERIFIED
    assert result["verified_runtime_state"] == {}
    assert "Traefik routing" in result["unverified_claims"]
    assert result["observations"]["proxy_security"]["status"] == security_posture.NOT_VERIFIED
    assert result["observations"]["lockerphycer"]["status"] == security_posture.UNCONFIGURED
