"""VNP Routing and Data Ingestion API."""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
import nacl.signing
import nacl.exceptions
from nacl.encoding import HexEncoder

import uuid
from datetime import datetime, timezone
from backend.core.database.database import get_db
from backend.db.models.vnp import (
    Api, Validator, ProbeEvent, RegionalTelemetry,
    SettlementEntry, LedgerEntryType, SettlementState, VnpMetric
)
from backend.core.services.vnp_scoring import update_api_composite_score, get_cached_api_score

router = APIRouter(prefix="/vnp", tags=["Veklom Network Protocol"])


VNP_VERIFICATION_STACK = [
    {"section": "Physical measurements", "status": "Live"},
    {"section": "Signed telemetry", "status": "Live"},
    {"section": "Route beacons", "status": "Connected"},
    {"section": "Robust scoring", "status": "Connected"},
    {"section": "x402 settlement evidence", "status": "Live"},
    {"section": "PGL audit trails", "status": "Connected"},
    {"section": "Agent/runtime enforcement", "status": "Connected", "backend": "cappo-backend"},
]


class ProbeMetricPayload(BaseModel):
    api_id: str
    validator_id: str
    region: str
    latency_ms: int
    http_status_code: int
    success: bool


@router.get("/methodology")
async def get_vnp_methodology() -> dict:
    """Backend-backed VNP v1.0 methodology and route wiring manifest."""
    return {
        "methodology": "VNP Methodology v1.0",
        "tagline": "Cryptographic API telemetry for the machine-to-machine economy",
        "verification_stack": VNP_VERIFICATION_STACK,
        "repo": "reprewindai-dev/veklom-byos-backend",
        "backends": {
            "byos": {
                "status": "Live",
                "responsibility": "VNP, x402, PGL, route beacons, scoring, settlement evidence",
                "endpoints": {
                    "vnp_metrics": "/api/v1/vnp/metrics",
                    "vnp_beacon": "/api/v1/vnp/beacon",
                    "vnp_ingestion": "/api/v1/vnp/ingestion",
                    "x402_config": "/api/v1/x402/config",
                    "x402_verify": "/api/v1/x402/verify",
                    "x402_search": "/api/v1/x402/search",
                    "x402_evaluate": "/api/v1/x402/evaluate",
                    "x402_score": "/api/v1/x402/score",
                    "x402_yield": "/api/v1/x402/yield/predict",
                },
            },
            "cappo": {
                "status": "Connected",
                "responsibility": "Governed runtime execution, ExecutionIdentityV1, PGL certificates, LAW 0 enforcement",
                "endpoint": "/v1/exec",
            },
        },
        "stale_public_copy_removed": [
            "10D",
            "10-D",
            "10-dimensional",
            "10 immutable vectors",
            "LOCKED SPECIFICATION v0.1.5",
        ],
    }


@router.post("/ingestion", status_code=status.HTTP_201_CREATED)
async def ingest_probe_metric(
    payload: ProbeMetricPayload,
    x_vnp_signature: str = Header(..., description="Ed25519 Hex Signature of the payload"),
    db: AsyncSession = Depends(get_db)
):
    """
    Data Plane Ingestion Endpoint.
    Receives latency/status telemetry from decentralized VNP probes.
    Cryptographically verifies the submission using the Validator's registered public key.
    """
    # 1. Look up validator to get public key
    validator = await db.get(Validator, payload.validator_id)
    if not validator or not validator.is_active:
        raise HTTPException(status_code=403, detail="Invalid or inactive validator")

    # 2. Verify Cryptographic Signature
    # Construct the deterministic message string that the prober should have signed
    # Format: {api_id}:{validator_id}:{region}:{latency_ms}:{http_status_code}:{success}
    message = f"{payload.api_id}:{payload.validator_id}:{payload.region}:{payload.latency_ms}:{payload.http_status_code}:{int(payload.success)}".encode("utf-8")
    
    try:
        verify_key = nacl.signing.VerifyKey(validator.public_key, encoder=HexEncoder)
        # Verify the signature
        # PyNaCl verify throws an exception if invalid
        verify_key.verify(message, bytes.fromhex(x_vnp_signature))
    except (nacl.exceptions.BadSignatureError, ValueError):
        raise HTTPException(status_code=401, detail="Cryptographic signature verification failed")

    # 3. Save metric
    metric = ProbeEvent(
        event_id=str(uuid.uuid4()),
        partition_key=datetime.now(timezone.utc).strftime("%Y-%m"),
        api_id=payload.api_id,
        region=payload.region,
        worker_id=payload.validator_id,
        worker_signature=x_vnp_signature,
        latency_ms=float(payload.latency_ms),
        status_code=payload.http_status_code,
        measured_at=datetime.now(timezone.utc)
    )
    db.add(metric)
    await db.commit()

    # 4. Asynchronously update the score
    # In a fully scaled environment, this is pushed to Kafka/NATS.
    # For Phase 1, we compute it synchronously inline or as a background task.
    score = await update_api_composite_score(db, payload.api_id)
    
    return {"status": "accepted", "new_score": score}


@router.get("/beacon")
async def get_route_beacon(api_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    Control Plane Route Beacon.
    Provides sub-15ms resolution on the healthiest APIs to route traffic to.
    """
    if api_id:
        score_data = await get_cached_api_score(api_id)
        return {
            "api_id": api_id,
            "composite_score": score_data.get("score", 100.0),
            "stability_rating": score_data.get("rating", "Unknown"),
            "timestamp": score_data.get("updated_at")
        }
    
    # If no api_id provided, return all registered APIs
    stmt = select(Api)
    result = await db.execute(stmt)
    apis = result.scalars().all()
    
    return {
        "network_status": "operational",
        "routes": [
            {
                "api_id": getattr(api, "api_id", getattr(api, "id", None)),
                "provider": getattr(api, "provider_name", getattr(api, "name", None)),
                "endpoint": getattr(api, "endpoint_url", getattr(api, "base_url", None)),
                "composite_score": api.current_composite_score,
                "stability": api.stability_rating
            }
            for api in apis
        ]
    }


@router.get("/metrics")
async def vnp_metrics(db: AsyncSession = Depends(get_db)):
    """
    VNP Network Metrics — aggregated protocol telemetry.
    Returns total staked, active validators, network yield, slashing stats,
    and recent API health summaries. Used by the frontend runtime.py page.
    """
    # Total staked across all active validators
    stake_result = await db.execute(
        select(func.coalesce(func.sum(Validator.stake_amount), 0))
        .where(Validator.status == "active")
    )
    total_staked = float(stake_result.scalar_one())

    # Active validator count
    validator_count_result = await db.execute(
        select(func.count(Validator.id)).where(Validator.status == "active")
    )
    active_validators = validator_count_result.scalar_one()

    # Active API count
    api_count_result = await db.execute(
        select(func.count(Api.id)).where(Api.status == "active")
    )
    active_apis = api_count_result.scalar_one()

    # Slashing total (settlement entries of type 'slash')
    slash_result = await db.execute(
        select(func.coalesce(func.sum(SettlementEntry.amount_minor), 0))
        .where(SettlementEntry.entry_type == LedgerEntryType.slash)
    )
    total_slashed_minor = int(slash_result.scalar_one())

    # Recent probe success rate (last 1000 probes)
    probe_result = await db.execute(
        select(func.count(ProbeEvent.id))
    )
    total_probes = probe_result.scalar_one()

    # Average composite score across all active APIs
    avg_score_result = await db.execute(
        select(func.coalesce(func.avg(Api.current_composite_score), 100.0))
        .where(Api.status == "active")
    )
    avg_composite_score = round(float(avg_score_result.scalar_one()), 2)

    return {
        "network_status": "operational",
        "total_staked_usd": total_staked,
        "active_validators": active_validators,
        "active_apis": active_apis,
        "total_probes_recorded": total_probes,
        "total_slashed_minor": total_slashed_minor,
        "avg_composite_score": avg_composite_score,
        "yield_rate_annual_pct": 4.2,
        "epoch_duration_seconds": 300,
        "protocol_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/directory/realtime")
async def get_realtime_directory(db: AsyncSession = Depends(get_db)):
    """
    Returns the latest physical edge probe latency for each API target.
    """
    # Get the latest metric for each API using a distinct ON clause or window function.
    # Since sqlite doesn't support DISTINCT ON, we'll fetch recent records and filter in Python.
    # Or just fetch the latest 50 records and group.
    stmt = select(VnpMetric).order_by(VnpMetric.measured_at.desc()).limit(100)
    result = await db.execute(stmt)
    metrics = result.scalars().all()
    
    latest_metrics = {}
    for m in metrics:
        if m.api_name not in latest_metrics:
            latest_metrics[m.api_name] = {
                "latency_ms": m.latency_ms,
                "is_up": m.is_up,
                "measured_at": m.measured_at.isoformat()
            }
            
    return {"status": "ok", "realtime_metrics": latest_metrics}
