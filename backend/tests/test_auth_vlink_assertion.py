import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.apps.api.routers import auth
from backend.core.database.database import get_db
from backend.db.models.user import APIKey


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None


class _Session:
    def __init__(self, user, keys=None, bindings=None):
        self.user = user
        self.keys = list(keys or [])
        self.bindings = list(bindings) if bindings is not None else None

    async def execute(self, statement):
        from backend.db.models.vlink_binding import VLinkBinding
        import json
        statement_text = str(statement)
        if "vlink_bindings" in statement_text:
            if self.bindings is not None:
                return _ScalarResult(self.bindings)
            bindings = []
            for k in self.keys:
                scopes = json.loads(k.scopes)
                vlink_id = None
                conn_ref = None
                for s in scopes:
                    if s.startswith("vlink:id:"):
                        vlink_id = s.split(":")[-1]
                    elif s.startswith("vlink:conn:"):
                        conn_ref = s.split(":")[-1]
                if vlink_id:
                    bindings.append(VLinkBinding(
                        id=f"binding-{k.id}",
                        vlink_id=vlink_id,
                        api_key_id=k.id,
                        workspace_id=k.workspace_id,
                        connection_ref=conn_ref,
                        is_active=k.is_active
                    ))
            return _ScalarResult(bindings)
        if "api_keys" in statement_text:
            return _ScalarResult(self.keys)
        if "users" in statement_text:
            return _ScalarResult([self.user] if self.user is not None else [])
        raise AssertionError(f"unexpected query: {statement_text}")

    def add(self, obj):
        if type(obj).__name__ == "APIKey":
            if obj.id is None:
                obj.id = f"key-{len(self.keys) + 1}"
            if obj.is_active is None:
                obj.is_active = True
            self.keys.append(obj)
        elif type(obj).__name__ == "VLinkBinding":
            if self.bindings is None:
                self.bindings = []
            if obj.id is None:
                obj.id = f"binding-{len(self.bindings) + 1}"
            if obj.is_active is None:
                obj.is_active = True
            self.bindings.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        return None

def _user(workspace_id="workspace-1", status="ACTIVE", is_active=True):
    return SimpleNamespace(
        id="user-1",
        workspace_id=workspace_id,
        status=status,
        is_active=is_active,
        role="OWNER",
    )


def _app(user, session):
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")

    async def override_user():
        return user

    async def override_db():
        yield session

    app.dependency_overrides[auth.get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    return app


def _key(user, raw, scopes, **kwargs):
    return APIKey(
        id=kwargs.get("id", "key-1"),
        user_id=user.id,
        workspace_id=kwargs.get("workspace_id", user.workspace_id),
        name=kwargs.get("name", "vlink:machine-1"),
        key_hash=auth.get_password_hash(raw),
        key_prefix=raw[:10],
        scopes=json.dumps(scopes),
        is_active=kwargs.get("is_active", True),
        expires_at=kwargs.get("expires_at"),
    )


@pytest.fixture
def signing_key(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setenv("CAPPO_ASSERTION_SIGNING_KEY", private_key.private_bytes_raw().hex())
    monkeypatch.setenv("CAPPO_ASSERTION_ISSUER", "https://issuer.test")
    monkeypatch.setenv("CAPPO_ASSERTION_AUDIENCE", "https://cappo.test")
    return private_key


def test_provision_then_exchange_returns_workspace_bound_assertion(signing_key):
    user = _user("workspace-7")
    session = _Session(user)
    client = TestClient(_app(user, session))

    provisioned = client.post(
        "/api/v1/auth/vlink-credentials",
        json={"vlink_id": "machine-1"},
    )
    assert provisioned.status_code == 200
    provision_body = provisioned.json()
    assert provision_body["workspace_id"] == "workspace-7"
    assert provision_body["scopes"] == [
        "vlink:assertion",
        "vlink:id:machine-1",
        f"vlink:conn:{provision_body['connection_ref']}",
    ]

    exchanged = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": provision_body["key"]},
        json={"vlink_id": "machine-1"},
    )
    assert exchanged.status_code == 200
    body = exchanged.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 120
    assert body["workspace_id"] == "workspace-7"
    assert body["connection_ref"] == provision_body["connection_ref"]

    claims = jwt.decode(
        body["access_token"],
        signing_key.public_key(),
        algorithms=["EdDSA"],
        issuer="https://issuer.test",
        audience="https://cappo.test",
    )
    assert claims["iss"] == "https://issuer.test"
    assert claims["aud"] == "https://cappo.test"
    assert claims["sub"] == "vlink:machine-1"
    assert claims["workspace_id"] == "workspace-7"
    assert claims["connection_ref"] == provision_body["connection_ref"]
    assert claims["role"] == "MACHINE"
    assert claims["exp"] - claims["iat"] == 120
    assert claims["jti"]


def test_provisioning_requires_workspace_and_rejects_extra_fields():
    user = _user(None)
    client = TestClient(_app(user, _Session(user)))
    response = client.post(
        "/api/v1/auth/vlink-credentials",
        json={"vlink_id": "machine-1"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "WORKSPACE_CONTEXT_MISSING"}}

    user = _user()
    client = TestClient(_app(user, _Session(user)))
    response = client.post(
        "/api/v1/auth/vlink-credentials",
        json={"vlink_id": "machine-1", "workspace_id": "attacker-workspace"},
    )
    assert response.status_code == 422


def test_vlink_binding_mismatch_is_denied(signing_key):
    user = _user()
    raw = "byos_machine-a"
    key = _key(
        user,
        raw,
        ["vlink:assertion", "vlink:id:machine-a", "vlink:conn:conn_a"],
    )
    client = TestClient(_app(user, _Session(user, [key])))

    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-b"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "VLINK_BINDING_MISMATCH"}}


@pytest.mark.parametrize(
    ("key_kwargs", "expected"),
    [
        ({"is_active": False}, "MACHINE_CREDENTIAL_REVOKED"),
        (
            {"expires_at": datetime.utcnow() - timedelta(seconds=1)},
            "MACHINE_CREDENTIAL_EXPIRED",
        ),
    ],
)
def test_machine_credential_lifecycle_gates(signing_key, key_kwargs, expected):
    user = _user()
    raw = "byos_lifecycle"
    key = _key(
        user,
        raw,
        ["vlink:assertion", "vlink:id:machine-1", "vlink:conn:conn_1"],
        **key_kwargs,
    )
    client = TestClient(_app(user, _Session(user, [key])))

    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": {"error": expected}}


@pytest.mark.parametrize(
    ("user_kwargs", "expected"),
    [
        ({"status": "SUSPENDED"}, "OWNER_INACTIVE"),
        ({"status": "ACTIVE", "is_active": False}, "OWNER_INACTIVE"),
    ],
)
def test_inactive_owner_is_denied(signing_key, user_kwargs, expected):
    user = _user(**user_kwargs)
    raw = "byos_owner"
    key = _key(
        user,
        raw,
        ["vlink:assertion", "vlink:id:machine-1", "vlink:conn:conn_1"],
    )
    client = TestClient(_app(user, _Session(user, [key])))

    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": {"error": expected}}


def test_scope_and_workspace_gates(signing_key):
    user = _user("workspace-1")
    raw = "byos_scopes"
    key = _key(user, raw, ["vlink:id:machine-1", "vlink:conn:conn_1"])
    client = TestClient(_app(user, _Session(user, [key])))

    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "SCOPE_NOT_GRANTED"}}

    key.scopes = json.dumps(
        ["vlink:assertion", "vlink:id:machine-1", "vlink:conn:conn_1"]
    )
    key.workspace_id = "workspace-2"
    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "WORKSPACE_MISMATCH"}}


def test_missing_binding_and_connection_reference_are_distinct(signing_key):
    user = _user()
    raw = "byos_missing"
    key = _key(user, raw, ["vlink:assertion", "vlink:id:other"])
    client = TestClient(_app(user, _Session(user, [key])))

    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "VLINK_BINDING_MISMATCH"}}

    key.scopes = json.dumps(["vlink:assertion", "vlink:id:machine-1"])
    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "CONNECTION_REFERENCE_MISSING"}}


@pytest.mark.parametrize("header", [None, "", "garbage", "sk_machine-1"])
def test_invalid_machine_credentials_are_unauthorized(signing_key, header):
    user = _user()
    raw = "byos_valid"
    key = _key(
        user,
        raw,
        ["vlink:assertion", "vlink:id:machine-1", "vlink:conn:conn_1"],
    )
    client = TestClient(_app(user, _Session(user, [key])))
    headers = {} if header is None else {"X-API-Key": header}

    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers=headers,
        json={"vlink_id": "machine-1"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": {"error": "INVALID_MACHINE_CREDENTIAL"}}


def test_request_cannot_supply_workspace_and_header_is_ignored(signing_key):
    user = _user("workspace-bound")
    raw = "byos_bound"
    key = _key(
        user,
        raw,
        ["vlink:assertion", "vlink:id:machine-1", "vlink:conn:conn_1"],
    )
    client = TestClient(_app(user, _Session(user, [key])))

    invalid = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw, "X-Workspace-ID": "attacker-workspace"},
        json={"vlink_id": "machine-1", "workspace_id": "attacker-workspace"},
    )
    assert invalid.status_code == 422

    response = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw, "X-Workspace-ID": "attacker-workspace"},
        json={"vlink_id": "machine-1"},
    )
    assert response.status_code == 200
    assert response.json()["workspace_id"] == "workspace-bound"


def test_reprovisioning_reuses_connection_reference(signing_key):
    user = _user()
    session = _Session(user)
    client = TestClient(_app(user, session))

    first = client.post(
        "/api/v1/auth/vlink-credentials",
        json={"vlink_id": "machine-1"},
    ).json()
    second = client.post(
        "/api/v1/auth/vlink-credentials",
        json={"vlink_id": "machine-1"},
    ).json()

    assert first["connection_ref"] == second["connection_ref"]
    assert first["key_id"] != second["key_id"]


def test_successive_exchanges_change_jti_but_preserve_binding(signing_key):
    user = _user()
    raw = "byos_repeat"
    key = _key(
        user,
        raw,
        ["vlink:assertion", "vlink:id:machine-1", "vlink:conn:conn_1"],
    )
    client = TestClient(_app(user, _Session(user, [key])))

    first = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    ).json()
    second = client.post(
        "/api/v1/auth/vlink-assertion",
        headers={"X-API-Key": raw},
        json={"vlink_id": "machine-1"},
    ).json()
    first_claims = jwt.decode(first["access_token"], options={"verify_signature": False})
    second_claims = jwt.decode(second["access_token"], options={"verify_signature": False})

    assert first["workspace_id"] == second["workspace_id"] == "workspace-1"
    assert first["connection_ref"] == second["connection_ref"] == "conn_1"
    assert first_claims["jti"] != second_claims["jti"]
