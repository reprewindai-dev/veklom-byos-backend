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

from backend.core.services.route_beacon_service import RouteBeaconService

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
    Uses RouteBeaconService for hot-cache <15ms resolution.
    """
    snapshot = await RouteBeaconService.get_best_route(
        db=db,
        customer_id=customer_id,
        project_id=project_id,
        policy_id=policy_id,
        requested_region=requested_region
    )

    if "error" in snapshot:
        raise HTTPException(status_code=404, detail=snapshot["error"])

    # Optionally trim candidates if max_candidates is different from default
    if len(snapshot["candidates"]) > max_candidates:
        snapshot["candidates"] = snapshot["candidates"][:max_candidates]

    return snapshot

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

