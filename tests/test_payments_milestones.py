import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

# SQLite fallback mapping for PostgreSQL JSONB
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"

from backend.apps.api.main import app
from backend.core.database.database import get_db, Base, engine, async_session
from backend.core.security.auth import get_current_user, create_access_token
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.marketplace import MarketplaceListing, InstalledAsset, Vendor
from backend.db.models.billing import WalletTransaction, Subscription, BudgetRule
from backend.db.models.security import AuditLog, KillSwitchState
from backend.db.models.ai import ExecutionLog
from backend.db.models.provider import ProviderKey, ProviderRoutingLog

# Configure a test user & workspace
class MockUser:
    id = "mock-user-id"
    email = "test-merchant@veklom.local"
    workspace_id = "mock-ws-id"
    role = "OWNER"
    status = "active"
    is_active = True
    is_superuser = False


@pytest.fixture
def mock_user_instance():
    return MockUser()


@pytest.fixture
def auth_headers(mock_user_instance):
    token = create_access_token(data={"sub": mock_user_instance.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
async def clean_db():
    """Drops and recreates SQLite tables for each test for absolute isolation."""
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
        MarketplaceListing.__table__,
        InstalledAsset.__table__,
        Vendor.__table__,
    ]
    async with engine.begin() as conn:
        # Drop all tables first to get a completely clean state
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(
            bind=sync_conn,
            tables=tables,
            checkfirst=True
        ))
        # Create all tables
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=tables,
            checkfirst=True
        ))
    yield
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(
            bind=sync_conn,
            tables=tables,
            checkfirst=True
        ))


@pytest.fixture
def client(mock_user_instance):
    app.dependency_overrides[get_current_user] = lambda: mock_user_instance
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stripe_onboarding_mock_express(client, auth_headers):
    # Seed workspace & user
    async with async_session() as db:
        ws = Workspace(id=MockUser.workspace_id, name="Test WS", slug="mock-ws-id", is_active=True)
        usr = User(
            id=MockUser.id,
            email=MockUser.email,
            full_name="Tester",
            hashed_password="",
            role="OWNER",
            status="active",
            is_active=True,
            workspace_id=MockUser.workspace_id
        )
        db.add_all([ws, usr])
        await db.commit()

    # 1. Trigger express onboarding generation
    response = client.post("/api/v1/x402/onboarding/express", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "onboarding_started"
    assert "account_id" in data
    assert "stripe_url" in data
    
    # URL should contain the success callback parameters since stripe key is a mockup
    assert "onboarding/callback" in data["stripe_url"]
    
    # 2. Simulate user redirected back to callback
    callback_res = client.get(
        f"/api/v1/x402/onboarding/callback?status=success&account_id={data['account_id']}&user_id={MockUser.id}",
        follow_redirects=False
    )
    # Assert redirect back to frontend workspace settings
    assert callback_res.status_code == 307
    assert "workspace#/settings" in callback_res.headers["location"]
    
    # 3. Check DB states - vendor record should be approved and complete
    async with async_session() as db:
        result = await db.execute(select(Vendor).where(Vendor.user_id == MockUser.id))
        vendor = result.scalars().first()
        assert vendor is not None
        assert vendor.stripe_account_id == data["account_id"]
        assert vendor.onboarding_complete is True
        assert vendor.status == "approved"


@pytest.mark.asyncio
async def test_milestone_pricing_progressive(client):
    # Under Level 1: 1 workspace
    async with async_session() as db:
        ws = Workspace(id="ws-1", name="WS 1", slug="ws-1", is_active=True)
        db.add(ws)
        await db.commit()
        
    res1 = client.get("/api/v1/subscriptions/plans")
    assert res1.status_code == 200
    plans1 = res1.json()
    starter1 = next(p for p in plans1 if p["id"] == "starter")
    assert starter1["price"] == 395  # Level 1 Price
    
    # Under Level 2: 60 workspaces
    async with async_session() as db:
        for i in range(2, 62):
            ws = Workspace(id=f"ws-{i}", name=f"WS {i}", slug=f"ws-{i}", is_active=True)
            db.add(ws)
        await db.commit()
        
    res2 = client.get("/api/v1/subscriptions/plans")
    assert res2.status_code == 200
    plans2 = res2.json()
    starter2 = next(p for p in plans2 if p["id"] == "starter")
    assert starter2["price"] == 495  # Level 2 Price

    # Under Level 3: 260 workspaces
    async with async_session() as db:
        for i in range(62, 262):
            ws = Workspace(id=f"ws-{i}", name=f"WS {i}", slug=f"ws-{i}", is_active=True)
            db.add(ws)
        await db.commit()
        
    res3 = client.get("/api/v1/subscriptions/plans")
    assert res3.status_code == 200
    plans3 = res3.json()
    starter3 = next(p for p in plans3 if p["id"] == "starter")
    assert starter3["price"] == 595  # Level 3 Price


@pytest.mark.asyncio
async def test_native_washing_vs_splits(client, auth_headers):
    async with async_session() as db:
        # Seed user and workspace
        ws = Workspace(id=MockUser.workspace_id, name="Test WS", slug="mock-ws-id", is_active=True)
        usr = User(
            id=MockUser.id,
            email=MockUser.email,
            full_name="Tester",
            hashed_password="",
            role="OWNER",
            status="active",
            is_active=True,
            workspace_id=MockUser.workspace_id
        )
        db.add_all([ws, usr])
        
        # 1. Setup workspace wallets with balance
        tx1 = WalletTransaction(
            id="tx-initial",
            user_id=MockUser.id,
            workspace_id=MockUser.workspace_id,
            amount=2000.0,
            tx_type="topup",
            description="Initial reserve funding"
        )
        db.add(tx1)
        
        # 2. Setup Third-party Developer Listing
        listing1 = MarketplaceListing(
            id="ls_finance_prompts",
            vendor_id="vendor-numera-id",
            name="Finance Prompt Pack",
            description="Production prompts",
            category="prompt_packs",
            price=179.0,
            pricing_model="one_time",
            status="published",
            config_json={"vendor_slug": "numera"}
        )
        db.add(listing1)
        
        # Setup vendor profile for split crediting
        v = Vendor(
            id="vendor-numera-id",
            user_id="numera-user-id",
            business_name="Numera Inc",
            stripe_account_id="acct_numera123",
            onboarding_complete=True,
            status="approved",
            total_revenue=0.0
        )
        db.add(v)
        
        # 3. Setup First-party Native Listing for washing
        listing2 = MarketplaceListing(
            id="ls_clinical_rag",
            vendor_id="veklom_native",
            name="Clinical RAG",
            description="HIPAA RAG",
            category="rag_templates",
            price=1490.0,
            pricing_model="monthly",
            status="published",
            config_json={"vendor_slug": "veklom_native"}
        )
        db.add(listing2)
        
        await db.commit()
        
    # --- Purchase Listing 1 (Third-Party Split) ---
    inst1 = client.post("/api/v1/marketplace/listings/ls_finance_prompts/install", headers=auth_headers)
    assert inst1.status_code == 200
    
    # Assert Wallet Debited & Developer Credited
    async with async_session() as db:
        # Sum of wallet transactions (2000 - 179 = 1821)
        from sqlalchemy import func
        sum_bal = await db.scalar(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
            .where(WalletTransaction.workspace_id == MockUser.workspace_id)
        )
        assert sum_bal == 1821.0
        
        # Vendor total revenue should be $179 (since revenue < $2500, no fee)
        vendor = await db.scalar(select(Vendor).where(Vendor.id == "vendor-numera-id"))
        assert vendor.total_revenue == 179.0
        
    # --- Purchase Listing 2 (Washed First-Party) ---
    inst2 = client.post("/api/v1/marketplace/listings/ls_clinical_rag/install", headers=auth_headers)
    assert inst2.status_code == 200
    
    async with async_session() as db:
        # Wallet balance should be debited (1821 - 1490 = 331)
        from sqlalchemy import func
        sum_bal = await db.scalar(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
            .where(WalletTransaction.workspace_id == MockUser.workspace_id)
        )
        assert sum_bal == 331.0
        
        # Verify NO vendor with slug 'veklom_native' received credit in the database
        vendor_check = await db.scalar(select(Vendor).where(Vendor.user_id == "veklom_native"))
        assert vendor_check is None


@pytest.mark.asyncio
async def test_review_reward_and_robot_badge(client, auth_headers):
    async with async_session() as db:
        # Seed user and workspace
        ws = Workspace(id=MockUser.workspace_id, name="Test WS", slug="mock-ws-id", is_active=True)
        usr = User(
            id=MockUser.id,
            email=MockUser.email,
            full_name="Tester",
            hashed_password="",
            role="OWNER",
            status="active",
            is_active=True,
            workspace_id=MockUser.workspace_id
        )
        db.add_all([ws, usr])
        
        # Add a listing in catalog
        listing = MarketplaceListing(
            id="ls_clinical_rag",
            vendor_id="veklom_native",
            name="Clinical RAG",
            description="HIPAA RAG",
            category="rag_templates",
            price=1490.0,
            pricing_model="monthly",
            status="published",
            config_json={"vendor_slug": "veklom_native", "badges": ["HIPAA"]}
        )
        db.add(listing)
        await db.commit()
        
    # 1. Human review submission
    review_res = client.post(
        "/api/v1/marketplace/listings/ls_clinical_rag/review",
        json={"rating": 5.0, "comment": "Amazing PHI-safe tools!", "is_robot": False},
        headers=auth_headers
    )
    assert review_res.status_code == 200
    rev_data = review_res.json()
    assert rev_data["reward_awarded"] is True
    assert rev_data["reward_amount"] == 5.0
    
    # 2. Check Wallet Transaction Credit
    async with async_session() as db:
        tx = await db.scalar(
            select(WalletTransaction).where(
                WalletTransaction.workspace_id == MockUser.workspace_id,
                WalletTransaction.amount == 5.0
            )
        )
        assert tx is not None
        assert "Review Reward" in tx.description
        
        # Audit Log Check
        audit = await db.scalar(
            select(AuditLog).where(
                AuditLog.resource_type == "marketplace_review",
                AuditLog.resource_id == "ls_clinical_rag"
            )
        )
        assert audit is not None
        assert audit.details["rating"] == 5.0
        assert audit.details["is_robot"] is False
        
    # 3. Test Reward Cap Limit (enforce 5 limits)
    # Submit 5 more reviews (making 6 total)
    for i in range(5):
        client.post(
            "/api/v1/marketplace/listings/ls_clinical_rag/review",
            json={"rating": 4.5, "comment": f"Great feedback {i}", "is_robot": False},
            headers=auth_headers
        )
        
    async with async_session() as db:
        # We should only have 5 reward transactions of 5.0
        from sqlalchemy import func
        tx_count = await db.scalar(
            select(func.count(WalletTransaction.id)).where(
                WalletTransaction.workspace_id == MockUser.workspace_id,
                WalletTransaction.amount == 5.0
            )
        )
        assert tx_count == 5  # Limit of 5 rewards enforced
        
    # 4. Test Robot review badge appending
    robot_res = client.post(
        "/api/v1/marketplace/listings/ls_clinical_rag/review",
        json={"rating": 4.9, "comment": "Verification suite pass", "is_robot": True},
        headers=auth_headers
    )
    assert robot_res.status_code == 200
    assert robot_res.json()["reward_awarded"] is False
    
    async with async_session() as db:
        item = await db.scalar(select(MarketplaceListing).where(MarketplaceListing.id == "ls_clinical_rag"))
        badges = item.config_json.get("badges", [])
        assert "Robot Reviewed: 4.9★" in badges


@pytest.mark.asyncio
async def test_marketplace_automated_pricing_milestones(client, auth_headers):
    # Seed workspace, user, and listing
    async with async_session() as db:
        ws = Workspace(id=MockUser.workspace_id, name="Test WS", slug="mock-ws-id", is_active=True)
        usr = User(
            id=MockUser.id,
            email=MockUser.email,
            full_name="Tester",
            hashed_password="",
            role="OWNER",
            status="active",
            is_active=True,
            workspace_id=MockUser.workspace_id
        )
        db.add_all([ws, usr])
        
        listing = MarketplaceListing(
            id="ls_clinical_rag",
            vendor_id="veklom_native",
            name="Clinical RAG",
            description="HIPAA RAG",
            category="rag_templates",
            price=1000.0,
            pricing_model="monthly",
            status="published",
            downloads=0,
            config_json={"vendor_slug": "veklom_native", "target_price": 1000.0}
        )
        db.add(listing)
        await db.commit()

    # 1. 0 downloads (trust building stage) -> should be 20% = $200.00
    res1 = client.get("/api/v1/marketplace/listings/ls_clinical_rag", headers=auth_headers)
    assert res1.status_code == 200
    assert res1.json()["price"] == 200.0
    
    # 2. 20 downloads (early adoption stage) -> should be 50% = $500.00
    async with async_session() as db:
        item = await db.scalar(select(MarketplaceListing).where(MarketplaceListing.id == "ls_clinical_rag"))
        item.downloads = 20
        await db.commit()

    res2 = client.get("/api/v1/marketplace/listings/ls_clinical_rag", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["price"] == 500.0

    # 3. 120 downloads (mature target stage) -> should be 100% = $1000.00
    async with async_session() as db:
        item = await db.scalar(select(MarketplaceListing).where(MarketplaceListing.id == "ls_clinical_rag"))
        item.downloads = 120
        await db.commit()

    res3 = client.get("/api/v1/marketplace/listings/ls_clinical_rag", headers=auth_headers)
    assert res3.status_code == 200
    assert res3.json()["price"] == 1000.0


@pytest.mark.asyncio
async def test_marketplace_density_pricing_calibration(client, auth_headers):
    # Seed workspace, user, and 5 listings in the same category
    async with async_session() as db:
        ws = Workspace(id=MockUser.workspace_id, name="Test WS", slug="mock-ws-id", is_active=True)
        usr = User(
            id=MockUser.id,
            email=MockUser.email,
            full_name="Tester",
            hashed_password="",
            role="OWNER",
            status="active",
            is_active=True,
            workspace_id=MockUser.workspace_id
        )
        db.add_all([ws, usr])
        
        # Add 5 generic listings to generic_tools category to trigger dime-a-dozen calibration (density >= 5 -> 60%)
        for i in range(1, 6):
            listing = MarketplaceListing(
                id=f"ls_tool_{i}",
                vendor_id="veklom_native",
                name=f"Generic Tool {i}",
                description=f"Description {i}",
                category="generic_tools",
                price=1000.0,
                pricing_model="monthly",
                status="published",
                downloads=120 if i == 1 else 0,  # 120 downloads on the first tool to reach 100% milestone factor
                config_json={"vendor_slug": "veklom_native", "target_price": 1000.0}
            )
            db.add(listing)
        await db.commit()

    # Query the first tool
    res = client.get("/api/v1/marketplace/listings/ls_tool_1", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    
    # 100% milestone * 60% density multiplier = 600.0
    assert data["price"] == 600.0
    assert data["target_price"] == 1000.0
    assert data["density_multiplier"] == 0.60
    assert data["category_density"] == 5
    assert data["is_rare"] is False
    assert data["sovereign_baseline_premium"] is True
    assert "Target Price ($1000.00) * Milestone Factor (100%) * Density Multiplier (60%)" in data["pricing_formula"]


@pytest.mark.asyncio
async def test_vendor_pending_stripe_cannot_publish_paid(async_session, auth_headers):
    # 4. vendor pending Stripe status cannot publish paid listing
    from httpx import AsyncClient
    from backend.apps.api.main import app
    from backend.db.models.marketplace import Vendor, MarketplaceListing
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a paid listing
        resp = await client.post("/api/v1/marketplace/listings/create", json={
            "id": "ls_test_paid_publish",
            "name": "Test Paid Listing",
            "price": 99.99,
            "category": "tool",
            "short_description": "A paid tool",
            "developer_name": "Test Vendor"
        }, headers=auth_headers)
        
        # Publish should fail with 403
        resp = await client.post("/api/v1/marketplace/listings/ls_test_paid_publish/submit", headers=auth_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "Stripe Connect onboarding must be completed" in data.get("detail", "")

@pytest.mark.asyncio
async def test_paid_marketplace_acquire_requires_payment(async_session, auth_headers):
    # 5. paid marketplace acquire without existing entitlement returns checkout/payment-required, not installed
    from httpx import AsyncClient
    from backend.apps.api.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First ensure the user has completed workspace onboarding
        await client.post("/api/v1/workspaces", json={"name": "Test Workspace", "industry": "technology"}, headers=auth_headers)
        
        # Create paid listing
        await client.post("/api/v1/marketplace/listings/create", json={
            "id": "ls_test_acquire_paid",
            "name": "Test Paid Acquire",
            "price": 49.99,
            "category": "tool",
            "short_description": "Paid tool",
            "developer_name": "Test Vendor"
        }, headers=auth_headers)
        
        # Attempt to install without payment
        resp = await client.post("/api/v1/marketplace/listings/ls_test_acquire_paid/install", json={}, headers=auth_headers)
        assert resp.status_code == 402
        data = resp.json()
        assert data.get("requires_payment") is True
        assert "checkout_url" in data
        assert data.get("price") == "49.99"
        assert data.get("currency") == "usd"

@pytest.mark.asyncio
async def test_stale_billing_string_not_in_current_payload(async_session, auth_headers):
    # 6. old /workspace/#/billing string is not present in /subscriptions/current payload
    from httpx import AsyncClient
    from backend.apps.api.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/subscriptions/current", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.text
        assert "/workspace#/billing" not in data
        assert "/control-plane-next/billing/" in data
