import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import json
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, ARRAY as PG_ARRAY
from sqlalchemy.types import ARRAY as StandardARRAY

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "TEXT"

@compiles(PG_ARRAY, "sqlite")
@compiles(StandardARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "TEXT"

try:
    from pgvector.sqlalchemy import VECTOR
    @compiles(VECTOR, "sqlite")
    def compile_vector_sqlite(element, compiler, **kw):
        return "TEXT"
except ImportError:
    pass

from fastapi.testclient import TestClient
from backend.apps.api.main import app
from backend.db.models.agent import AgentIdentity
from backend.db.models.authority import AuthorityBundle
from backend.core.database.database import get_db

@pytest.fixture(scope="module", autouse=True)
async def setup_test_db():
    from backend.core.database.database import engine, Base
    import backend.db.models.user
    import backend.db.models.workspace
    import backend.db.models.ai
    import backend.db.models.agent
    import backend.db.models.billing
    import backend.db.models.security
    import backend.db.models.ledger
    import backend.db.models.decision_frame
    import backend.db.models.authority
    import backend.db.models.vnp
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

client = TestClient(app)

@pytest.mark.asyncio
async def test_phase_1_signature_failure():
    """Test 1: Tampered Payload Signature Rejection (Phase 1)"""
    payload = {
        "agent_id": "agent-core-01",
        "pgl_id": "badsig", # Explicitly trigger failure
        "target_protocol": "syscall_execute",
        "action": "fs.write",
        "payload": {
            "path": "/etc/hosts",
            "content": "127.0.0.1 illegal-routing.net"
        }
    }
    response = client.post("/api/v1/capi/execute", json=payload)
    assert response.status_code == 200
    
    # Parse SSE stream
    events = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            if line_str.startswith("data: "):
                event_data = json.loads(line_str[6:])
                events.append(event_data)
                
    error_event = next((e for e in events if e.get("type") == "error"), None)
    assert error_event is not None, f"Expected error event in stream, got {events}"
    detail = error_event["detail"]
    assert detail["error"] == "cAPI_VETO_ENGAGED"
    assert detail["phase"] == 1
    assert detail["reason"] == "CRYPTOGRAPHIC_SIGNATURE_INVALID"


@pytest.mark.asyncio
async def test_phase_2_implicit_deny():
    """Test 2: Implicit Deny Enforcement (Phase 2)"""
    # We use a valid-looking pgl_id but a target protocol/action that won't have an ALLOW rule
    payload = {
        "agent_id": "agent-core-01",
        "pgl_id": "valid_mock_sig",
        "target_protocol": "unsupported_protocol",
        "action": "some_unsupported_action",
        "payload": {}
    }
    response = client.post("/api/v1/capi/execute", json=payload)
    assert response.status_code == 200
    
    # Parse SSE stream
    events = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            if line_str.startswith("data: "):
                event_data = json.loads(line_str[6:])
                events.append(event_data)
                
    error_event = next((e for e in events if e.get("type") == "error"), None)
    assert error_event is not None, f"Expected error event in stream, got {events}"
    detail = error_event["detail"]
    assert detail["phase"] == 2
    assert "NO_EXPLICIT_ALLOW_RULE" in detail["reason"] or "POLICIES_CONSTRUCT_DENY" in detail["reason"]


@pytest.mark.asyncio
async def test_terminal_governance_wiring():
    """Test that the /terminal/run endpoint is now governed."""
    from backend.core.security.auth import create_access_token
    token = create_access_token({"sub": "test_user_id"})
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "intent": "rm -rf /",
        "agent_id": "terminal-test-agent",
        "pgl_id": "terminal-test-pgl"
    }
    response = client.post("/api/v1/terminal/run", json=payload, headers=headers)
    assert response.status_code == 200
    
    # Parse SSE stream
    events = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            if line_str.startswith("data: "):
                event_data = json.loads(line_str[6:])
                events.append(event_data)
                
    error_event = next((e for e in events if e.get("type") == "error"), None)
    assert error_event is not None, f"Expected error event in stream, got {events}"
    detail = error_event["detail"]
    assert detail["error"] == "cAPI_VETO_ENGAGED"
    assert detail["phase"] == 2
    assert "SYSTEM_POLICY_VETO" in detail["reason"]


def test_recursive_schema_depth_moat():
    """Test that verify_schema_depth successfully identifies and blocks deeply nested JSON payloads."""
    from backend.core.security.schema_moat import verify_schema_depth
    
    # 1. Nesting level of 3 (Safe)
    safe_payload = {"a": {"b": {"c": 1}}}
    verify_schema_depth(safe_payload, max_depth=6) # Should not raise
    
    # 2. Nesting level of 8 (Malicious/Deep)
    malicious_payload = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": 1}}}}}}}}
    with pytest.raises(ValueError) as exc_info:
        verify_schema_depth(malicious_payload, max_depth=6)
    assert "Schema depth limit exceeded" in str(exc_info.value)


def test_in_process_error_sanitization():
    """Test that the InProcessErrorSanitizer successfully strips sensitive system details and paths."""
    from backend.core.security.sanitizer import InProcessErrorSanitizer
    sanitizer = InProcessErrorSanitizer()
    
    # 1. Test database connection URL stripping
    raw_db_msg = "Connection failed at postgresql://veklom_admin:SuperSecretPassword123@db.veklom.internal:5432/veklom_prod"
    sanitized_db_msg = sanitizer.sanitize_message(raw_db_msg)
    assert "SuperSecretPassword123" not in sanitized_db_msg
    assert "[REDACTED_SECURITY_CREDENTIALS]" in sanitized_db_msg
    
    # 2. Test system paths (antho, data/coolify) stripping
    raw_path_msg = "Error opening file: C:\\Users\\antho\\documents\\sensitive_key.pem on VPS path /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env"
    sanitized_path_msg = sanitizer.sanitize_message(raw_path_msg)
    assert "antho" not in sanitized_path_msg
    assert "coolify" not in sanitized_path_msg
    assert "[SYSTEM_ENVIRONMENT_BOUND_PATH]" in sanitized_path_msg
    assert "[SYSTEM_ENVIRONMENT_CONTAINMENT_PATH]" in sanitized_path_msg
    
    # 3. Test exception translation to error signatures
    try:
        raise ValueError("Could not query DB URL postgresql://postgres:pw123@localhost/db on path /data/coolify/apps")
    except Exception as e:
        sanitized_payload, diag_log = sanitizer.sanitize_exception(e)
        
    assert sanitized_payload["error"] == "cAPI_CONTAINED_EXECUTION_FAILURE"
    assert "ERR-SHA256-" in sanitized_payload["signature"]
    assert "pw123" not in sanitized_payload["message"]
    assert "pw123" not in diag_log
    assert "coolify" not in sanitized_payload["message"]
    assert "coolify" not in diag_log

