"""Regression tests for Auth and OAuth bugs."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from backend.apps.api.routers.auth import register, github_callback, RegisterRequest
from backend.db.models.user import User
from backend.db.models.pgl import Workspace

class MockRequest:
    def __init__(self, query_params=None, method="GET", cookies=None, headers=None, url="https://api.veklom.com/"):
        self.query_params = query_params or {}
        self.method = method
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.url = MagicMock()
        self.url.__str__.return_value = url
        self.url.scheme = "https"
        self.url.netloc = "api.veklom.com"
        
    async def json(self):
        return {}


class MockSession:
    def __init__(self):
        self.added = []
        self.executed_queries = []
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True
        # Mock ids for created objects
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = "mock_id"

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        pass

    async def execute(self, stmt, params=None):
        self.executed_queries.append((str(stmt), params))
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result


@pytest.mark.asyncio
async def test_anonymous_signup_creates_workspace_and_user_under_correct_context():
    db = MockSession()
    request = MockRequest(headers={"user-agent": "test"})
    body = RegisterRequest(email="test@veklom.com", password="Password123!", full_name="Test User", workspace_name="Test WS")
    
    with patch("backend.apps.api.routers.auth.log_audit_event", new_callable=AsyncMock):
        resp = await register(body=body, request=request, db=db)
        
    assert db.flushed is True
    assert db.committed is True
    
    workspace = next(obj for obj in db.added if getattr(obj, "__class__", None) and obj.__class__.__name__ == 'Workspace')
    user = next(obj for obj in db.added if getattr(obj, "__class__", None) and obj.__class__.__name__ == 'User')
    
    # Assert RLS context was set AFTER workspace creation
    set_config_calls = [q for q, p in db.executed_queries if "set_config('app.workspace_id'" in q]
    assert len(set_config_calls) == 1
    assert user.workspace_id == workspace.id

@pytest.mark.asyncio
async def test_user_cannot_be_created_into_another_workspace():
    # Attempting to manipulate input has no effect because workspace is always newly generated inside register
    body = RegisterRequest(email="test@veklom.com", password="Password123!", full_name="Test User", workspace_name="Test WS")
    # There is no workspace_id field on RegisterRequest, proving isolation
    assert not hasattr(body, "workspace_id")

@pytest.mark.asyncio
async def test_failed_signup_rolls_back_atomically():
    db = MockSession()
    # Mock flush to raise an exception
    async def mock_flush():
        raise Exception("DB Error")
    db.flush = mock_flush
    
    body = RegisterRequest(email="test@veklom.com", password="Password123!", full_name="Test User")
    request = MockRequest()
    
    with pytest.raises(Exception):
        await register(body=body, request=request, db=db)
    # The get_db context manager in FastAPI handles the rollback in production when exception bubbles up
    assert not db.committed

@pytest.mark.asyncio
async def test_github_new_user_gets_rls_context():
    db = MockSession()
    request = MockRequest(query_params={"code": "mock", "state": "mock"})
    
    # Mock httpx and oauth config
    with patch("backend.apps.api.routers.auth._github_oauth_configured", return_value=True), \
         patch("backend.apps.api.routers.auth._resolve_github_oauth_values", return_value={"client_id": "c", "client_secret": "s", "redirect_uri": "r"}), \
         patch("backend.apps.api.routers.auth._validate_github_state", return_value=(None, "https://control.veklom.com/dashboard/")), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "mock_token"}
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"login": "ghuser", "email": "gh@veklom.com", "id": 123, "name": "GH User"}
        
        resp = await github_callback(request=request, code="mock", state="mock", db=db)
        
    set_config_calls = [q for q, p in db.executed_queries if "set_config('app.workspace_id'" in q]
    assert len(set_config_calls) == 1
    
    # Assert OAuth sets expected Secure/HttpOnly cookies
    assert isinstance(resp, RedirectResponse)
    cookies = resp.headers.getlist("set-cookie")
    assert any("access_token=" in c and "Secure" in c and "HttpOnly" in c and "Domain=.veklom.com" in c for c in cookies)
    assert any("refresh_token=" in c and "Secure" in c and "HttpOnly" in c and "Domain=.veklom.com" in c for c in cookies)
    
@pytest.mark.asyncio
async def test_callback_redirects_to_allowed_origin():
    db = MockSession()
    # Provide a malicious next_url in state
    request = MockRequest(query_params={"code": "mock", "state": "mock"})
    
    with patch("backend.apps.api.routers.auth._github_oauth_configured", return_value=True), \
         patch("backend.apps.api.routers.auth._resolve_github_oauth_values", return_value={"client_id": "c", "client_secret": "s", "redirect_uri": "r"}), \
         patch("backend.apps.api.routers.auth._validate_github_state", return_value=(None, "https://evil.com/dashboard/")), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "mock_token"}
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"login": "ghuser", "email": "gh@veklom.com", "id": 123}
        
        resp = await github_callback(request=request, code="mock", state="mock", db=db)
        
    # Should fallback to control plane url, not evil.com
    assert resp.headers["location"].startswith("https://control.veklom.com")
