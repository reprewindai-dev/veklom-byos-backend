import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock
from backend.apps.api.routers.discovery import get_discovery_leaderboard
from sqlalchemy.engine.row import Row

@pytest.mark.asyncio
async def test_empty_data():
    db = AsyncMock()
    # Mock return value of db.execute(...).all()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    db.execute.return_value = mock_result

    result = await get_discovery_leaderboard(db=db)
    assert result == {"leaderboard": []}

@pytest.mark.asyncio
async def test_missing_tenant_id():
    db = AsyncMock()
    mock_result = MagicMock()

    class MockRow:
        def __init__(self, tenant_id, pgl_identity, state):
            self.tenant_id = tenant_id
            self.pgl_identity = pgl_identity
            self.state = state

    mock_result.all.return_value = [
        MockRow(None, {}, "success"),
        MockRow("", {}, "success")
    ]
    db.execute.return_value = mock_result

    result = await get_discovery_leaderboard(db=db)
    assert result == {"leaderboard": []}

@pytest.mark.asyncio
async def test_dict_non_dict_pgl_identity():
    db = AsyncMock()
    mock_result = MagicMock()

    class MockRow:
        def __init__(self, tenant_id, pgl_identity, state):
            self.tenant_id = tenant_id
            self.pgl_identity = pgl_identity
            self.state = state

    mock_result.all.return_value = [
        MockRow("tenant1", {"agent_id": "agent_alpha"}, "success"),
        MockRow("tenant2", "not_a_dict", "success"),
        MockRow("tenant3", None, "success")
    ]
    db.execute.return_value = mock_result

    result = await get_discovery_leaderboard(db=db)

    leaderboard = result["leaderboard"]
    assert len(leaderboard) == 3

    # Sort by address for easy checking since scores are equal
    leaderboard.sort(key=lambda x: x["address"])

    assert leaderboard[0]["agent"] == "agent_alpha"
    assert leaderboard[1]["agent"] == "Unknown Agent"
    assert leaderboard[2]["agent"] == "Unknown Agent"

@pytest.mark.asyncio
async def test_success_failure_scoring():
    db = AsyncMock()
    mock_result = MagicMock()

    class MockRow:
        def __init__(self, tenant_id, pgl_identity, state):
            self.tenant_id = tenant_id
            self.pgl_identity = pgl_identity
            self.state = state

    mock_result.all.return_value = [
        MockRow("tenant_win", {}, "success"),
        MockRow("tenant_win", {}, "completed"),
        MockRow("tenant_lose", {}, "error"),
        MockRow("tenant_lose", {}, "failed"),
        MockRow("tenant_lose", {}, "law0_violation"),
        MockRow("tenant_neutral", {}, "pending"),
    ]
    db.execute.return_value = mock_result

    result = await get_discovery_leaderboard(db=db)

    leaderboard = result["leaderboard"]
    # Sorted by score descending

    assert leaderboard[0]["address"] == "tenant_win"
    assert leaderboard[0]["trustScore"] == 500 + 10 + 10 # 520
    assert leaderboard[0]["completedMissions"] == 2

    assert leaderboard[1]["address"] == "tenant_neutral"
    assert leaderboard[1]["trustScore"] == 500 # 500
    assert leaderboard[1]["completedMissions"] == 1

    assert leaderboard[2]["address"] == "tenant_lose"
    assert leaderboard[2]["trustScore"] == 500 - 15 - 15 - 15 # 455
    assert leaderboard[2]["completedMissions"] == 3

@pytest.mark.asyncio
async def test_ordering_limit_behavior():
    db = AsyncMock()
    mock_result = MagicMock()

    class MockRow:
        def __init__(self, tenant_id, pgl_identity, state):
            self.tenant_id = tenant_id
            self.pgl_identity = pgl_identity
            self.state = state

    # Generate 5 tenants with different scores
    rows = []
    for i in range(5):
        tenant_id = f"tenant_{i}"
        # Adding 'success' rows to give them different scores based on i
        for _ in range(i):
            rows.append(MockRow(tenant_id, {}, "success"))

    mock_result.all.return_value = rows
    db.execute.return_value = mock_result

    # Check limit = 3
    result = await get_discovery_leaderboard(db=db, limit=3)
    leaderboard = result["leaderboard"]

    assert len(leaderboard) == 3
    # Top should be tenant_4 (4 wins), then tenant_3, then tenant_2
    assert leaderboard[0]["address"] == "tenant_4"
    assert leaderboard[1]["address"] == "tenant_3"
    assert leaderboard[2]["address"] == "tenant_2"

@pytest.mark.asyncio
async def test_sqlalchemy_row_access():
    db = AsyncMock()
    mock_result = MagicMock()

    # SQLAlchemy Rows can act somewhat like namedtuples / objects with getattr
    class MockSQLRow:
        def __init__(self, t):
            self.tenant_id = t[0]
            self.pgl_identity = t[1]
            self.state = t[2]

        def __getattr__(self, name):
            if name == "tenant_id": return self.tenant_id
            if name == "pgl_identity": return self.pgl_identity
            if name == "state": return self.state
            raise AttributeError

    mock_result.all.return_value = [
        MockSQLRow(("row_tenant", {"agent_id": "row_agent"}, "success"))
    ]
    db.execute.return_value = mock_result

    result = await get_discovery_leaderboard(db=db)

    assert len(result["leaderboard"]) == 1
    assert result["leaderboard"][0]["address"] == "row_tenant"
    assert result["leaderboard"][0]["agent"] == "row_agent"
    assert result["leaderboard"][0]["trustScore"] == 510
