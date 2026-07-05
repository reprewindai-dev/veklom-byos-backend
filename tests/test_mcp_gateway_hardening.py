import asyncio
import json
import hashlib
from datetime import datetime
import time

from backend.security.mcp_gateway import EnhancedMCPAPIRuntime
from backend.core.governance.compliance_profiles import get_compliance_profile

async def test_mcp_gateway():
    print("Running MCP Gateway Hardening Tests (v3)...")
    
    # --- Test 1: Legal Denial (451) ---
    print("\n[Test 1] Legal Denial (451)")
    runtime_ontario = EnhancedMCPAPIRuntime(compliance_profile_id="ontario_public")
    req_1 = {
        "nonce": "run_123",
        "connection_id": "test_1",
        "agent_id": "agent_123",
        "capability_id": "cap_read",
        "target_region": "EU", # Ontario profile only allows CA
        "upstream_evidence_hash": "mock_hash"
    }
    resp_1 = await runtime_ontario.process_request(req_1)
    assert resp_1["error"]["code"] == "451", f"Expected 451, got {resp_1['error'].get('code')}"
    assert "headers" in resp_1, "Expected Link headers for 451"
    assert "blocked-by" in resp_1["headers"]["Link"], "Expected rel='blocked-by' in headers"
    print("PASS: Passed: Legal Denial (451)")

    # --- Test 2: Policy Denial (403) ---
    print("\n[Test 2] Policy Denial (403)")
    runtime_us = EnhancedMCPAPIRuntime(compliance_profile_id="us_hipaa")
    req_2 = {
        "nonce": "run_124",
        "connection_id": "test_2",
        "agent_id": "agent_123",
        "capability_id": "cap_read",
        "target_region": "EU", # US HIPAA only allows US
        "upstream_evidence_hash": "mock_hash"
    }
    resp_2 = await runtime_us.process_request(req_2)
    assert resp_2["error"]["code"] == "403", f"Expected 403, got {resp_2['error'].get('code')}"
    print("PASS: Passed: Policy Denial (403)")

    # --- Test 3: Fail-Closed Missing Config ---
    print("\n[Test 3] Fail-Closed Missing Config")
    runtime_unknown = EnhancedMCPAPIRuntime(compliance_profile_id="non_existent_profile")
    req_3 = {
        "nonce": "run_125",
        "connection_id": "test_3",
        "agent_id": "agent_123",
        "capability_id": "cap_read",
        "target_region": "US",
        "upstream_evidence_hash": "mock_hash"
    }
    resp_3 = await runtime_unknown.process_request(req_3)
    # Fail-closed profile requires evidence and allows 0 regions, so US will block it
    assert resp_3["error"]["code"] == "403", f"Expected 403 (policy block), got {resp_3['error'].get('code')}"
    print("PASS: Passed: Fail-Closed Config")
    
    # --- Test 4: Exhaustive Bound Approval Token ---
    print("\n[Test 4] Exhaustive Bound Approval Token")
    runtime_global = EnhancedMCPAPIRuntime(compliance_profile_id="global_default")
    
    payload = {"data": "test_data"}
    request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    nonce = "run_126"
    
    req_4_base = {
        "nonce": nonce,
        "connection_id": "test_4",
        "agent_id": "agent_123",
        "capability_id": "cap_read",
        "target_region": "US",
        "upstream_evidence_hash": "mock_hash",
        "payload": payload
    }
    
    # Monkeypatch permissions to force approval
    original_calc = runtime_global.permissions_calculator.calculate_effective_permissions
    runtime_global.permissions_calculator.calculate_effective_permissions = lambda *args: {"can_execute": True, "requires_approval": True}
    runtime_global.cost_attribution.can_afford_request = lambda *args, **kwargs: True
    
    composition = runtime_global.policy_composition.compose_policy("agent_123", "cap_read", None, None, None, None)
    policy_snapshot_id = hashlib.md5(json.dumps(composition, sort_keys=True).encode()).hexdigest()
    
    valid_token = {
        "expires_at": datetime.utcnow().timestamp() + 3600,
        "request_hash": request_hash,
        "policy_snapshot_id": policy_snapshot_id,
        "capability_id": "cap_read",
        "nonce": nonce,
        "signature": "valid_signature",
        "approver_id": "admin_human"
    }
    
    # 4A: Valid Token
    req_4_valid = req_4_base.copy()
    req_4_valid["approval_token"] = valid_token.copy()
    
    resp_4a = await runtime_global.process_request(req_4_valid)
    assert resp_4a.get("status") == "authorized", f"Expected authorized, got {resp_4a}"
    print("PASS: Passed: Bound Approval Token (Valid)")
    
    # 4B: Reused Token (Single-Use Replay Attack)
    resp_4b = await runtime_global.process_request(req_4_valid)
    assert resp_4b["error"]["code"] == "403"
    assert "Token reuse detected" in resp_4b["error"]["message"]
    print("PASS: Passed: Blocked Reused Token (Single-Use)")
    
    # Let's use a new nonce for the remaining tests so they don't fail on reuse
    nonce_c = "run_127"
    req_4_base["nonce"] = nonce_c
    
    # 4C: Expired Token
    expired_token = valid_token.copy()
    expired_token["nonce"] = nonce_c
    expired_token["expires_at"] = datetime.utcnow().timestamp() - 3600
    req_4c = req_4_base.copy()
    req_4c["approval_token"] = expired_token
    resp_4c = await runtime_global.process_request(req_4c)
    assert "expired" in resp_4c["error"]["message"]
    print("PASS: Passed: Blocked Expired Token")
    
    # 4D: Altered Payload
    nonce_d = "run_128"
    req_4_base["nonce"] = nonce_d
    altered_token = valid_token.copy()
    altered_token["nonce"] = nonce_d
    req_4d = req_4_base.copy()
    req_4d["payload"] = {"data": "malicious"}
    req_4d["approval_token"] = altered_token
    resp_4d = await runtime_global.process_request(req_4d)
    assert "request_hash mismatch" in resp_4d["error"]["message"]
    print("PASS: Passed: Blocked Altered Payload")

    # 4E: Altered Policy Snapshot
    nonce_e = "run_129"
    req_4_base["nonce"] = nonce_e
    altered_policy_token = valid_token.copy()
    altered_policy_token["nonce"] = nonce_e
    altered_policy_token["policy_snapshot_id"] = "fake_snapshot"
    req_4e = req_4_base.copy()
    req_4e["approval_token"] = altered_policy_token
    resp_4e = await runtime_global.process_request(req_4e)
    assert "policy_snapshot mismatch" in resp_4e["error"]["message"]
    print("PASS: Passed: Blocked Altered Policy")
    
    # Restore monkeypatch
    runtime_global.permissions_calculator.calculate_effective_permissions = original_calc

    # --- Test 5: Unified Run Timeline ---
    print("\n[Test 5] Unified Run Timeline Audit")
    timeline = resp_4a["metadata"]["unified_run_timeline"]
    phases = [event["phase"] for event in timeline]
    
    # We should have one contiguous sequence mapping to all 9 phases
    assert "INTAKE" in phases
    assert "IDENTITY" in phases
    assert "PROFILE_RESOLUTION" in phases
    assert "APPROVAL_STATE" in phases
    assert "FINAL_LEDGER_EVENT" in phases
    print("PASS: Passed: Unified Run Timeline Validation")

    print("\nAll Hardening tests passed successfully.")

if __name__ == "__main__":
    asyncio.run(test_mcp_gateway())
