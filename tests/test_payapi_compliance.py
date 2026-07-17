"""Automated compliance validation test for PayAPI 67-endpoint catalog.

Fires mock requests at every single path to assert routing correctness.
"""

import pytest
from fastapi.testclient import TestClient
from backend.apps.api.main import app
from backend.core.security.auth import get_current_user

# Mock user for bypassing Auth
class MockUser:
    def __init__(self):
        self.id = "mock_user_id"
        self.workspace_id = "ws_test_workspace"
        self.email = "test@veklom.com"
        self.status = "active"
        self.is_superuser = True
        self.is_active = True

async def override_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)

ENDPOINTS = [
    # Category A: GPC Pipeline
    ("POST", "/api/v1/gpc/intent-to-plan", {"intent": "compile shortform workflow"}),
    ("POST", "/api/v1/gpc/plans", {"name": "Test Plan", "nodes": [], "edges": []}),
    ("GET", "/api/v1/gpc/plans", None),
    ("POST", "/api/v1/gpc/runs", {"plan_id": "plan_123"}),
    ("GET", "/api/v1/gpc/runs", None),
    ("GET", "/api/v1/gpc/events", None),
    ("GET", "/api/v1/gpc/bootstrap", None),

    # Category B: cAPI
    ("POST", "/api/v1/capi/execute", {"tool": "mcp_git_commit"}),
    ("GET", "/api/v1/capi/quarantine", None),
    ("POST", "/api/v1/capi/quarantine/q_123/resolve", {"resolution": "approved"}),
    ("GET", "/api/v1/authority/runs", None),
    ("GET", "/api/v1/authority/runs/run_123/decisions", None),
    ("GET", "/api/v1/authority/bundles", None),
    ("GET", "/api/v1/authority/context", None),
    ("POST", "/api/v1/autonomous", {"intent": "evaluate network routing"}),

    # Category C: PGL Identity & Workforce
    ("POST", "/api/v1/pgl/identity-rag/resolve", {"address": "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970"}),
    ("GET", "/api/v1/pgl/agent_123/genealogy", None),
    ("POST", "/api/v1/pgl/agent_123/quarantine", {}),
    ("GET", "/api/v1/agents/law", None),
    ("GET", "/api/v1/agents/registry", None),
    ("GET", "/api/v1/agents/fleet", None),
    ("GET", "/api/v1/agents/registry/1", None),
    ("GET", "/api/v1/agents/skills", None),

    # Category D: Guardrails & Memory
    ("POST", "/api/v1/agent-guardrails/agent_123/guardrails", {"rules": {}}),
    ("POST", "/api/v1/agent-guardrails/agent_123/evaluate-input", {"input": "test prompt"}),
    ("POST", "/api/v1/agent-guardrails/agent_123/evaluate-output", {"output": "test response"}),
    ("POST", "/api/v1/agent-guardrails/agent_123/evaluate-tool-call", {"tool_name": "mcp_bash"}),
    ("POST", "/api/v1/agent-memory/agent_123/memory/store", {"content": "test memory"}),
    ("GET", "/api/v1/agent-memory/agent_123/memory/search?query=test", None),
    ("POST", "/api/v1/agent-memory/agent_123/context/ctx_123/update", {"prompt": "new system instructions"}),
    ("DELETE", "/api/v1/agent-memory/agent_123/memory/mem_123", None),

    # Category E: On-Chain Settlement & VNP
    ("POST", "/api/v1/x402/register-api", {"name": "New endpoint", "target_url": "http://localhost"}),
    ("POST", "/api/v1/x402/verify", {"receipt_id": "rcpt_123", "proof_hash": "0xabc", "evidence_hash": "0xdef"}),
    ("POST", "/api/v1/x402/flash-loan", {"amount_usdc": 10.0}),
    ("POST", "/api/v1/agents/skills/skill_123/invoke", {}),
    ("POST", "/api/v1/vnp/bounty/submit-proof", {"provider_id": "prov_123", "proof_transaction_hash": "0xabc"}),
    ("POST", "/api/v1/vnp/beacon", {"provider_id": "prov_123", "stake_amount": 10.0}),
    ("GET", "/api/v1/billing/ledger", None),
    ("GET", "/api/v1/vnp/stakes", None),
    ("GET", "/api/v1/billing/receipts/rcpt_123", None),

    # Category F: Compliance & Audits
    ("POST", "/api/v1/compliance/check", {}),
    ("GET", "/api/v1/compliance/frameworks", None),
    ("POST", "/api/v1/privacy/detect-pii", {"text": "My email is test@test.com"}),
    ("POST", "/api/v1/privacy/mask-pii", {"text": "My email is test@test.com"}),
    ("POST", "/api/v1/content-safety/scan", {"text": "clean prompt"}),
    ("GET", "/api/v1/audit/verify/log_123", None),
    ("GET", "/api/v1/audit/logs", None),
    ("GET", "/api/v1/audit/logs/log_123", None),
    ("GET", "/api/v1/compliance/evidence/framework_123/export", None),

    # Category G: Observability & Self-Learning
    ("GET", "/api/v1/gpc/stats", None),
    ("GET", "/api/v1/explain/routing/dec_123", None),
    ("GET", "/api/v1/explain/cost/pred_123", None),
    ("GET", "/api/v1/gpc/ssrn-signals", None),
    ("GET", "/api/v1/gpc/observability/signals", None),
    ("POST", "/api/v1/onboarding/register", {"organization_name": "Outly", "owner_address": "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970"}),
    ("POST", "/api/v1/playground/evaluate", {}),
    ("POST", "/api/v1/copilot/explain", {"code": "print('hello')"}),
    ("POST", "/api/v1/terminal/command", {"command": "echo hello"}),
    ("GET", "/api/v1/forensics/replay", None),
    ("GET", "/api/v1/onboarding/metrics", None),

    # Category H: Mission Lock
    ("POST", "/api/v1/mission-lock/agents/agent_123/act", {"intent": "step forward"}),
    ("POST", "/api/v1/mission-lock/agents/agent_123/update", {"trace_id": "trc_123", "reward": 1.0}),
    ("GET", "/api/v1/mission-lock/agents/agent_123/state", None),
    ("POST", "/api/v1/mission-lock/agents/agent_123/adjust", {"rigidity_factor": 0.5}),
    ("GET", "/api/v1/mission-lock/teams/team_123/coordinate", None),
    ("GET", "/api/v1/mission-lock/agents/agent_123/trace", None),
    ("GET", "/api/v1/mission-lock/agents/agent_123/metrics", None)
]

@pytest.mark.parametrize("method,path,payload", ENDPOINTS)
def test_payapi_compliance_endpoints(method, path, payload):
    if method == "POST":
        response = client.post(path, json=payload)
    elif method == "GET":
        response = client.get(path)
    elif method == "DELETE":
        response = client.delete(path)
    else:
        raise ValueError(f"Unsupported method: {method}")

    # Assert that the route is resolved and not a 404
    assert response.status_code != 404, f"Endpoint {method} {path} returned 404 Not Found"
    # Assert it returned a successful status code or auth error (if middleware rejected it)
    assert response.status_code in [200, 201, 401, 402], f"Endpoint {method} {path} returned {response.status_code}"
