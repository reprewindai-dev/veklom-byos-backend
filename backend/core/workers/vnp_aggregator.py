import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import math

from backend.core.database.database import get_db_session
from backend.db.models.vnp import ProbeEvent, RegionalTelemetry, Api
from sqlalchemy.future import select
from sqlalchemy import delete

def calculate_percentile(data, percentile):
    if not data:
        return 0
    data.sort()
    index = (percentile / 100) * (len(data) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return data[lower]
    weight = index - lower
    return data[lower] * (1 - weight) + data[upper] * weight

async def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting VNP Aggregator...")
    
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)
    
    async with get_db_session() as db:
        # Fetch all probe events in the last 24h
        events_result = await db.execute(
            select(ProbeEvent).where(ProbeEvent.measured_at >= window_start)
        )
        events = events_result.scalars().all()
        
        if not events:
            print("No probe events found for the last 24 hours.")
            return
            
        print(f"Loaded {len(events)} probe events for aggregation.")
        
        # Group by api_id and region
        grouped_data = {}
        for ev in events:
            key = (ev.api_id, ev.region)
            if key not in grouped_data:
                grouped_data[key] = {
                    "latencies": [],
                    "success_count": 0,
                    "total_count": 0
                }
            
            group = grouped_data[key]
            group["total_count"] += 1
            if ev.status_code and 200 <= ev.status_code < 300:
                group["success_count"] += 1
            if ev.latency_ms is not None:
                group["latencies"].append(ev.latency_ms)
                
        # Generate new telemetry records
        new_telemetry_records = []
        for (api_id, region), stats in grouped_data.items():
            total = stats["total_count"]
            success = stats["success_count"]
            lats = stats["latencies"]
            
            uptime_pct = (success / total) * 100.0 if total > 0 else 0.0
            error_rate = 100.0 - uptime_pct
            
            p50 = calculate_percentile(lats, 50) if lats else 0
            p95 = calculate_percentile(lats, 95) if lats else 0
            p99 = calculate_percentile(lats, 99) if lats else 0
            
            # For this MVP phase, trust_score is derived simply from uptime
            trust_score = uptime_pct / 100.0
            
            telemetry = RegionalTelemetry(
                api_id=api_id,
                region_code=region,
                window_start=window_start,
                window_end=now,
                sample_count=total,
                success_count=success,
                p50_latency_ms=int(p50),
                p95_latency_ms=int(p95),
                p99_latency_ms=int(p99),
                error_rate_percent=error_rate,
                uptime_percent=uptime_pct,
                throughput_rps=0, # Phase 4 feature
                trust_score=trust_score,
                measured_at=now
            )
            new_telemetry_records.append(telemetry)
            
        # Optional: We clear out the old regional telemetry for these APIs to avoid duplication,
        # or we just let it accumulate if the frontend groups by the latest one.
        # Since the leaderboard usually wants the "current" rolling window, let's delete old records for the updated APIs.
        if new_telemetry_records:
            api_ids = list(set([api_id for api_id, _ in grouped_data.keys()]))
            await db.execute(
                delete(RegionalTelemetry).where(RegionalTelemetry.api_id.in_(api_ids))
            )
            
            db.add_all(new_telemetry_records)
            await db.commit()
            
            print(f"Aggregated and saved {len(new_telemetry_records)} telemetry windows.")
            for t in new_telemetry_records:
                print(f"  - API {t.api_id} in {t.region_code}: uptime={t.uptime_percent:.2f}%, p95={t.p95_latency_ms}ms")

if __name__ == "__main__":
    asyncio.run(main())
