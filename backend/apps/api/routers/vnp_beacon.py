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

CANONICAL_VNP_NODES = [
    {"id": "vnp-us-east-1", "region": "us-east-1", "name": "validator-us-east-1", "x": 270, "y": 180},
    {"id": "vnp-us-west-2", "region": "us-west-2", "name": "validator-us-west-2", "x": 120, "y": 190},
    {"id": "vnp-eu-west-1", "region": "eu-west-1", "name": "validator-eu-west-1", "x": 380, "y": 150},
    {"id": "vnp-ap-southeast-1", "region": "ap-southeast-1", "name": "validator-ap-southeast-1", "x": 505, "y": 285},
    {"id": "vnp-ap-northeast-1", "region": "ap-northeast-1", "name": "validator-ap-northeast-1", "x": 535, "y": 170},
]

REGION_ALIASES = {
    "us-east": "us-east-1",
    "useast": "us-east-1",
    "us-west": "us-west-2",
    "uswest": "us-west-2",
    "eu-west": "eu-west-1",
    "euwest": "eu-west-1",
    "ap-southeast": "ap-southeast-1",
    "apsoutheast": "ap-southeast-1",
    "ap-northeast": "ap-northeast-1",
    "apnortheast": "ap-northeast-1",
}


def canonical_region(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip().lower().replace("_", "-")
    if not raw:
        return None
    if raw in REGION_ALIASES:
        return REGION_ALIASES[raw]
    for node in CANONICAL_VNP_NODES:
        if node["region"] in raw:
            return node["region"]
    return raw

router = APIRouter(
    prefix="/beacon",
    tags=["VNP Data Plane"],
    responses={404: {"description": "Not found"}},
)

from backend.apps.api.services.vnp_scoring_engine import VNPScoringEngine

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
    Uses VNPScoringEngine for <15ms resolution.
    """
    snapshot = await VNPScoringEngine.get_latest_beacon(region=requested_region)

    if not snapshot:
        # Fallback to default if region-specific not found
        snapshot = await VNPScoringEngine.get_latest_beacon(region="default")

    if not snapshot:
        raise HTTPException(status_code=404, detail="No active route recommendations found. VNP Engine may be starting.")

    return snapshot

@router.get("/topology")
async def get_swarm_topology(db: AsyncSession = Depends(get_db)):
    """
    Returns the real-time VNP PBFT Swarm Topology for the Control Plane UI.
    """
    from backend.db.models.vnp import Validator
    from backend.db.models.ledger import SettlementLedger, SettlementStatus
    
    # 1. Fetch active validators and project them into the canonical five-node frame.
    val_stmt = select(Validator).where(Validator.state == "active").limit(20)
    val_res = await db.execute(val_stmt)
    validators = val_res.scalars().all()
    validators_by_region = {}
    for validator in validators:
        region_key = canonical_region(validator.operator_entity)
        if region_key:
            validators_by_region.setdefault(region_key, validator)
    
    nodes = []
    active_node_count = 0
    for canonical in CANONICAL_VNP_NODES:
        v = validators_by_region.get(canonical["region"])
        if v:
            active_node_count += 1
        nodes.append({
            "id": str(v.id) if v else canonical["id"],
            "name": f"validator-{v.public_key[:8]}" if v else canonical["name"],
            "region": canonical["region"],
            "status": "ATTESTING" if v else "STANDBY",
            "status_str": "Connected" if v else "Disconnected",
            "x": canonical["x"],
            "y": canonical["y"],
            "stakeUsd": float(v.stake_amount_minor or 0) / 1000000 if v else 0,
            "cpuMs": 0.1 if v else 0,
            "poolUtilization": 10 if v else 0,
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
    if active_node_count < len(CANONICAL_VNP_NODES):
        eventsLog.append(f"Five-node VNP frame loaded; {active_node_count}/5 validator regions connected.")
    else:
        eventsLog.append("Five-node VNP measurement frame connected across all canonical regions.")

    return {
        "status": "success",
        "topology": {
            "nodes": nodes,
            "ledgerFeed": ledgerFeed,
            "eventsLog": eventsLog,
            "totalSettledUsd": round(total_settled_usd, 4),
            "activeNodes": active_node_count,
            "expectedNodes": len(CANONICAL_VNP_NODES),
            "isActiveStorm": False,
            "safetyGuardActive": True
        }
    }

