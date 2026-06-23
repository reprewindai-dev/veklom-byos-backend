import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Must mock redis_client before importing routers or memory
import backend.core.database.redis_client as redis_client_mod
mock_redis = AsyncMock()
redis_client_mod.redis_client = mock_redis

from backend.apps.api.main import app
from backend.core.memory.conversation import ConversationMemory
import json

client = TestClient(app)

@pytest.fixture
def mock_auth():
    # Mock authentication to return a test user with a workspace
    with patch("backend.core.security.auth.get_current_user") as mock_user:
        user = AsyncMock()
        user.workspace_id = "test_workspace"
        mock_user.return_value = user
        yield mock_user

@pytest.mark.asyncio
async def test_conversation_memory_history():
    """Test retrieving history from ConversationMemory"""
    mock_redis.lrange.return_value = [
        json.dumps({"role": "user", "content": "Hello"}).encode(),
        json.dumps({"role": "assistant", "content": "Hi there"}).encode()
    ]
    
    history = await ConversationMemory.get_history("workspace_1", "conv_1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
    
    mock_redis.lrange.assert_called_with("conv:workspace_1:conv_1", 0, -1)

@pytest.mark.asyncio
async def test_conversation_memory_add():
    """Test adding messages and triggering TTL / Trim logic"""
    mock_redis.llen.return_value = 25  # Force a trim
    
    messages = [{"role": "user", "content": "Test"}]
    await ConversationMemory.add_messages("workspace_1", "conv_1", messages)
    
    # Verify rpush was called
    mock_redis.rpush.assert_called()
    
    # Verify trim was called because length (25) > max_msgs (20)
    mock_redis.ltrim.assert_called_with("conv:workspace_1:conv_1", 5, -1)
    
    # Verify expire was called to reset TTL
    mock_redis.expire.assert_called()

@pytest.mark.asyncio
async def test_memory_api_get_stats(mock_auth):
    """Test the new dedicated API endpoint for retrieving stats"""
    mock_redis.llen.return_value = 15
    mock_redis.ttl.return_value = 3600
    
    # Make request, bypassing actual auth with dependency overrides
    from backend.core.security.auth import get_current_user
    async def mock_user():
        return type("User", (), {"workspace_id": "test_workspace"})()
    app.dependency_overrides[get_current_user] = mock_user
    
    response = client.get("/api/v1/memory/conversation/conv_test/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert data["conversation_id"] == "conv_test"
    assert data["current_messages"] == 15
    assert data["remaining_ttl_seconds"] == 3600
    assert data["status"] == "active"
    
    app.dependency_overrides.clear()
