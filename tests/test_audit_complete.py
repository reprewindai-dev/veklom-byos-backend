"""Veklom Control Plane — Comprehensive Audit Validation Test Suite.

Tests ALL P0/P1 audit items in a single file for final readiness verification:
1. Subscription plans structure & normalization
2. x402 config fail-closed behavior
3. Fax webhook authentication matrix
4. Playground sovereign fallback
5. Control-plane-map identity surface
6. Onboarding vertical selection
"""

import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.apps.api.main import app
from backend.core.database.database import async_session, engine, Base
from backend.core.security.auth import get_current_user, create_access_token
from backend.db.models.security import AuditLog
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.billing import Subscription, BudgetRule, WalletTransaction
from backend.db.models.security import KillSwitchState
from backend.db.models.ai import ExecutionLog
from backend.db.models.provider import ProviderKey, ProviderRoutingLog
from backend.core.config.settings import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_user():
    class MockUser:
        id = "audit-test-user"
        workspace_id = "audit-test-ws"
        role = "OWNER"
        plan = "pro"
        email = "audit@veklom.local"
        status = "active"
        is_active = True
        is_superuser = False
    return MockUser()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(mock_user):
    token = create_access_token(data={"sub": mock_user.id})
    return {"Authorization": f"Bearer {token}"}


async def _init_tables(*extra_tables):
    """Initialize SQLite tables for testing."""
    tables = [
        AuditLog.__table__,
        User.__table__,
        Workspace.__table__,
        Subscription.__table__,
        KillSwitchState.__table__,
        BudgetRule.__table__,
        ExecutionLog.__table__,
        WalletTransaction.__table__,
        ProviderKey.__table__,
        ProviderRoutingLog.__table__,
    ]
    for t in extra_tables:
        if t not in tables:
            tables.append(t)
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=tables,
        ))


# ---------------------------------------------------------------------------
# 1. Subscription Plans Structure
# ---------------------------------------------------------------------------

def test_subscription_plans_structure(client):
    """Verify plans API returns 4 aligned plans with correct IDs."""
    response = client.get("/api/v1/subscriptions/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 4

    plan_ids = [p["plan_id"] for p in plans]
    assert "free" in plan_ids
    assert "starter" in plan_ids
    assert "pro" in plan_ids
    assert "sovereign" in plan_ids

    # Only the free plan should show $0
    for p in plans:
        if p["plan_id"] == "free":
            assert p["price"] == 0
        else:
            assert p["price"] > 0

    # IDs and tiers must be aligned
    for p in plans:
        assert p["id"] == p["plan_id"]
        assert p["tier"] == p["plan_id"]


# ---------------------------------------------------------------------------
# 2. x402 Config Fail-Closed
# ---------------------------------------------------------------------------

def test_x402_config_fail_closed_invalid(client):
    """x402 /config must return enabled=false when treasury is invalid."""
    with patch.dict(os.environ, {"VEKLOM_TREASURY_ADDRESS": ""}, clear=False):
        response = client.get("/api/v1/x402/config")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert "VEKLOM_TREASURY_ADDRESS" in data["missing_config"]


def test_x402_config_valid_treasury(client):
    """x402 /config returns enabled=true when treasury is a real EVM address."""
    with patch.dict(os.environ, {"VEKLOM_TREASURY_ADDRESS": "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"}, clear=False):
        response = client.get("/api/v1/x402/config")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["missing_config"] == []
        assert data["pay_to"] == "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"


def test_x402_config_zero_address_rejected(client):
    """Zero address must be rejected (fail-closed)."""
    with patch.dict(os.environ, {"VEKLOM_TREASURY_ADDRESS": "0x0000000000000000000000000000000000000001"}, clear=False):
        response = client.get("/api/v1/x402/config")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False


# ---------------------------------------------------------------------------
# 3. Fax Webhook Authentication Matrix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fax_webhook_missing_key(client):
    """Fax inbound without signature header -> 401."""
    await _init_tables()
    payload = {
        "sender_number": "+15550192",
        "receiver_number": "+18005550100",
        "document_url": "https://storage.veklom.com/faxes/test.pdf"
    }
    response = client.post("/api/v1/connectors/fax/inbound", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_fax_webhook_invalid_key(client):
    """Fax inbound with wrong signature -> 403."""
    await _init_tables()
    payload = {
        "sender_number": "+15550192",
        "receiver_number": "+18005550100",
        "document_url": "https://storage.veklom.com/faxes/test.pdf"
    }
    response = client.post(
        "/api/v1/connectors/fax/inbound",
        json=payload,
        headers={"X-Fax-Signature": "wrong_secret_123"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_fax_webhook_valid_key(client):
    """Fax inbound with correct signature -> 201."""
    await _init_tables()
    payload = {
        "sender_number": "+15550192",
        "receiver_number": "+18005550100",
        "document_url": "https://storage.veklom.com/faxes/patient_intake.pdf"
    }
    response = client.post(
        "/api/v1/connectors/fax/inbound",
        json=payload,
        headers={"X-Fax-Signature": settings.FAX_WEBHOOK_SECRET}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["fax_id"].startswith("fax_in_")
    assert data["status"] == "queued"
    assert data["evidence_id"].startswith("evd_")


@pytest.mark.asyncio
async def test_fax_webhook_malformed_payload(client):
    """Fax inbound with valid key but bad body -> 422."""
    await _init_tables()
    response = client.post(
        "/api/v1/connectors/fax/inbound",
        json={"sender_number": "only_one_field"},
        headers={"X-Fax-Signature": settings.FAX_WEBHOOK_SECRET}
    )
    assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 4. Playground Sovereign Fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_playground_sovereign_fallback(client, mock_user, auth_headers):
    """When OPENAI_API_KEY is missing, GPT-4o requests must fallback to sovereign."""
    await _init_tables()

    # Seed workspace and user
    async with async_session() as db:
        ws = Workspace(
            id=mock_user.workspace_id,
            name="Audit Test WS",
            slug="audit-test-ws",
            is_active=True,
            license_tier="pro"
        )
        usr = User(
            id=mock_user.id,
            email=mock_user.email,
            full_name="Audit Tester",
            hashed_password="",
            role="OWNER",
            status="active",
            is_active=True,
            workspace_id=mock_user.workspace_id
        )
        wt = WalletTransaction(
            id=f"tx_{uuid.uuid4().hex[:12]}",
            workspace_id=mock_user.workspace_id,
            user_id=mock_user.id,
            amount=100.0,
            tx_type="topup",
            description="Test balance"
        )
        db.add_all([ws, usr, wt])
        await db.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch.object(settings, "OPENAI_API_KEY", ""):
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello from audit test"}]
            }
            response = client.post("/api/v1/ai/complete", json=payload, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "sovereign"
            assert "[Sovereign Fallback" in data["response_text"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 5. Control-Plane Map Identity Surface
# ---------------------------------------------------------------------------

def test_control_plane_map(client, auth_headers):
    """Verify /sys/control-plane-map returns all mounted modules."""
    response = client.get("/api/v1/sys/control-plane-map", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "Veklom" in data["control_plane"]
    assert "modules" in data
    assert len(data["modules"]) >= 10

    module_names = [m["name"] for m in data["modules"]]
    assert "Workspace" in module_names
    assert "AI Inference" in module_names
    assert "x402 Payment Gateway" in module_names
    assert "Fax Connector" in module_names
    assert "Evidence Ledger" in module_names

    # Every module must have a path and status
    for m in data["modules"]:
        assert "path" in m
        assert m["status"] == "active"


# ---------------------------------------------------------------------------
# 6. Onboarding Vertical Selection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_onboarding_vertical_valid(client, mock_user, auth_headers):
    """Setting a valid vertical stores it on the workspace."""
    await _init_tables()

    # Seed workspace
    async with async_session() as db:
        ws = Workspace(
            id=mock_user.workspace_id,
            name="Vertical Test WS",
            slug=f"vertical-test-{uuid.uuid4().hex[:6]}",
            is_active=True
        )
        db.add(ws)
        await db.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.post(
            "/api/v1/workspace/onboarding/vertical",
            json={"vertical": "healthcare_hospital"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "vertical_selected"
        assert data["vertical"] == "healthcare_hospital"
        assert data["redirect"] == "/control-plane-next/"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_onboarding_vertical_invalid(client, mock_user, auth_headers):
    """Setting an invalid vertical returns 400."""
    await _init_tables()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.post(
            "/api/v1/workspace/onboarding/vertical",
            json={"vertical": "fake_industry"},
            headers=auth_headers
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_onboarding_vertical_get(client, mock_user, auth_headers):
    """GET vertical returns available list."""
    await _init_tables()

    # Update the existing workspace (created by previous test) or create new
    async with async_session() as db:
        result = await db.execute(select(Workspace).where(Workspace.id == mock_user.workspace_id))
        ws = result.scalar_one_or_none()
        if ws:
            ws.industry = "finance_banking"
        else:
            ws = Workspace(
                id=mock_user.workspace_id,
                name="Get Vertical WS",
                slug=f"get-vert-{uuid.uuid4().hex[:6]}",
                is_active=True,
                industry="finance_banking"
            )
            db.add(ws)
        await db.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.get(
            "/api/v1/workspace/onboarding/vertical",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vertical"] == "finance_banking"
        assert "verticals_available" in data
        assert "healthcare_hospital" in data["verticals_available"]
        assert len(data["verticals_available"]) == 6
    finally:
        app.dependency_overrides.clear()
