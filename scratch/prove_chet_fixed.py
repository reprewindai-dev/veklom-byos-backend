
import httpx
import json
import uuid

API_BASE = "https://api.veklom.com"
SCORE_ROUTE = "/api/v1/x402/score"

tx_hash = f"test_proof_{uuid.uuid4().hex[:12]}"
print(f"[*] Generated Payment Proof Hash: {tx_hash}")

proof_json = json.dumps({"payment_proof_hash": tx_hash})

resp = httpx.post(
    f"{API_BASE}{SCORE_ROUTE}",
    json={"tenant_id": "veklom-demo", "subject": "chet_parker_pay_api"},
    headers={
        "Content-Type": "application/json",
        "X-PAYMENT": proof_json,
        "X-Payment-Verified": proof_json
    },
    timeout=15.0
)

print(f"[*] /score status code: {resp.status_code}")
try:
    data = resp.json()
    print("[*] Score JSON:")
    print(json.dumps(data, indent=2))
except Exception:
    print(resp.text)

