
import httpx
import json
import hashlib
import time

BASE_URL = "https://api.veklom.com"

print("\n[*] Firing payment for /api/v1/x402/score...")
dummy_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()
proof = {"payment_proof_hash": f"0x{dummy_hash}"}
resp = httpx.post(
    f"{BASE_URL}/api/v1/x402/score",
    headers={"X-Payment-Verified": json.dumps(proof)},
    json={"subject_id": "test_agent_123"}
)
print(f"  [>] API Response: {resp.status_code} {resp.text}")

print("\n[*] Firing payment for /api/v1/ai/chat...")
resp_chat = httpx.post(
    f"{BASE_URL}/api/v1/ai/chat",
    json={"messages": [{"role": "user", "content": "Hello!"}], "model": "llama3.2:latest"}
)
print(f"  [>] API Response: {resp_chat.status_code} {resp_chat.text}")

