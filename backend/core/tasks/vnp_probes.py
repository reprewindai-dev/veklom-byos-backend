import asyncio
import time
import httpx
import logging
from datetime import datetime, timezone
from backend.core.database.database import get_db_session
from backend.db.models.vnp import VnpMetric

logger = logging.getLogger(__name__)

# APIs to ping to simulate the VNP Edge Swarm
VNP_TARGETS = [
    {"id": "openai", "url": "https://api.openai.com/v1/models"},
    {"id": "anthropic", "url": "https://api.anthropic.com/v1/models"},
    {"id": "stripe", "url": "https://api.stripe.com/v1/charges"}
]

async def ping_target(client: httpx.AsyncClient, target: dict) -> tuple:
    start_time = time.monotonic()
    is_up = False
    
    try:
        # We expect a 401 Unauthorized for these since we don't send auth headers,
        # but a 401 still means the API is UP and responding to TLS/HTTP.
        response = await client.get(target["url"], timeout=5.0)
        is_up = response.status_code in (200, 401, 403)
    except Exception as e:
        logger.warning(f"[VNP Probe] Failed to ping {target['id']}: {e}")
        
    latency_ms = int((time.monotonic() - start_time) * 1000)
    return target["id"], latency_ms, is_up

async def run_vnp_probes():
    """
    Background task that periodically pings target APIs and records real latency.
    Runs continuously while the FastAPI app is alive.
    """
    logger.info("[VNP Probe Swarm] Initialized physical edge probes.")
    
    async with httpx.AsyncClient() as client:
        while True:
            tasks = [ping_target(client, target) for target in VNP_TARGETS]
            results = await asyncio.gather(*tasks)
            
            # Persist to database
            async for db in get_db_session():
                try:
                    for api_name, latency_ms, is_up in results:
                        metric = VnpMetric(
                            api_name=api_name,
                            latency_ms=latency_ms,
                            is_up=is_up,
                            measured_at=datetime.now(timezone.utc)
                        )
                        db.add(metric)
                    await db.commit()
                except Exception as e:
                    logger.error(f"[VNP Probe Swarm] DB commit failed: {e}")
                finally:
                    break # just need one session
            
            # Ping every 10 seconds to generate a realistic stream of data
            await asyncio.sleep(10)
