import asyncio
import httpx
import time
import os
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Environment config
CAPI_URL = os.getenv("CAPI_URL", "http://capi:8002")
LEDGER_URL = os.getenv("LEDGER_URL", "http://ledger:8003")
PROBE_ID = os.getenv("PROBE_ID", "vnp-probe-us-east-1")
INTERVAL_SEC = int(os.getenv("INTERVAL_SEC", "5"))

async def ping_capi(client: httpx.AsyncClient):
    """Ping the CAPI execution node to measure latency."""
    start = time.perf_counter()
    try:
        resp = await client.get(f"{CAPI_URL}/health", timeout=2.0)
        resp.raise_for_status()
        latency_ms = (time.perf_counter() - start) * 1000
        return True, latency_ms
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        logging.warning(f"CAPI Ping failed: {e}")
        return False, latency_ms

async def submit_telemetry(client: httpx.AsyncClient, latency: float, is_up: bool):
    """Submit VNP telemetry to the Ledger node asynchronously."""
    payload = {
        "probe_id": PROBE_ID,
        "target": "capi",
        "latency_ms": latency,
        "is_up": is_up,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        # PGL verification runs on the Ledger node
        await client.post(f"{LEDGER_URL}/api/v1/telemetry", json=payload, timeout=2.0)
    except Exception as e:
        logging.error(f"Failed to submit telemetry to Ledger: {e}")

async def daemon_loop():
    logging.info(f"Starting VNP Probe Daemon ({PROBE_ID})")
    async with httpx.AsyncClient() as client:
        while True:
            is_up, latency = await ping_capi(client)
            logging.info(f"Ping result - UP: {is_up}, Latency: {latency:.2f}ms")
            
            # Non-blocking submission to Ledger
            asyncio.create_task(submit_telemetry(client, latency, is_up))
            
            await asyncio.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    try:
        asyncio.run(daemon_loop())
    except KeyboardInterrupt:
        logging.info("VNP Probe Daemon shutting down.")
