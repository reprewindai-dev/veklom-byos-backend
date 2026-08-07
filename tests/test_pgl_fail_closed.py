"""Regression tests for issue #170's fail-closed PGL correction."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.apps.api.routers import pgl
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_admin


class NoSideEffectSession:
    """DB double that records any attempted mutation or settlement-adjacent work."""

    def __init__(self):
        self.execute = AsyncMock()
        self.add = MagicMock()
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.rollback = AsyncMock()


def _test_app(session: NoSideEffectSession) -> FastAPI:
    app = FastAPI()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.include_router(pgl.router, prefix="/api/v1")
    return app


def test_unauthenticated_quarantine_is_denied_without_side_effects():
    session = NoSideEffectSession()
    client = TestClient(_test_app(session))

    response = client.post("/api/v1/pgl/agent-1/quarantine")

    assert response.status_code in {401, 403}
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()


def test_authorized_quarantine_fails_closed_without_side_effects():
    session = NoSideEffectSession()
    app = _test_app(session)
    operator = type(
        "Operator",
        (),
        {"role": "admin", "workspace_id": "workspace-1"},
    )()
    app.dependency_overrides[get_current_admin] = lambda: operator
    client = TestClient(app)

    response = client.post(
        "/api/v1/pgl/agent-1/quarantine",
        params={"reason": "regression test"},
    )

    assert response.status_code == 501
    detail = response.json()["detail"]
    assert detail["status"] == "NOT_IMPLEMENTED"
    assert detail["verification_status"] == "NOT_VERIFIED"
    assert detail["containment_performed"] is False
    assert detail["settlement_created"] is False
    session.execute.assert_not_awaited()
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()


def test_pgl_router_contains_no_synthetic_proof_or_settlement_claims():
    source = Path(pgl.__file__).read_text(encoding="utf-8")

    forbidden = (
        "2000000",
        "SettlementLedgerRepository",
        "create_fee_entry",
        "quarantine_" + agent_id",
        '"verified": True',
        '"mode": "live"',
        '"status": "success"',
        '"decoy_buffer": "ACTIVE"',
        '"database_mode": "READ_ONLY_EPHEMERAL"',
        "api.veklom.com",
        "control.veklom.com",
        "llama3-70b-instruct-v2",
        "VNP_TIER_1_CLEAN_ROOM",
    )
    for claim in forbidden:
        assert claim not in source


def test_missing_registry_status_defaults_to_not_verified():
    source = Path(pgl.__file__).read_text(encoding="utf-8")

    assert 'metadata.get("status", NOT_VERIFIED)' in source
    assert 'metadata.get("status", "ACTIVE")' not in source
