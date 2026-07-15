from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.apps.api.routers import repogate_api
from backend.core.security import auth
from backend.core.security.middlewares import (
    ZeroTrustMiddleware,
    _accepts_internal_operator_credential,
)


class MockAsyncSession:
    def __init__(self):
        self.entries = []
        self.committed = False

    def add(self, entry):
        self.entries.append(entry)

    async def commit(self):
        self.committed = True


def mock_session_factory(session):
    @asynccontextmanager
    async def _session():
        yield session

    return _session


def seal_payload():
    return {
        "run_id": "run_123",
        "agent_id": "agent_456",
        "repo_url": "https://github.com/example/protected-repo",
        "risk_level": "HIGH",
        "decision": "human_approval_required",
        "decision_note": "Deployment files changed.",
        "ledger_hash": "a" * 64,
        "timestamp": "2026-07-15T00:00:00Z",
    }


def test_seal_rejects_prefix_only_api_key(monkeypatch):
    app = FastAPI()
    app.add_middleware(ZeroTrustMiddleware)
    app.include_router(repogate_api.router, prefix="/api/v1")

    monkeypatch.setattr(auth, "_UACP_INTERNAL_KEY", "expected-internal-key")

    response = TestClient(app).post(
        "/api/v1/repogate/seal",
        headers={"X-API-Key": "byos_not_an_authenticated_key"},
        json=seal_payload(),
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required for UACP internal routes"


def test_seal_requires_verified_internal_operator_and_records_server_provenance(monkeypatch):
    app = FastAPI()
    app.add_middleware(ZeroTrustMiddleware)
    app.include_router(repogate_api.router, prefix="/api/v1")

    session = MockAsyncSession()
    monkeypatch.setattr(auth, "_UACP_INTERNAL_KEY", "expected-internal-key")
    monkeypatch.setattr(repogate_api, "async_session", mock_session_factory(session))

    client = TestClient(app)

    rejected = client.post(
        "/api/v1/repogate/seal",
        headers={"x-uacp-internal-key": "wrong-key"},
        json=seal_payload(),
    )
    assert rejected.status_code == 401
    assert session.entries == []

    accepted = client.post(
        "/api/v1/repogate/seal",
        headers={"x-uacp-internal-key": "expected-internal-key"},
        json=seal_payload(),
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["status"] == "sealed"
    assert body["ledger_hash"] == "a" * 64
    assert body["receipt_id"].startswith("repogate_")
    assert body["sealed_at"] != seal_payload()["timestamp"]

    assert session.committed is True
    assert len(session.entries) == 1
    metadata = session.entries[0].log_metadata
    assert metadata["reported_at"] == seal_payload()["timestamp"]
    assert metadata["sealed_at"] == body["sealed_at"]
    assert metadata["sealed_by"] == "uacp-internal"
    assert metadata["receipt_id"] == body["receipt_id"]


def test_internal_operator_header_cannot_bypass_unrelated_routes():
    app = FastAPI()
    app.add_middleware(ZeroTrustMiddleware)

    @app.get("/api/v1/unrelated")
    async def unrelated_route():
        return {"status": "ok"}

    response = TestClient(app).get(
        "/api/v1/unrelated",
        headers={"x-uacp-internal-key": "arbitrary-value"},
    )

    assert response.status_code == 401


def test_internal_uacp_path_accepts_the_documented_internal_credential():
    assert _accepts_internal_operator_credential("/api/v1/internal/uacp/summary")
