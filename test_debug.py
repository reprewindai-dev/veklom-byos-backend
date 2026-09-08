import json
from fastapi.testclient import TestClient
from backend.tests.test_auth_vlink_assertion import _app, _user, _Session, _key

user = _user("workspace-1")
raw = "byos_scopes"
key = _key(user, raw, ["vlink:id:machine-1", "vlink:conn:conn_1"])
session = _Session(user, [key])
client = TestClient(_app(user, session))

key.scopes = json.dumps(
    ["vlink:assertion", "vlink:id:machine-1", "vlink:conn:conn_1"]
)
key.workspace_id = "workspace-2"
response = client.post(
    "/api/v1/auth/vlink-assertion",
    headers={"X-API-Key": raw},
    json={"vlink_id": "machine-1"},
)
print("Response:", response.status_code, response.json())
