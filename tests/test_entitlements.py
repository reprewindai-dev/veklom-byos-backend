import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
from fastapi.testclient import TestClient

from backend.apps.api.main import app
from backend.core.security.auth import get_current_user, create_access_token
from backend.core.database.database import Base, engine

@pytest.fixture
def mock_user_free():
    class MockUser:
        id = "test-user-free"
        workspace_id = "test-ws-free"
        role = "OWNER"
        plan = "free"
        email = "free@veklom.local"
        status = "active"
        is_active = True
    return MockUser()

@pytest.fixture
def mock_user_pro():
    class MockUser:
        id = "test-user-pro"
        workspace_id = "test-ws-pro"
        role = "OWNER"
        plan = "pro"  # maps to standard
        email = "pro@veklom.local"
        status = "active"
        is_active = True
    return MockUser()

@pytest.fixture
def mock_user_sovereign():
    class MockUser:
        id = "test-user-sovereign"
        workspace_id = "test-ws-sov"
        role = "OWNER"
        plan = "sovereign"  # maps to regulated
        email = "sovereign@veklom.local"
        status = "active"
        is_active = True
    return MockUser()

@pytest.mark.asyncio
async def test_entitlement_gating_scenarios(mock_user_free, mock_user_pro, mock_user_sovereign):
    # Setup sqlite tables
    from backend.db.models.workspace import Workspace
    from backend.db.models.user import User
    from backend.db.models.ai import ExecutionLog

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[Workspace.__table__, User.__table__, ExecutionLog.__table__]
        ))

    client = TestClient(app)

    # 1. Test Free User
    app.dependency_overrides[get_current_user] = lambda: mock_user_free
    headers_free = {"Authorization": f"Bearer {create_access_token(data={'sub': mock_user_free.id})}"}
    
    # Check production run (gated on founding, Free has level 0 < required 1)
    resp = client.get("/api/v1/workspace/entitlements/check?action=production_run", headers=headers_free)
    assert resp.status_code == 200
    data = resp.json()
    assert data["canView"] is True
    assert data["canPreview"] is True
    assert data["canExecute"] is False
    assert data["currentTier"] == "free"
    assert data["requiredTier"] == "founding"
    assert "quota_gate" in data["gateType"]
    
    # Check deploy action (gated on standard, Free has level 0 < required 2)
    resp = client.get("/api/v1/workspace/entitlements/check?action=deploy", headers=headers_free)
    assert resp.status_code == 200
    data = resp.json()
    assert data["canExecute"] is False
    assert data["requiredTier"] == "standard"
    assert data["marketplaceAlternative"]["moduleId"] == "deploy-gate"
    
    # Check POST endpoint
    resp = client.post("/api/v1/workspace/entitlements/check", json={"action": "deploy"}, headers=headers_free)
    assert resp.status_code == 200
    assert resp.json()["canExecute"] is False

    # 2. Test Pro (Standard) User
    app.dependency_overrides[get_current_user] = lambda: mock_user_pro
    headers_pro = {"Authorization": f"Bearer {create_access_token(data={'sub': mock_user_pro.id})}"}
    
    # Check production run (Standard level 2 >= founding level 1)
    resp = client.get("/api/v1/workspace/entitlements/check?action=production_run", headers=headers_pro)
    assert resp.status_code == 200
    assert resp.json()["canExecute"] is True
    
    # Check deploy action (Standard level 2 >= standard level 2)
    resp = client.get("/api/v1/workspace/entitlements/check?action=deploy", headers=headers_pro)
    assert resp.status_code == 200
    assert resp.json()["canExecute"] is True

    # Check export_signed_evidence (Regulated level 3 > standard level 2)
    resp = client.get("/api/v1/workspace/entitlements/check?action=export_signed_evidence", headers=headers_pro)
    assert resp.status_code == 200
    data = resp.json()
    assert data["canExecute"] is False
    assert data["requiredTier"] == "regulated"

    # 3. Test Sovereign (Regulated) User
    app.dependency_overrides[get_current_user] = lambda: mock_user_sovereign
    headers_sovereign = {"Authorization": f"Bearer {create_access_token(data={'sub': mock_user_sovereign.id})}"}
    
    # Check export_signed_evidence (Regulated level 3 >= regulated level 3)
    resp = client.get("/api/v1/workspace/entitlements/check?action=export_signed_evidence", headers=headers_sovereign)
    assert resp.status_code == 200
    assert resp.json()["canExecute"] is True

    app.dependency_overrides.clear()
