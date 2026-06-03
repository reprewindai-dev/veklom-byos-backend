import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file:test_playground_db?mode=memory&cache=shared&uri=true"
os.environ["REDIS_ENABLED"] = "False"

import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
import uuid

from backend.apps.api.main import app
from backend.core.database.database import async_session, engine, Base, get_db_session
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.billing import Subscription, BudgetRule, WalletTransaction
from backend.db.models.security import KillSwitchState, AuditLog
from backend.db.models.ai import ExecutionLog
from backend.core.security.auth import get_current_user, create_access_token

class MockUser:
    id = "test-playground-user"
    workspace_id = "test-playground-ws"
    role = "OWNER"
    plan = "pro"
    email = "play@veklom.local"
    status = "active"
    is_active = True
    is_superuser = False

async def run_debug():
    # Initialize the database schema for the test
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[
                User.__table__, Workspace.__table__, Subscription.__table__,
                KillSwitchState.__table__, BudgetRule.__table__, ExecutionLog.__table__,
                WalletTransaction.__table__, AuditLog.__table__
            ]
        ))

    # Mock DB seeding
    async with async_session() as db:
        ws = Workspace(
            id=MockUser.workspace_id,
            name="Playground Workspace",
            slug="playground-ws",
            is_active=True,
            license_tier="pro"
        )
        usr = User(
            id=MockUser.id,
            email=MockUser.email,
            full_name="Play Tester",
            hashed_password="",
            role="OWNER",
            status="active",
            is_active=True,
            workspace_id=MockUser.workspace_id
        )
        wt = WalletTransaction(
            id=f"tx_{uuid.uuid4().hex[:12]}",
            workspace_id=MockUser.workspace_id,
            user_id=MockUser.id,
            amount=100.0,
            tx_type="topup",
            description="Test initial balance"
        )
        db.add_all([ws, usr, wt])
        await db.commit()

    # Query directly via get_db_session to see if usr is there
    async with get_db_session() as db:
        res = await db.execute(select(User).where(User.id == MockUser.id))
        user = res.scalar_one_or_none()
        print(f"Direct query: found user? {user is not None}")

    client = TestClient(app)

    # Mock auth dependency
    app.dependency_overrides[get_current_user] = lambda: MockUser

    # Generate token
    token = create_access_token(data={"sub": MockUser.id})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "How's the weather?"}]
    }

    response_inf = client.post("/api/v1/ai/inference", json=payload, headers=headers)
    print(f"Inference Response Status: {response_inf.status_code}")
    print(f"Inference Response Body: {response_inf.json()}")
    print(f"Inference Response Headers: {dict(response_inf.headers)}")

if __name__ == "__main__":
    asyncio.run(run_debug())
