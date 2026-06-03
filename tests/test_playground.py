import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"
os.environ["VEKLOM_TREASURY_ADDRESS"] = "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"
os.environ["X402_DISABLED"] = "true"

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.apps.api.main import app
from backend.core.database.database import async_session, engine, Base
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.security import KillSwitchState
from backend.db.models.billing import BudgetRule, Subscription, WalletTransaction
from backend.db.models.ai import ExecutionLog
from backend.db.models.provider import ProviderKey, ProviderRoutingLog
from backend.core.security.auth import get_current_user, create_access_token

@pytest.fixture
def mock_user():
    class MockUser:
        id = "test-playground-user"
        workspace_id = "test-playground-ws"
        role = "OWNER"
        plan = "pro"
        email = "play@veklom.local"
        status = "active"
        is_active = True
        is_superuser = False
    return MockUser()

@pytest.mark.asyncio
async def test_playground_openai_fallback(mock_user):
    # Initialize only required tables to avoid JSONB compilation errors on decision_frames in SQLite
    tables = [
        User.__table__,
        Workspace.__table__,
        KillSwitchState.__table__,
        BudgetRule.__table__,
        ExecutionLog.__table__,
        WalletTransaction.__table__,
        ProviderKey.__table__,
        ProviderRoutingLog.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=tables,
        ))

    # Mock DB seeding
    async with async_session() as db:
        ws = Workspace(
            id=mock_user.workspace_id,
            name="Playground Workspace",
            slug="playground-ws",
            is_active=True,
            license_tier="pro"
        )
        usr = User(
            id=mock_user.id,
            email=mock_user.email,
            full_name="Play Tester",
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
            description="Test initial balance"
        )
        db.add_all([ws, usr, wt])
        await db.commit()

    with TestClient(app) as client:
        # Mock auth dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user

        # Generate token
        token = create_access_token(data={"sub": mock_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        # Force OpenAI key to be absent in settings
        with patch("backend.core.config.settings.settings.OPENAI_API_KEY", ""):
            # Request completion for gpt-4o (which requires OpenAI API key)
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "How's the weather?"}]
            }
            
            # Test completion route
            response = client.post("/api/v1/ai/complete", json=payload, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "[Sovereign Fallback - OpenAI API Key Not Configured. Using Local Enclave]" in data["response_text"]
            assert data["provider"] == "sovereign"
            assert data["model"] == "Veklom-Llama3-Sovereign-v1"

            # Test inference route
            response_inf = client.post("/api/v1/ai/inference", json=payload, headers=headers)
            assert response_inf.status_code == 200
            data_inf = response_inf.json()
            assert "[Sovereign Fallback - OpenAI API Key Not Configured. Using Local Enclave]" in data_inf["response_text"]
            assert data_inf["provider"] == "sovereign"
            assert data_inf["model"] == "Veklom-Llama3-Sovereign-v1"

    app.dependency_overrides.clear()
