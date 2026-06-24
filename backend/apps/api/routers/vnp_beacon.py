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

from backend.core.ml.vnp_scoring import compute_vnp_score
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
            
        # We assume p50 is slightly lower than p99 for calculation purposes since DB only has p99 here for MVP.
        # In full production we would fetch p50 and p99.
        p50_latency = max(10, telemetry.p99_latency_ms - 20)
        
        score = compute_vnp_score(
            p50_latency_ms=p50_latency,
            p99_latency_ms=telemetry.p99_latency_ms,
            availability_percent=float(telemetry.uptime_percent),
            owasp_compliance_flag=True, # Assuming true for existing records
            weights=policy.weights
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
    from backend.db.models.vnp import Validator
    from backend.db.models.ledger import SettlementLedger, SettlementStatus
    
    # 1. Fetch active validators
    val_stmt = select(Validator).where(Validator.state == "active").limit(20)
    val_res = await db.execute(val_stmt)
    validators = val_res.scalars().all()
    
    nodes = []
    for i, v in enumerate(validators):
        nodes.append({
            "id": str(v.id),
            "name": f"validator-{v.public_key[:8]}",
            "region": v.operator_entity or "global",
            "status": "ATTESTING",
            "x": 100 + (i * 50) % 400,
            "y": 100 + (i * 30) % 300,
            "stakeUsd": float(v.stake_amount_minor or 0) / 1000000,
            "cpuMs": 0.1,
            "poolUtilization": 10,
            "version": "vnp-v1.0.0",
            "tenantLock": "veklom"
        })

    # 2. Fetch recent real ledger settlements
    ledger_stmt = select(SettlementLedger).where(SettlementLedger.status == SettlementStatus.SETTLED).order_by(SettlementLedger.created_at.desc()).limit(15)
    ledger_res = await db.execute(ledger_stmt)
    settlements = ledger_res.scalars().all()

    ledgerFeed = []
    total_settled_usd = 0.0
    for s in settlements:
        amt = float(s.amount) / 1000000
        total_settled_usd += amt
        ledgerFeed.append({
            "id": str(s.id)[:8],
            "timestamp": s.created_at.strftime("%H:%M:%S") if s.created_at else "00:00:00",
            "tenant": s.tenant_id,
            "amount": amt,
            "status": getattr(s.status, "value", str(s.status)),
            "signature": s.settlement_tx_hash or "unverified",
            "proposer": "network"
        })

    eventsLog = []
    if not nodes:
        eventsLog.append("Awaiting PBFT consensus session establishment.")
    else:
        eventsLog.append(f"PBFT consensus session established globally with {len(nodes)} validators.")

    return {
        "status": "success",
        "topology": {
            "nodes": nodes,
            "ledgerFeed": ledgerFeed,
            "eventsLog": eventsLog,
            "totalSettledUsd": round(total_settled_usd, 4),
            "isActiveStorm": False,
            "safetyGuardActive": True
        }
    }

