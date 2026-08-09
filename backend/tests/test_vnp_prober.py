from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.core.workers.vnp_prober import REGION, WORKER_ID, _content_hash, ping_api


class _Response:
    status = 204

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def read(self):
        return b""


class _Session:
    def __init__(self):
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        return _Response()


@pytest.mark.asyncio
async def test_missing_base_url_is_recorded_without_http_call():
    api = SimpleNamespace(id=uuid4(), base_url=None)
    session = _Session()

    event = await ping_api(session, api)

    assert session.calls == []
    assert event.status_code is None
    assert event.latency_ms is None
    assert event.error_reason == "INVALID_CONFIGURATION: missing base_url"
    assert event.worker_signature == "UNSIGNED"


@pytest.mark.asyncio
async def test_probe_event_uses_deterministic_content_hash_and_unsigned_worker():
    api = SimpleNamespace(id=uuid4(), base_url="https://example.com/health")
    session = _Session()

    event = await ping_api(session, api)

    expected_hash = _content_hash(
        api_id=event.api_id,
        region=REGION,
        worker_id=WORKER_ID,
        url=api.base_url,
        status_code=event.status_code,
        latency_ms=event.latency_ms,
        error_reason=event.error_reason,
        measured_at=event.measured_at,
    )
    assert session.calls
    assert event.worker_signature == "UNSIGNED"
    assert event.worker_signature != "sig_dummy_worker_auth"
    assert event.evidence_hash == expected_hash
    assert event.provenance_hash == expected_hash
    assert event.cryptography_anchor is None
