import asyncio
import uuid
import time
from datetime import datetime, timezone
import aiohttp

# Adjust imports according to the veklom-byos-backend structure
from backend.core.database.database import get_db_session
from backend.db.models.vnp import Api, ProbeEvent
from sqlalchemy.future import select

WORKER_ID = "vnp-worker-useast1-01"
REGION = "us-east-1"

async def ping_api(session: aiohttp.ClientSession, api: Api) -> ProbeEvent:
    start_time = time.time()
    url = api.base_url or "http://localhost:80/health" # fallback to local health if None
    
    # Simple timeout to prevent hanging probes
    timeout = aiohttp.ClientTimeout(total=5.0)
    
    status_code = None
    error_reason = None
    
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
    
    # Generate partition key YYYY-MM
    partition_key = now.strftime("%Y-%m")
    
    return ProbeEvent(
        event_id=f"probe_{uuid.uuid4().hex}",
        partition_key=partition_key,
        api_id=api.id,
        region=REGION,
        worker_id=WORKER_ID,
        worker_signature="sig_dummy_worker_auth", # Placeholder until real worker auth
        latency_ms=latency_ms,
        status_code=status_code,
        error_reason=error_reason,
        measured_at=now,
        evidence_hash=f"hash_{uuid.uuid4().hex[:8]}" # Placeholder for cryptographic proof of ping
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
            db.add_all(probe_events)
            await db.commit()
            
            print(f"Successfully recorded {len(probe_events)} probe events.")
            
            for event in probe_events:
                print(f"  - API {event.api_id}: status={event.status_code}, latency={event.latency_ms:.2f}ms")

if __name__ == "__main__":
    asyncio.run(main())
