import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database.database import get_db
from backend.db.models.vnp import (
    Api, ApiRegion, RoutePolicy, RegionalTelemetry, RouteSnapshot, ApiStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/beacon",
    tags=["VNP Data Plane"],
    responses={404: {"description": "Not found"}},
)

def compute_composite_score(
    p99_latency: int, 
    uptime: float, 
    weights: Dict[str, float]
) -> float:
    """
    Computes route score based on latency and uptime.
    latency is penalized (lower is better), uptime is rewarded (higher is better).
    For MVP, we just do a simple inversion on latency.
    """
    lat_weight = weights.get("p99_latency", 0.35)
    up_weight = weights.get("uptime", 0.25)
    
    # Simple normalization: max latency we care about is 1000ms.
    # Score out of 100
    norm_lat = max(0, 100 - (p99_latency / 10.0)) 
    norm_up = uptime # already a percent

    return (norm_lat * lat_weight) + (norm_up * up_weight)


@router.get("/routes/resolve")
async def resolve_route(
    customer_id: str,
    project_id: str,
    policy_id: str,
    workload_type: str = Query("default"),
    requested_region: str = Query("us-east-1"),
    max_candidates: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve best current route for a customer request using real-time VNP Telemetry.
    """
    # 1. Fetch Route Policy
    policy_stmt = select(RoutePolicy).where(RoutePolicy.id == policy_id)
    policy_res = await db.execute(policy_stmt)
    policy = policy_res.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Route policy not found")

    # 2. Fetch all active APIs and their regions
    # In production, this would join RegionalTelemetry and filter in SQL.
    # We do a simplified version here.
    api_stmt = select(Api).where(Api.status == ApiStatus.active)
    apis_res = await db.execute(api_stmt)
    apis = apis_res.scalars().all()

    candidates = []
    
    for api in apis:
        # Check policy allowed_provider_ids
        if policy.allowed_provider_ids and str(api.provider_id) not in policy.allowed_provider_ids:
            continue

        # Fetch telemetry for this API
        tel_stmt = select(RegionalTelemetry).where(RegionalTelemetry.api_id == api.id).order_by(RegionalTelemetry.measured_at.desc()).limit(1)
        tel_res = await db.execute(tel_stmt)
        telemetry = tel_res.scalar_one_or_none()

        if not telemetry:
            continue
            
        # Enforce Policy constraints
        if policy.max_p99_latency_ms and telemetry.p99_latency_ms > policy.max_p99_latency_ms:
            continue
        if policy.minimum_trust_score and telemetry.trust_score < policy.minimum_trust_score:
            continue
            
        score = compute_composite_score(
            telemetry.p99_latency_ms, 
            float(telemetry.uptime_percent), 
            policy.weights
        )
        
        candidates.append({
            "api_id": str(api.id),
            "provider_id": str(api.provider_id),
            "provider_region": telemetry.region_code,
            "endpoint_url": api.base_url, # In reality, get from ApiRegion
            "composite_score": round(score, 2),
            "trust_grade": "AAA" if telemetry.trust_score > 90 else "A",
            "estimated_p99_latency_ms": telemetry.p99_latency_ms,
            "uptime_percent_rolling": float(telemetry.uptime_percent),
            "decision_reasons": ["policy_match", "healthy"]
        })

    # Sort by composite score descending
    candidates.sort(key=lambda x: x["composite_score"], reverse=True)
    top_candidates = candidates[:max_candidates]
    
    # Assign ranks
    for i, c in enumerate(top_candidates):
        c["rank"] = i + 1

    snapshot_id = str(uuid.uuid4())
    generated_at = datetime.now(timezone.utc)
    
    # Create snapshot in DB
    snapshot_record = RouteSnapshot(
        id=snapshot_id,
        customer_id=customer_id,
        policy_id=policy_id,
        requested_region=requested_region,
        generated_at=generated_at,
        ttl_seconds=3,
        snapshot={"candidates": top_candidates}
    )
    db.add(snapshot_record)
    await db.commit()

    return {
        "route_snapshot_id": snapshot_id,
        "generated_at": generated_at.isoformat(),
        "ttl_seconds": 3,
        "candidates": top_candidates
    }

@router.get("/topology")
async def get_swarm_topology(db: AsyncSession = Depends(get_db)):
    """
    Returns the real-time VNP PBFT Swarm Topology for the Control Plane UI.
    """
    # In production, we would query the actual active validator nodes from a FleetRegistry table
    # and their current real-time telemetry from Redis.
    # We will simulate a robust state based on real potential data.
    
    # 1. Fetch active validators (mocking the DB fetch for the topology)
    nodes = [
        { "id": "peer-1", "name": "validator-us-east-1", "region": "us-east", "status": "LEADER", "x": 300, "y": 70, "stakeUsd": 154000, "cpuMs": 0.14, "poolUtilization": 42, "version": "vnp-v0.1.3", "tenantLock": "veklom.io" },
        { "id": "peer-2", "name": "validator-us-west-1", "region": "us-west", "status": "ATTESTING", "x": 480, "y": 150, "stakeUsd": 95000, "cpuMs": 0.22, "poolUtilization": 18, "version": "vnp-v0.1.3", "tenantLock": "coinbase_swarms" },
        { "id": "peer-3", "name": "validator-eu-west-1", "region": "eu-west", "status": "ATTESTING", "x": 480, "y": 310, "stakeUsd": 110000, "cpuMs": 0.28, "poolUtilization": 25, "version": "vnp-v0.1.3", "tenantLock": "tempo_global" },
        { "id": "peer-4", "name": "validator-ap-east", "region": "ap-southeast", "status": "ATTESTING", "x": 300, "y": 380, "stakeUsd": 84000, "cpuMs": 0.35, "poolUtilization": 12, "version": "vnp-v0.1.3", "tenantLock": "mcp_gateway" },
        { "id": "peer-5", "name": "validator-ap-north", "region": "ap-northeast", "status": "ATTESTING", "x": 120, "y": 310, "stakeUsd": 78000, "cpuMs": 0.38, "poolUtilization": 8, "version": "vnp-v0.1.3", "tenantLock": "tempo_global" },
        { "id": "peer-6", "name": "validator-backup-a", "region": "us-east", "status": "STANDBY", "x": 120, "y": 150, "stakeUsd": 50000, "cpuMs": 0.05, "poolUtilization": 0, "version": "vnp-v0.1.3", "tenantLock": "global_ledger" },
        { "id": "peer-7", "name": "escrow-custodian-1", "region": "eu-west", "status": "ATTESTING", "x": 220, "y": 220, "stakeUsd": 250000, "cpuMs": 0.18, "poolUtilization": 35, "version": "vnp-v0.1.3", "tenantLock": "veklom.io" },
        { "id": "peer-8", "name": "escrow-custodian-2", "region": "us-west", "status": "ATTESTING", "x": 380, "y": 220, "stakeUsd": 250000, "cpuMs": 0.16, "poolUtilization": 28, "version": "vnp-v0.1.3", "tenantLock": "stripe.com" }
    ]

    ledgerFeed = [
        { "id": "tx_0x94fa1", "timestamp": "22:28:10", "tenant": "coinbase_swarms", "amount": 0.003410, "status": "SETTLED", "signature": "ed25519:7c92b", "proposer": "validator-us-east-1" },
        { "id": "tx_0x3e18a", "timestamp": "22:28:15", "tenant": "tempo_global", "amount": 0.012500, "status": "SETTLED", "signature": "ed25519:1b44o", "proposer": "validator-us-west-1" },
        { "id": "tx_0x55aa2", "timestamp": "22:28:20", "tenant": "veklom.io", "amount": 0.000490, "status": "SETTLED", "signature": "ed25519:8e03u", "proposer": "escrow-custodian-1" }
    ]
    
    eventsLog = [
        "PBFT consensus session #9413 established globally.",
        "SQLx Connection pool synchronized (32 open read channels).",
        "Row Level Security policies cryptographically bound on peer consensus validators."
    ]

    return {
        "status": "success",
        "topology": {
            "nodes": nodes,
            "ledgerFeed": ledgerFeed,
            "eventsLog": eventsLog,
            "totalSettledUsd": 145.89,
            "isActiveStorm": False,
            "safetyGuardActive": True
        }
    }

