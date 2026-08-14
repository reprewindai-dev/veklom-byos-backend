import asyncio
from types import SimpleNamespace

import httpx
import pytest

from backend.apps.api.routers.protocol import (
    MANIFEST,
    IntrospectQuery,
    get_protocol_manifest,
    introspect_capabilities,
)
from backend.core.services.capi_registration import build_registration_payload


class RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, statuses: list[int]) -> None:
        self._statuses = statuses
        self.paths: list[str] = []
        self._calls = asyncio.Event()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        self._calls.set()
        return httpx.Response(self._statuses.pop(0), request=request)

    async def wait_for_calls(self, count: int) -> None:
        while len(self.paths) < count:
            self._calls.clear()
            await asyncio.wait_for(self._calls.wait(), timeout=1)


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


def test_heartbeat_refreshes_an_existing_registration() -> None:
    from backend.core.services.capi_registration import maintain_capi_registration

    async def exercise() -> None:
        settings = SimpleNamespace(
            CAPI_BACKEND_URL="http://capi.test",
            CAPI_REGISTRY_TOKEN="registry-token",
            CAPI_REGISTRY_TTL_MS=1,
        )
        transport = RecordingTransport([201, 200])
        stop = asyncio.Event()
        task = asyncio.create_task(maintain_capi_registration(settings, stop, transport))
        await transport.wait_for_calls(2)
        stop.set()
        await task
        assert transport.paths == ["/api/v1/registry/register", "/api/v1/registry/heartbeat"]

    asyncio.run(exercise())
