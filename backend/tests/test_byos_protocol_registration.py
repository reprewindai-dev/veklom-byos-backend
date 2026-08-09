import pytest

from backend.apps.api.routers.protocol import (
    MANIFEST,
    IntrospectQuery,
    get_protocol_manifest,
    introspect_capabilities,
)
from backend.core.services.capi_registration import build_registration_payload


@pytest.mark.anyio
async def test_protocol_manifest_is_canonical_and_endpoint_backed():
    manifest = await get_protocol_manifest()

    assert manifest["base_url"] == "https://api.veklom.com"
    assert manifest["role"] == "sovereign backend / control-plane core"
    assert manifest["links"] == {
        "byos": "https://api.veklom.com/protocol.json",
        "capi": "https://capi.veklom.com/protocol.json",
        "cappo": "https://cappo.veklom.com/protocol.json",
        "pgl": "https://pgl.veklom.com/protocol.json",
    }
    assert set(manifest["capabilities"]) == set(manifest["capability_endpoints"])


@pytest.mark.anyio
async def test_protocol_introspection_filters_declared_capabilities():
    response = await introspect_capabilities(IntrospectQuery(query="evidence"))

    assert response["matches"] == ["build_evidence_packs"]
    assert response["total"] == 1
    assert response["links"] == MANIFEST["links"]


def test_registration_payload_contains_executable_capability_objects():
    payload = build_registration_payload()

    assert payload["base_url"] == "https://api.veklom.com"
    assert payload["capabilities"]
    assert all(isinstance(capability, dict) for capability in payload["capabilities"])
    executable = [
        capability
        for capability in payload["capabilities"]
        if capability["endpoint"].startswith("https://api.veklom.com/")
    ]
    assert executable
    assert all(
        capability["input_schema"]
        and capability["risk_level"]
        and isinstance(capability["requires_approval"], bool)
        for capability in executable
    )
