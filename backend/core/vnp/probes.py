import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from backend.core.database.database import get_db_session
from backend.db.models.vnp import VnpMetric

logger = logging.getLogger(__name__)

VNP_TARGETS = [
    {"id": "openai", "url": "https://api.openai.com/v1/models"},
    {"id": "anthropic", "url": "https://api.anthropic.com/v1/models"},
    {"id": "stripe", "url": "https://api.stripe.com/v1/charges"},
]


async def ping_target(client: httpx.AsyncClient, target: dict) -> tuple[str, int, bool]:
    start_time = time.monotonic()
    is_up = False

    try:
        response = await client.get(target["url"], timeout=5.0)
        is_up = response.status_code in (200, 401, 403)
    except Exception as exc:
        logger.warning("[VNP Probe] Failed to ping %s: %s", target["id"], exc)

    latency_ms = int((time.monotonic() - start_time) * 1000)
    return target["id"], latency_ms, is_up


async def run_vnp_probes() -> None:
    """Persist live physical probe latency for the public VNP directory/status."""
    logger.info("[VNP Probe Swarm] Initialized physical edge probes.")

    async with httpx.AsyncClient() as client:
        while True:
            tasks = [ping_target(client, target) for target in VNP_TARGETS]
            results = await asyncio.gather(*tasks)

            async for db in get_db_session():
                try:
                    for api_name, latency_ms, is_up in results:
                        db.add(
                            VnpMetric(
                                api_name=api_name,
                                latency_ms=latency_ms,
                                is_up=is_up,
                                measured_at=datetime.now(timezone.utc),
                            )
                        )
                    await db.commit()
                except Exception as exc:
                    logger.error("[VNP Probe Swarm] DB commit failed: %s", exc)
                finally:
                    break

            await asyncio.sleep(10)
