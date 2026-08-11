"""Regression tests for request-scoped JWT and RLS tenant binding."""

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text

from backend.core.security import auth


class _ScalarResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _TrackingSession:
    def __init__(self, *, user=None, active_session=None):
        self.user = user
        self.active_session = active_session
        self.calls = []
        self.workspace_context = None
        self.expunge_calls = []
        self.commit_calls = 0

    async def execute(self, statement, params=None):
        sql = str(statement)
        bound_params = params or {}
        self.calls.append((sql, bound_params))

        normalized = " ".join(sql.lower().split())
        if "set_config('app.workspace_id'" in normalized:
            self.workspace_context = bound_params.get("workspace_id", bound_params.get("tenant_id"))
            return _ScalarResult()
        if normalized == "reset app.workspace_id":
            self.workspace_context = None
            return _ScalarResult()
        if " from users " in f" {normalized} ":
            return _ScalarResult(self.user)
        if " from sessions " in f" {normalized} ":
            return _ScalarResult(self.active_session)
        return _ScalarResult()

    async def commit(self):
        self.commit_calls += 1
        # set_config(..., true) is transaction-local in PostgreSQL.
        self.workspace_context = None

    def expunge(self, value):
        self.expunge_calls.append(value)


def _request(path="/api/v1/workspace"):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def _credentials(token="test-token"):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _user(workspace_id, **overrides):
    values = {
        "id": "user-1",
        "workspace_id": workspace_id,
        "status": "active",
        "is_active": True,
        "last_activity": datetime.utcnow(),
    }
    values.update(overrides)
    return SimpleNamespace(
        **values,
    )


def _assert_no_rls_bypass(db):
    assert all("app.bypass_rls" not in sql.lower() for sql, _ in db.calls)


@pytest.mark.asyncio
async def test_missing_workspace_jwt_fails_before_any_database_context(monkeypatch):
    db = _TrackingSession()
    monkeypatch.setattr(auth, "verify_token", lambda _token: {"sub": "user-1"})

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(_request(), _credentials(), db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token missing workspace_id claim. Re-authenticate to obtain a scoped token."
    assert db.calls == []
    assert db.workspace_context is None
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_binds_only_the_claimed_account_tenant(monkeypatch):
    workspace_id = "workspace-a"
    user = _user(workspace_id)
    db = _TrackingSession(user=user, active_session=object())
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": user.id, "workspace_id": workspace_id},
    )

    authenticated_user = await auth.get_current_user(_request(), _credentials(), db)

    tenant_bindings = [
        params["workspace_id"]
        for sql, params in db.calls
        if "set_config('app.workspace_id'" in sql.lower()
    ]
    assert authenticated_user is user
    assert tenant_bindings == [workspace_id, workspace_id]
    assert "reset app.workspace_id" in [" ".join(sql.lower().split()) for sql, _ in db.calls]
    assert db.workspace_context == workspace_id
    assert db.expunge_calls == [user]
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_rebinds_authoritative_tenant_after_activity_commit(monkeypatch):
    workspace_id = "workspace-a"
    user = _user(workspace_id, last_activity=None)
    db = _TrackingSession(user=user, active_session=object())
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": user.id, "workspace_id": workspace_id},
    )

    authenticated_user = await auth.get_current_user(_request(), _credentials(), db)

    assert authenticated_user is user
    assert db.commit_calls == 1
    assert db.workspace_context == workspace_id
    assert db.expunge_calls == [user]
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_rejects_account_tenant_mismatch(monkeypatch):
    claimed_workspace = "workspace-claimed"
    account_workspace = "workspace-account"
    user = _user(account_workspace)
    db = _TrackingSession(user=user, active_session=object())
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": user.id, "workspace_id": claimed_workspace},
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(_request(), _credentials(), db)

    tenant_bindings = [
        params["workspace_id"]
        for sql, params in db.calls
        if "set_config('app.workspace_id'" in sql.lower()
    ]
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Workspace claim does not match account"
    assert tenant_bindings == [claimed_workspace]
    assert account_workspace not in tenant_bindings
    assert db.workspace_context is None
    assert db.expunge_calls == []
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_clears_tenant_when_user_is_not_found(monkeypatch):
    claimed_workspace = "workspace-claimed"
    db = _TrackingSession(user=None, active_session=object())
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": "missing-user", "workspace_id": claimed_workspace},
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(_request(), _credentials(), db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User not found"
    assert db.workspace_context is None
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_clears_tenant_when_session_is_inactive(monkeypatch):
    claimed_workspace = "workspace-claimed"
    user = _user(claimed_workspace)
    db = _TrackingSession(user=user, active_session=None)
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": user.id, "workspace_id": claimed_workspace},
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(_request(), _credentials(), db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Session revoked or expired"
    assert db.workspace_context is None
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_clears_tenant_when_account_is_inactive(monkeypatch):
    workspace_id = "workspace-a"
    user = _user(workspace_id, status="suspended", is_active=False)
    db = _TrackingSession(user=user, active_session=object())
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": user.id, "workspace_id": workspace_id},
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(_request(), _credentials(), db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Account inactive"
    assert db.workspace_context is None
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_clears_tenant_when_account_has_no_workspace(monkeypatch):
    claimed_workspace = "workspace-claimed"
    user = _user(None)
    db = _TrackingSession(user=user, active_session=object())
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": user.id, "workspace_id": claimed_workspace},
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(_request(), _credentials(), db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "User account is missing a workspace assignment."
    assert db.workspace_context is None
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_workspace_jwt_clears_tenant_when_verification_is_required(monkeypatch):
    workspace_id = "workspace-a"
    user = _user(workspace_id, status="pending_verification")
    db = _TrackingSession(user=user, active_session=object())
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: {"sub": user.id, "workspace_id": workspace_id},
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(_request("/api/v1/protected"), _credentials(), db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "email_verification_required"
    assert db.workspace_context is None
    _assert_no_rls_bypass(db)


@pytest.mark.asyncio
async def test_rls_dependency_clears_tenant_context_after_downstream_query():
    workspace_id = "workspace-a"
    db = _TrackingSession()
    dependency = auth.get_rls_db(user=_user(workspace_id), db=db)

    downstream_db = await anext(dependency)
    assert downstream_db is db
    assert db.workspace_context == workspace_id

    await downstream_db.execute(text("SELECT 1"))
    await dependency.aclose()

    assert db.workspace_context is None
    assert "reset app.workspace_id" in [" ".join(sql.lower().split()) for sql, _ in db.calls]
    _assert_no_rls_bypass(db)
