import asyncio
import json
import hashlib
from datetime import datetime
import time
from unittest.mock import MagicMock, patch

from backend.security.mcp_gateway import EnhancedMCPAPIRuntime
from backend.core.governance.compliance_profiles import get_compliance_profile

class MockPipeline:
    def __init__(self, store):
        self.store = store
        self.watched = False
        self.operations = []
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def watch(self, *keys):
        self.watched = True
        
    def get(self, key):
        return self.store.get(key)
        
    def multi(self):
        pass
        
    def set(self, key, value):
        self.operations.append((key, value))
        
    def execute(self):
        for key, value in self.operations:
            self.store[key] = value

class MockRedis:
    def __init__(self):
        self.store = {}
        
    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True
        
    def exists(self, key):
        return 1 if key in self.store else 0
        
    def pipeline(self):
        return MockPipeline(self.store)

@patch('redis.Redis.from_url')
async def test_mcp_gateway(mock_redis_from_url):
    print("Running MCP Gateway Hardening Tests (v4 Distributed Architecture)...")
    
    mock_redis = MockRedis()
    mock_redis_from_url.return_value = mock_redis
    
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
    print("\n[Test 4] Exhaustive Bound Approval Token (Redis-Backed)")
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
    
    # 4B: Reused Token (Single-Use Replay Attack via Mock Redis)
    resp_4b = await runtime_global.process_request(req_4_valid)
    assert resp_4b["error"]["code"] == "403"
    assert "Token reuse detected" in resp_4b["error"]["message"]
    print("PASS: Passed: Blocked Reused Token (Distributed SETNX via Redis)")
    
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
    
    # Restore monkeypatch
    runtime_global.permissions_calculator.calculate_effective_permissions = original_calc

    # --- Test 5: Unified Run Timeline & Merkle Chaining ---
    print("\n[Test 5] Merkle Hash Chaining Audit")
    metadata = resp_4a["metadata"]
    timeline = metadata["unified_run_timeline"]
    phases = [event["phase"] for event in timeline]
    
    # We should have one contiguous sequence mapping to all 9 phases
    assert "INTAKE" in phases
    assert "APPROVAL_STATE" in phases
    assert "FINAL_LEDGER_EVENT" in phases
    
    # Validate Merkle Hash Chaining logic
    assert "merkle_previous_hash" in metadata
    assert metadata["merkle_previous_hash"] == "0000000000000000000000000000000000000000000000000000000000000000" # First entry
    
    # Now run another request to see if the hash chain correctly captures the head
    print("Running second request to verify Merkle chain links...")
    req_5_second = req_4_base.copy()
    req_5_second["nonce"] = "run_999"
    resp_5 = await runtime_global.process_request(req_5_second)
    assert resp_5.get("status") == "authorized"
    assert resp_5["metadata"]["merkle_previous_hash"] == resp_4a["evidence_hash"]
    
    print("PASS: Passed: Merkle Hash Chaining (Redis Shared State)")
    print("\nAll Distributed Hardening tests passed successfully.")

if __name__ == "__main__":
    asyncio.run(test_mcp_gateway())
