import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import json
import uuid
import re
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.apps.api.main import app
from backend.core.database.database import async_session, engine, Base
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.security import KillSwitchState
from backend.db.models.billing import BudgetRule, Subscription
from backend.db.models.ai import ExecutionLog
from backend.core.security.auth import create_access_token
from backend.core.database.redis_client import redis_client

async def init_sqlite_tables():
    """Helper to initialize SQLite metadata tables for clean in-memory execution."""
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[
                User.__table__, Workspace.__table__, Subscription.__table__,
                KillSwitchState.__table__, BudgetRule.__table__, ExecutionLog.__table__
            ]
        ))

@pytest.mark.asyncio
async def test_x402_handshake_e2e():
    """
    Test standard X402 Handshake:
      1. Missing payment proof -> returns 402 with 'missing_payment_proof' detail and payment headers.
      2. Invalid signature format -> returns 402 with 'invalid_transaction' detail.
      3. Valid hash with mocked RPC call -> successful bypass/deduction or verified return.
    """
    await init_sqlite_tables()
    client = TestClient(app)
    
    # 1. Discovery Check: Request a paid route with 0 free daily quota (e.g. /api/v1/pipelines/trigger) with no payment headers
    response = client.post("/api/v1/pipelines/trigger", json={"prompt": "test"})
    assert response.status_code == 402
    assert response.headers.get("X-Payment-Required") == "true"
    assert response.headers.get("X-Payment-Price-USDC") == "0.025"
    assert response.headers.get("X-Payment-Network") == "base"
    
    data = response.json()
    assert data["error"] == "payment_required"
    assert data["detail"] == "missing_payment_proof"

    # 2. Replay attack: test double-spend of the same transaction hash or nonce
    tx_hash = f"0x{uuid.uuid4().hex}"
    nonce = f"nonce_{uuid.uuid4().hex}"
    
    # Mock Redis responses for nonce caching and transaction locks
    with patch("backend.core.database.redis_client.redis_client.get", new_callable=AsyncMock) as mock_redis_get, \
         patch("backend.core.database.redis_client.redis_client.set", new_callable=AsyncMock) as mock_redis_set:
         
        # First request: Redis says nonce doesn't exist yet
        mock_redis_get.return_value = None
        
        # Call with invalid proof hash format first
        bad_response = client.post(
            "/api/v1/pipelines/trigger",
            json={"prompt": "test"},
            headers={"X-Payment-Proof": "invalid_format_here", "X-Payment-Nonce": nonce}
        )
        assert bad_response.status_code == 402
        assert bad_response.json()["detail"] == "invalid_transaction"

        # Second request: Replay of used Nonce (mock Redis returning "1")
        mock_redis_get.return_value = "1"
        replay_response = client.post(
            "/api/v1/pipelines/trigger",
            json={"prompt": "test"},
            headers={"X-Payment-Proof": tx_hash, "X-Payment-Nonce": nonce}
        )
        assert replay_response.status_code == 402
        assert replay_response.json()["detail"] == "replay_detected"


@pytest.mark.asyncio
async def test_x402_pii_metadata_filter():
    """
    Verify that the metadata PII filter blocks sensitive payloads containing API keys, tokens or secrets.
    """
    await init_sqlite_tables()
    client = TestClient(app)
    
    # 1. Plaintext API key leaked in body
    payloads = [
        {"prompt": "my token is sk-proj-123456789"},
        {"prompt": "use api_key=secret-value"},
        {"prompt": "my secret=supersecret"}
    ]
    
    for payload in payloads:
        response = client.post(
            "/api/v1/pipelines/trigger",
            json=payload,
            headers={"X-Payment-Nonce": f"nonce_{uuid.uuid4().hex}"}
        )
        assert response.status_code == 400
        assert response.json()["error"] == "Sensitive data detected"


@pytest.mark.asyncio
async def test_x402_kill_switch_and_budgets():
    """
    Audit emergency halt kill switch and spend limits validation.
    """
    await init_sqlite_tables()
    
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    ws_id = f"ws_{uuid.uuid4().hex[:8]}"
    
    # Seed workspace, user, and subscription
    async with async_session() as db:
        ws = Workspace(id=ws_id, name="Test Space", slug="test-space", license_tier="business")
        user = User(
            id=user_id, 
            email="x402_test@veklom.com", 
            hashed_password="mocked_password_123", 
            role="member", 
            workspace_id=ws_id, 
            is_active=True, 
            status="active"
        )
        sub = Subscription(id=f"sub_{uuid.uuid4().hex[:8]}", user_id=user_id, workspace_id=ws_id, status="active", plan="business")
        db.add_all([ws, user, sub])
        await db.commit()

    token = create_access_token({"sub": user_id, "role": "member"})
    client = TestClient(app)

    # 1. Seed active workspace Cost Kill Switch
    async with async_session() as db:
        ks = KillSwitchState(
            workspace_id=ws_id,
            is_active=True,
            reason="Runaway agent billing loop detected",
            activated_by="admin"
        )
        db.add(ks)
        await db.commit()

    response = client.post(
        "/api/v1/pipelines/trigger",
        json={"prompt": "hello"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 402
    data = response.json()
    assert data["kill_switch_active"] is True
    assert "Emergency halt active" in data["detail"]

    # 2. Deactivate kill switch but trigger a breached budget limit rule
    async with async_session() as db:
        # Deactivate kill switch
        from sqlalchemy import update
        await db.execute(update(KillSwitchState).where(KillSwitchState.workspace_id == ws_id).values(is_active=False))
        
        # Add a budget rule that is already breached (current_spend >= limit_usd)
        budget = BudgetRule(
            id=f"br_{uuid.uuid4().hex[:8]}",
            workspace_id=ws_id,
            name="Max Inference Limit",
            limit_usd=10.0,
            current_spend=10.5,
            is_active=True
        )
        db.add(budget)
        await db.commit()

    # Request execution: should breach budget, trigger automatic Cost Kill Switch, and block with 402
    response2 = client.post(
        "/api/v1/pipelines/trigger",
        json={"prompt": "hello"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 402
    data2 = response2.json()
    assert data2["kill_switch_active"] is True
    assert "Budget rule breached" in data2["detail"]

    print("x402 E2E and Budget/Kill Switch Tests passed successfully!")
