import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from backend.core.database.database import get_db
from backend.db.models.vnp import (
    Api, ApiRegion, RoutePolicy, RegionalTelemetry, RouteSnapshot, ApiStatus, ValidatorState
)

logger = logging.getLogger(__name__)

CANONICAL_VNP_NODES = [
    {"id": "vnp-us-ashburn", "region": "us-ashburn", "name": "Ashburn Node", "x": 270, "y": 180},
    {"id": "vnp-us-hillsboro", "region": "us-hillsboro", "name": "Hillsboro Node", "x": 120, "y": 190},
    {"id": "vnp-de-nuremberg", "region": "de-nuremberg", "name": "Nuremberg Node", "x": 380, "y": 150},
    {"id": "vnp-de-falkenstein", "region": "de-falkenstein", "name": "Falkenstein Node", "x": 430, "y": 165},
    {"id": "vnp-sg-singapore", "region": "sg-singapore", "name": "Singapore Node", "x": 505, "y": 285},
]

REGION_ALIASES = {
    "us-east": "us-ashburn",
    "us-east-1": "us-ashburn",
    "us-east-1-ash": "us-ashburn",
    "useast": "us-ashburn",
    "ashburn": "us-ashburn",
    "us-west": "us-hillsboro",
    "us-west-1": "us-hillsboro",
    "us-west-1-hil": "us-hillsboro",
    "uswest": "us-hillsboro",
    "hillsboro": "us-hillsboro",
    "eu-north": "de-nuremberg",
    "eu-central-1-nur": "de-nuremberg",
    "nuremberg": "de-nuremberg",
    "eu-central": "de-falkenstein",
    "eu-central-1-fal": "de-falkenstein",
    "falkenstein": "de-falkenstein",
    "ap-southeast": "sg-singapore",
    "ap-southeast-1": "sg-singapore",
    "ap-southeast-1-sin": "sg-singapore",
    "apsoutheast": "sg-singapore",
    "singapore": "sg-singapore",
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


def canonical_region_from_node(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip().lower().replace("_", "-")
    if not raw:
        return None
    for node in CANONICAL_VNP_NODES:
        if node["region"] == raw:
            return node["region"]
    return canonical_region(raw)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def seconds_since(value: Optional[datetime]) -> Optional[int]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, int((utc_now() - value).total_seconds()))


def node_status(
    *,
    registration_status: Optional[str],
    revocation_state: Optional[str],
    active_key_count: int,
    latest_heartbeat: Optional[datetime],
    observation_count: int,
    freshness_seconds: int = 300,
) -> tuple[str, str]:
    if revocation_state:
        return "STANDBY", "Disconnected"
    if registration_status != "registered":
        return "STANDBY", "Config Incomplete"
    age = seconds_since(latest_heartbeat)
    if age is None:
        return "STANDBY", "Config Incomplete"
    if age > freshness_seconds:
        return "STANDBY", "Disconnected"
    if observation_count == 0:
        return "STANDBY", "Partially Implemented"
    if active_key_count == 0:
        return "STANDBY", "Partially Implemented"
    return "ATTESTING", "Connected"

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
    from backend.db.models.vnp import Validator, VnpNode, VnpNodeHeartbeat, VnpNodeKey, VnpObservation
    from backend.db.models.ledger import SettlementLedger, SettlementStatus
    
    # 1. Fetch the physical node registry first. Validators are a legacy
    # settlement concept; VNP node liveness requires registered nodes, active
    # keys, fresh signed heartbeats, and at least one accepted observation.
    node_stmt = select(VnpNode).order_by(VnpNode.created_at.asc()).limit(20)
    node_res = await db.execute(node_stmt)
    registry_nodes = node_res.scalars().all()

    nodes = []
    active_node_count = 0
    registered_node_count = 0
    config_incomplete_count = 0
    partially_implemented_count = 0

    if registry_nodes:
        nodes_by_region = {
            canonical_region_from_node(node.region_code): node
            for node in registry_nodes
            if canonical_region_from_node(node.region_code)
        }

        for canonical in CANONICAL_VNP_NODES:
            node = nodes_by_region.get(canonical["region"])
            if node:
                registered_node_count += 1
                key_count = (
                    await db.execute(
                        select(func.count(VnpNodeKey.id)).where(
                            VnpNodeKey.node_id == node.id,
                            VnpNodeKey.active.is_(True),
                            VnpNodeKey.revoked_at.is_(None),
                        )
                    )
                ).scalar_one()
                latest_heartbeat = (
                    await db.execute(
                        select(func.max(VnpNodeHeartbeat.timestamp)).where(
                            VnpNodeHeartbeat.node_id == node.id,
                        )
                    )
                ).scalar_one()
                observation_count = (
                    await db.execute(
                        select(func.count(VnpObservation.id)).where(
                            VnpObservation.node_id == node.id,
                        )
                    )
                ).scalar_one()
                latest_observation = (
                    await db.execute(
                        select(func.max(VnpObservation.completed_at)).where(
                            VnpObservation.node_id == node.id,
                        )
                    )
                ).scalar_one()
                status, status_str = node_status(
                    registration_status=node.registration_status,
                    revocation_state=node.revocation_state,
                    active_key_count=int(key_count),
                    latest_heartbeat=latest_heartbeat,
                    observation_count=int(observation_count),
                )
                if status_str == "Connected":
                    active_node_count += 1
                if status_str == "Config Incomplete":
                    config_incomplete_count += 1
                if status_str == "Partially Implemented":
                    partially_implemented_count += 1
                nodes.append({
                    "id": str(node.id),
                    "name": node.name,
                    "region": canonical["region"],
                    "physicalLocation": node.physical_location,
                    "macroRegion": node.macro_region,
                    "jurisdiction": node.jurisdiction,
                    "gdprZone": bool(node.gdpr_zone),
                    "status": status,
                    "status_str": status_str,
                    "x": canonical["x"],
                    "y": canonical["y"],
                    "stakeUsd": 0,
                    "cpuMs": 0.1 if status_str == "Connected" else 0,
                    "poolUtilization": 10 if status_str == "Connected" else 0,
                    "version": node.software_version or "Config Incomplete",
                    "tenantLock": "veklom",
                    "registrationStatus": node.registration_status,
                    "activeKeyCount": int(key_count),
                    "heartbeatFreshnessSeconds": seconds_since(latest_heartbeat),
                    "lastHeartbeat": latest_heartbeat.isoformat() if latest_heartbeat else None,
                    "observationCount": int(observation_count),
                    "lastObservation": latest_observation.isoformat() if latest_observation else None,
                })
            else:
                config_incomplete_count += 1
                nodes.append({
                    "id": canonical["id"],
                    "name": canonical["name"],
                    "region": canonical["region"],
                    "status": "STANDBY",
                    "status_str": "Config Incomplete",
                    "x": canonical["x"],
                    "y": canonical["y"],
                    "stakeUsd": 0,
                    "cpuMs": 0,
                    "poolUtilization": 0,
                    "version": "Config Incomplete",
                    "tenantLock": "veklom",
                    "registrationStatus": "missing",
                    "activeKeyCount": 0,
                    "heartbeatFreshnessSeconds": None,
                    "lastHeartbeat": None,
                    "observationCount": 0,
                    "lastObservation": None,
                })
    else:
        val_stmt = select(Validator).where(Validator.state == ValidatorState.active).limit(20)
        val_res = await db.execute(val_stmt)
        validators = val_res.scalars().all()
        validators_by_region = {}
        for validator in validators:
            region_key = canonical_region(validator.operator_entity)
            if region_key:
                validators_by_region.setdefault(region_key, validator)

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
                "tenantLock": "veklom",
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
    if registry_nodes:
        eventsLog.append(
            f"Five-node VNP registry loaded; {registered_node_count}/5 nodes registered, "
            f"{active_node_count}/5 connected, {partially_implemented_count}/5 partially implemented, "
            f"{config_incomplete_count}/5 config incomplete."
        )
    elif active_node_count < len(CANONICAL_VNP_NODES):
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
            "registeredNodes": registered_node_count,
            "partiallyImplementedNodes": partially_implemented_count,
            "configIncompleteNodes": config_incomplete_count,
            "isActiveStorm": False,
            "safetyGuardActive": True
        }
    }

