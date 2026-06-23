"""Internal Python Prober Fleet for VNP Phase 1.

This background worker simulates the decentralized Data Plane probes.
It runs on a loop, hits configured APIs to measure latency, signs the
results using a mock Validator Ed25519 key, and posts them to the Control Plane.
"""

import asyncio
import time
import httpx
import nacl.signing
from nacl.encoding import HexEncoder


# Pre-generated fixed keypair for the "Internal Local Prober Validator"
# In a real distributed system, each prober node has its own secret key
# and the public key is registered in VNPValidator.
PROBER_SECRET_KEY_HEX = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
try:
    signing_key = nacl.signing.SigningKey(PROBER_SECRET_KEY_HEX, encoder=HexEncoder)
    VALIDATOR_PUBLIC_KEY = signing_key.verify_key.encode(encoder=HexEncoder).decode('utf-8')
except Exception:
    # Fallback for simplicity if the fixed hex is invalid
    signing_key = nacl.signing.SigningKey.generate()
    VALIDATOR_PUBLIC_KEY = signing_key.verify_key.encode(encoder=HexEncoder).decode('utf-8')

import os

VALIDATOR_ID = os.environ.get("VNP_NODE_ID", "vnp-prober-node-001")
REGION = os.environ.get("VNP_REGION", "local-enclave")
INGESTION_URL = "http://127.0.0.1:8088/api/vnp/ingestion"

# Hardcoded APIs to monitor for this simulation
TARGET_APIS = [
    {"api_id": "api-openai-com", "url": "https://api.openai.com/v1/models"},
    {"api_id": "api-anthropic-com", "url": "https://api.anthropic.com/v1/models"},
    {"api_id": "httpbin-get", "url": "https://httpbin.org/get"}
]

async def probe_endpoint(client: httpx.AsyncClient, api: dict) -> dict:
    """Probe a single endpoint and record metrics."""
    start_time = time.time()
    try:
        response = await client.get(api["url"], timeout=5.0)
        latency_ms = int((time.time() - start_time) * 1000)
        # 401/403 are "success" for routing purposes if they respond fast and reliably.
        # It means the API is up, even if we didn't pass auth.
        success = response.status_code < 500
        status_code = response.status_code
    except httpx.RequestError:
        latency_ms = int((time.time() - start_time) * 1000)
        success = False
        status_code = 0
        
    return {
        "api_id": api["api_id"],
        "validator_id": VALIDATOR_ID,
        "region": REGION,
        "latency_ms": latency_ms,
        "http_status_code": status_code,
        "success": success
    }

async def sign_and_submit(client: httpx.AsyncClient, metric: dict):
    """Sign the metric payload and submit it to the VNP ingestion endpoint."""
    # Deterministic message string matching the server's expectation
    message = f"{metric['api_id']}:{metric['validator_id']}:{metric['region']}:{metric['latency_ms']}:{metric['http_status_code']}:{int(metric['success'])}".encode('utf-8')
    
    # Sign
    signed = signing_key.sign(message, encoder=HexEncoder)
    signature_hex = signed.signature.decode('utf-8')
    
    # Submit
    try:
        response = await client.post(
            INGESTION_URL,
            json=metric,
            headers={"X-VNP-Validator-Signature": signature_hex},
            timeout=2.0
        )
        if response.status_code != 201:
            print(f"[vnp-prober] Failed to ingest {metric['api_id']}: HTTP {response.status_code} - {response.text}")
        else:
            print(f"[vnp-prober] Successfully ingested {metric['api_id']} | Latency: {metric['latency_ms']}ms | Score: {response.json().get('new_score')}")
    except httpx.RequestError as e:
        print(f"[vnp-prober] Ingestion endpoint unreachable: {e}")

async def run_prober_loop():
    """Main loop for the internal prober fleet."""
    print(f"[vnp-prober] Starting internal prober fleet.")
    print(f"[vnp-prober] Validator ID: {VALIDATOR_ID}")
    print(f"[vnp-prober] Public Key: {VALIDATOR_PUBLIC_KEY}")
    
    # We use a single client for connection pooling
    async with httpx.AsyncClient() as client:
        while True:
            print(f"[vnp-prober] Waking up to probe {len(TARGET_APIS)} APIs...")
            tasks = [probe_endpoint(client, api) for api in TARGET_APIS]
            results = await asyncio.gather(*tasks)
            
            submit_tasks = [sign_and_submit(client, res) for res in results]
            await asyncio.gather(*submit_tasks)
            
            print("[vnp-prober] Sleeping for 30 seconds...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(run_prober_loop())
