import asyncio
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone

import aiohttp
from sqlalchemy.future import select

# Adjust imports according to the veklom-byos-backend structure
from backend.core.database.database import get_db_session
from backend.db.models.vnp import Api, ProbeEvent

WORKER_ID = "vnp-worker-useast1-01"
REGION = "us-east-1"
logger = logging.getLogger(__name__)


def _content_hash(
    *,
    api_id,
    region: str,
    worker_id: str,
    url: str | None,
    status_code: int | None,
    latency_ms: float | None,
    error_reason: str | None,
    measured_at: datetime,
) -> str:
    payload = {
        "api_id": str(api_id),
        "region": region,
        "worker_id": worker_id,
        "url": url,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "error_reason": error_reason,
        "measured_at": measured_at.isoformat(),
    }
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


async def ping_api(session: aiohttp.ClientSession, api: Api) -> ProbeEvent:
    start_time = time.time()
    url = api.base_url

    # Simple timeout to prevent hanging probes
    timeout = aiohttp.ClientTimeout(total=5.0)

    status_code = None
    error_reason = None

    if not url:
        error_reason = "INVALID_CONFIGURATION: missing base_url"
        latency_ms = None
    else:
        try:
            async with session.get(url, timeout=timeout) as response:
                status_code = response.status
                # Read minimal bytes to ensure request completes
                await response.read()
        except asyncio.TimeoutError:
            error_reason = "timeout"
        except Exception as e:
            error_reason = str(e)[:255]

        latency_ms = (time.time() - start_time) * 1000.0
    now = datetime.now(timezone.utc)
    evidence_hash = _content_hash(
        api_id=api.id,
        region=REGION,
        worker_id=WORKER_ID,
        url=url,
        status_code=status_code,
        latency_ms=latency_ms,
        error_reason=error_reason,
        measured_at=now,
    )

    # Generate partition key YYYY-MM
    partition_key = now.strftime("%Y-%m")

    return ProbeEvent(
        event_id=f"probe_{uuid.uuid4().hex}",
        partition_key=partition_key,
        api_id=api.id,
        region=REGION,
        worker_id=WORKER_ID,
        worker_signature="UNSIGNED",
        latency_ms=latency_ms,
        status_code=status_code,
        error_reason=error_reason,
        measured_at=now,
        evidence_hash=evidence_hash,
        provenance_hash=evidence_hash,
        cryptography_anchor=None,
    )

async def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting VNP Prober...")

    async with get_db_session() as db:
        # Fetch active APIs
        apis_result = await db.execute(select(Api).where(Api.status == "active"))
        apis = apis_result.scalars().all()

        if not apis:
            print("No active APIs found to probe.")
            return

        print(f"Found {len(apis)} active APIs to probe.")

        async with aiohttp.ClientSession() as session:
            tasks = [ping_api(session, api) for api in apis]
            probe_events = await asyncio.gather(*tasks)

            # Save events to database
            try:
                db.add_all(probe_events)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Failed to record probe events.")
                return

            print(f"Successfully recorded {len(probe_events)} probe events.")

            for event in probe_events:
                latency = (
                    f"{event.latency_ms:.2f}ms"
                    if event.latency_ms is not None
                    else "UNAVAILABLE"
                )
                print(f"  - API {event.api_id}: status={event.status_code}, latency={latency}")

if __name__ == "__main__":
    asyncio.run(main())
