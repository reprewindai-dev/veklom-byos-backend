import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
from datetime import datetime, timedelta

from backend.apps.api.main import app
from backend.core.database.database import async_session, engine, Base
from backend.db.models.billing import Subscription
from backend.db.models.user import User
from backend.db.models.workspace import Workspace

@pytest.fixture
def test_user_fixture():
    class TestUser:
        id = f"user_{uuid.uuid4().hex[:12]}"
        email = f"billing-{uuid.uuid4().hex[:6]}@veklom.local"
        workspace_id = f"ws_{uuid.uuid4().hex[:12]}"
        role = "OWNER"
        plan = "free"
        full_name = "Billing Tester"
        status = "active"
        is_active = True
        is_superuser = False
        mfa_enabled = False
        github_username = ""
        github_id = ""
        github_access_token = ""
        created_at = datetime.utcnow()
    return TestUser()

@pytest.mark.asyncio
async def test_subscription_plans_and_normalization(test_user_fixture):
    # Initialize the database schema for the test
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[Subscription.__table__, User.__table__, Workspace.__table__]
        ))

    client = TestClient(app)

    # Mock authentication dependency
    from backend.core.security.auth import get_current_user, create_access_token
    app.dependency_overrides[get_current_user] = lambda: test_user_fixture

    # Generate a real JWT token to satisfy ZeroTrustMiddleware
    token = create_access_token(data={"sub": test_user_fixture.id})
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # 1. Verify subscription plans returns aligned keys (starter, pro, sovereign)
        plans_resp = client.get("/api/v1/subscriptions/plans")
        assert plans_resp.status_code == 200
        plans = plans_resp.json()
        assert len(plans) == 4
        
        plan_ids = [p["plan_id"] for p in plans]
        ids = [p["id"] for p in plans]
        tiers = [p["tier"] for p in plans]
        
        # Verify plans IDs are aligned with keys
        assert "free" in plan_ids
        assert "starter" in plan_ids
        assert "pro" in plan_ids
        assert "sovereign" in plan_ids
        
        assert ids == plan_ids
        assert tiers == plan_ids

        # 2. Verify empty state / free tier returned initially
        current_resp = client.get("/api/v1/subscriptions/current", headers=headers)
        assert current_resp.status_code == 200
        current = current_resp.json()
        assert current["plan"] == "free"
        assert current["status"] == "none"

        # 3. Insert a legacy subscription in the DB and check if it is normalized correctly
        async with async_session() as db:
            # Seed the workspace first
            ws = Workspace(
                id=test_user_fixture.workspace_id,
                name="Billing Test Workspace",
                slug=f"billing-test-ws-{uuid.uuid4().hex[:8]}",
                is_active=True,
                industry="generic",
            )
            db.add(ws)
            await db.flush()

            # Seed standard user to pass any me checks
            usr = User(
                id=test_user_fixture.id,
                email=test_user_fixture.email,
                full_name="Billing Tester",
                hashed_password="",
                role="OWNER",
                status="active",
                is_active=True,
                workspace_id=test_user_fixture.workspace_id,
            )
            db.add(usr)
            await db.flush()

            # Seed legacy subscription: "founding"
            legacy_sub = Subscription(
                id=f"sub_{uuid.uuid4().hex[:12]}",
                workspace_id=test_user_fixture.workspace_id,
                user_id=test_user_fixture.id,
                stripe_subscription_id="sub_stripe_123",
                plan="founding",
                status="active",
                current_period_end=datetime.utcnow() + timedelta(days=30),
            )
            db.add(legacy_sub)
            await db.commit()

        # Check `/subscriptions/current` normalization ("founding" -> "starter")
        current_resp = client.get("/api/v1/subscriptions/current", headers=headers)
        assert current_resp.status_code == 200
        current = current_resp.json()
        assert current["plan"] == "starter"
        assert current["status"] == "active"

        # Check `/auth/me` normalization
        me_resp = client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["plan"] == "starter"
        assert me_data["workspace"]["plan"] == "starter"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()
