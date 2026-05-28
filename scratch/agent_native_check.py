#!/usr/bin/env python3
import urllib.request
import urllib.error
import json
import sys

BASE = "http://localhost:8088"

TESTS = [
    ("agent-json", "GET", "/.well-known/agent.json", 200, lambda b, h: "openapi_url" in json.loads(b)),
    ("pricing-api", "GET", "/api/v1/pricing", 200, lambda b, h: json.loads(b).get("network") == "base"),
    ("llms-txt", "GET", "/llms.txt", 200, lambda b, h: "text/plain" in h.get("Content-Type", "")),
    ("mcp-sse", "GET", "/mcp/sse", 200, lambda b, h: "text/event-stream" in h.get("Content-Type", "")),
    ("receipts-api", "GET", "/api/v1/receipts/rcpt_test123", 200, lambda b, h: json.loads(b).get("receipt_id") == "rcpt_test123"),
]

print("Starting Agent-Native Verification...")
all_passed = True

# Helper to make request
def run_req(url, method, data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read(), dict(r.info())
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.info())

# 1. Check Standard GET Tests
for name, method, path, exp_code, check_fn in TESTS:
    url = BASE + path
    code, body, headers = run_req(url, method)
    body_str = body.decode("utf-8")
    
    ok = (code == exp_code)
    if ok and check_fn:
        try:
            ok = check_fn(body_str, headers)
        except Exception as ex:
            ok = False
            print(f"[{name}] check function failed: {ex}")
            
    if ok:
        print(f"[PASS] {name:<15} (code={code})")
    else:
        print(f"[FAIL] {name:<15} (code={code}, expected={exp_code})")
        print(f"Body: {body_str[:300]}")
        all_passed = False

# 2. Check HTTP 402 Gating on Paid Route
print("\nVerifying HTTP 402 Payment Required gating...")
code, body, headers = run_req(BASE + "/api/v1/gpc/compile", "POST", {"intent": "test"})
body_str = body.decode("utf-8")
try:
    payload = json.loads(body_str)
    is_402_ok = (
        code == 402 and
        payload.get("error") == "payment_required" and
        payload.get("price", {}).get("currency") == "USDC" and
        "request_id" in payload
    )
except Exception as ex:
    is_402_ok = False
    print(f"Failed to parse 402 body: {ex}")

if is_402_ok:
    print("[PASS] HTTP 402 gating schema verified successfully.")
else:
    print("[FAIL] HTTP 402 gating check failed.")
    print(f"Code: {code}, Body: {body_str}")
    all_passed = False

# 3. Check Evidence Verification
print("\nVerifying Evidence verification...")
verify_body = {
    "evidence_id": "ev_01J",
    "sha256": "3c4d"
}
code, body, headers = run_req(BASE + "/api/v1/evidence/verify", "POST", verify_body)
body_str = body.decode("utf-8")
try:
    payload = json.loads(body_str)
    is_verify_ok = (
        code == 200 and
        payload.get("verified") is True and
        "signature" in payload
    )
except Exception as ex:
    is_verify_ok = False
    print(f"Failed to parse verify body: {ex}")

if is_verify_ok:
    print("[PASS] Evidence verification verified successfully.")
else:
    print("[FAIL] Evidence verification check failed.")
    print(f"Code: {code}, Body: {body_str}")
    all_passed = False

if all_passed:
    print("\n[SUCCESS] All Agent-Native verification tests passed.")
    sys.exit(0)
else:
    print("\n[FAILURE] Verification tests failed.")
    sys.exit(1)
