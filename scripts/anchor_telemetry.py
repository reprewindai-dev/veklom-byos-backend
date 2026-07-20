import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List
import uuid

# Ensure backend module is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from backend.core.database.database import async_session
from backend.db.models.vnp import Api, ProbeEvent, RegionalTelemetry
from backend.services.anchoring import hash_payload, create_merkle_root, anchor_merkle_root_to_base

async def main():
    async with async_session() as db:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Starting VNP Base L2 Anchoring Process...")
        
        # 1. Get all active APIs
        apis_result = await db.execute(select(Api).where(Api.status == "active"))
        apis = apis_result.scalars().all()
        print(f"Found {len(apis)} active APIs.")
        
        for api in apis:
            print(f"Processing API: {api.name} ({api.id})")
            
            # Fetch the latest ProbeEvents to build the Merkle Tree
            # We'll take the latest 50 probes from the last 24 hours
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            events_result = await db.execute(
                select(ProbeEvent)
                .where(and_(ProbeEvent.api_id == api.id, ProbeEvent.measured_at >= cutoff))
                .order_by(desc(ProbeEvent.measured_at))
                .limit(50)
            )
            events = events_result.scalars().all()
            
            if not events:
                print(f"  No recent ProbeEvents found for {api.name}, skipping.")
                continue
                
            print(f"  Found {len(events)} recent ProbeEvents. Generating Merkle Tree...")
            
            # 2. Hash each event payload
            leaf_hashes = []
            for event in events:
                payload = {
                    "event_id": event.event_id,
                    "api_id": str(event.api_id),
                    "region": event.region,
                    "latency_ms": event.latency_ms,
                    "status_code": event.status_code,
                    "measured_at": event.measured_at.isoformat()
                }
                leaf_hashes.append(hash_payload(payload))
                
            # 3. Compute Merkle Root
            merkle_root = create_merkle_root(leaf_hashes)
            print(f"  Computed Merkle Root: {merkle_root}")
            
            # 4. Anchor to Base L2
            window_start = events[-1].measured_at
            window_end = events[0].measured_at
            
            print(f"  Submitting to Base L2...")
            tx_hash = anchor_merkle_root_to_base(merkle_root, window_start, window_end)
            
            if not tx_hash:
                print("  Failed to anchor to Base L2.")
                continue
                
            print(f"  Anchored! TX Hash: {tx_hash}")
            
            # 5. Save to RegionalTelemetry (Create a new record or update latest)
            # Find an existing unanchored RegionalTelemetry for this API or create one
            tel_result = await db.execute(
                select(RegionalTelemetry)
                .where(and_(RegionalTelemetry.api_id == api.id, RegionalTelemetry.on_chain_anchor.is_(None)))
                .order_by(desc(RegionalTelemetry.measured_at))
                .limit(1)
            )
            telemetry = tel_result.scalar_one_or_none()
            
            if telemetry:
                print(f"  Updating existing RegionalTelemetry record (id={telemetry.id})")
                telemetry.on_chain_anchor = merkle_root
                telemetry.provenance_hash = tx_hash
                telemetry.window_start = window_start
                telemetry.window_end = window_end
            else:
                print("  Creating new RegionalTelemetry record.")
                telemetry = RegionalTelemetry(
                    api_id=api.id,
                    region_code="global",
                    window_start=window_start,
                    window_end=window_end,
                    sample_count=len(events),
                    success_count=sum(1 for e in events if e.status_code and e.status_code < 400),
                    p50_latency_ms=int(events[len(events)//2].latency_ms) if events else 0,
                    p95_latency_ms=int(events[max(0, int(len(events)*0.05))].latency_ms) if events else 0,
                    p99_latency_ms=int(events[max(0, int(len(events)*0.01))].latency_ms) if events else 0,
                    error_rate_percent=0.0,
                    uptime_percent=100.0,
                    throughput_rps=0,
                    trust_score=api.current_composite_score,
                    provenance_hash=tx_hash,
                    on_chain_anchor=merkle_root,
                    measured_at=datetime.now(timezone.utc)
                )
                db.add(telemetry)
                
            # Update the ProbeEvents to point to this anchor
            for event in events:
                event.cryptography_anchor = merkle_root
                event.provenance_hash = tx_hash
                
        await db.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
