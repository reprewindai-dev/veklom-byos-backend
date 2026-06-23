"""VNP Routing and Data Ingestion API."""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import nacl.signing
import nacl.exceptions
from nacl.encoding import HexEncoder

from backend.core.database.database import get_db
from backend.db.models.vnp import VNPMonitoredAPI, VNPValidator, VNPProbeMetric
from backend.core.services.vnp_scoring import update_api_composite_score, get_cached_api_score

router = APIRouter(prefix="/vnp", tags=["Veklom Network Protocol"])


class ProbeMetricPayload(BaseModel):
    api_id: str
    validator_id: str
    region: str
    latency_ms: int
    http_status_code: int
    success: bool


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
    validator = await db.get(VNPValidator, payload.validator_id)
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
    metric = VNPProbeMetric(
        api_id=payload.api_id,
        validator_id=payload.validator_id,
        region=payload.region,
        latency_ms=payload.latency_ms,
        http_status_code=payload.http_status_code,
        success=payload.success,
        signature=x_vnp_signature
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
    stmt = select(VNPMonitoredAPI)
    result = await db.execute(stmt)
    apis = result.scalars().all()
    
    return {
        "network_status": "operational",
        "routes": [
            {
                "api_id": api.api_id,
                "provider": api.provider_name,
                "endpoint": api.endpoint_url,
                "composite_score": api.current_composite_score,
                "stability": api.stability_rating
            }
            for api in apis
        ]
    }
