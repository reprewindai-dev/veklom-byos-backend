import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import backend.db.models  # Ensure all models are loaded to resolve relationships

import pytest
from fastapi.testclient import TestClient

from backend.apps.api.main import app
from backend.core.security.auth import get_current_user, create_access_token
from backend.core.database.database import Base, engine
from backend.db.models.benchmarks import BenchmarkAPI, StakingMarket, UserStake, SyntheticProbeLog
from backend.db.models.billing import WalletTransaction

@pytest.fixture
def mock_user():
    class MockUser:
        id = "test-user-id"
        workspace_id = "test-workspace-id"
        role = "OWNER"
        plan = "free"
        email = "user@veklom.local"
        status = "active"
        is_active = True
    return MockUser()

@pytest.mark.asyncio
async def test_benchmarks_staking_scenarios(mock_user):
    # Setup sqlite tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[
                BenchmarkAPI.__table__,
                StakingMarket.__table__,
                UserStake.__table__,
                SyntheticProbeLog.__table__,
                WalletTransaction.__table__
            ]
        ))

    client = TestClient(app)

    # Mock user dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user
    headers = {"Authorization": f"Bearer {create_access_token(data={'sub': mock_user.id})}"}

    # Verify initial leaderboard retrieval seeds default data
    resp = client.get("/api/v1/benchmarks/leaderboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0

    # Verify initial markets retrieval seeds default markets
    resp = client.get("/api/v1/benchmarks/staking/markets", headers=headers)
    assert resp.status_code == 200
    markets = resp.json()
    assert len(markets) > 0
    market_id = markets[0]["id"]

    # Since user has $0.00 wallet balance (no Topup transactions recorded), staking should FAIL with HTTP 400
    stake_payload = {
        "market_id": market_id,
        "outcome": "YES",
        "amount": 100.0
    }
    resp = client.post("/api/v1/benchmarks/staking/stake", json=stake_payload, headers=headers)
    assert resp.status_code == 400
    error_data = resp.json()
    assert "Insufficient funds" in error_data["detail"]

    # Let's add a topup WalletTransaction to user's workspace to simulate a real payment / operating reserve top-up
    from backend.core.database.database import async_session
    async with async_session() as session:
        topup_txn = WalletTransaction(
            user_id=mock_user.id,
            workspace_id=mock_user.workspace_id,
            amount=500.0,
            tx_type="topup",
            description="Workspace top-up"
        )
        session.add(topup_txn)
        await session.commit()

    # Now, placing the stake should SUCCEED
    resp = client.post("/api/v1/benchmarks/staking/stake", json=stake_payload, headers=headers)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["new_balance"] == 400.0

    # Verify that attempting to stake more than the remaining balance fails
    stake_excess_payload = {
        "market_id": market_id,
        "outcome": "NO",
        "amount": 500.0
    }
    resp = client.post("/api/v1/benchmarks/staking/stake", json=stake_excess_payload, headers=headers)
    assert resp.status_code == 400
    assert "Insufficient funds" in resp.json()["detail"]

    app.dependency_overrides.clear()
