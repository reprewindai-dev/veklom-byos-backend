import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from backend.core.database.database import get_db
from backend.core.security.vnp_security import VNPEventVerifier, VNPSecurityError
from backend.db.models.vnp import (
    ProbeEvent, UsageEvent, Api, Customer, Project, SdkCredential, RoutePolicy, Provider, ProbeResultState
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ingest",
    tags=["VNP Data Plane"],
    responses={404: {"description": "Not found"}},
)

# Pydantic Schemas for Ingest
class ProbeMeasurement(BaseModel):
    dns_ms: Optional[int] = None
    connect_ms: Optional[int] = None
    tls_ms: Optional[int] = None
    ttfb_ms: Optional[int] = None
    total_ms: int
    status_code: Optional[int] = None
    success: bool
    timeout: bool = False
    error_class: Optional[str] = None

class SignatureBlock(BaseModel):
    alg: str
    key_id: str
    sig: str

class ProbeEventItem(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    producer: Dict[str, Any]
    target: Dict[str, Any]
    measurement: ProbeMeasurement
    signature: SignatureBlock

class ProbeBatch(BaseModel):
    batch_id: str
    events: List[ProbeEventItem]

class UsageMeasurement(BaseModel):
    billable_units: int
    unit_type: str
    success: bool
    response_ms: Optional[int] = None
    http_status: Optional[int] = None
    retry_count: int = 0
    failover_count: int = 0

class UsageCommercial(BaseModel):
    pricing_tier_id: Optional[str] = None
    preauth_amount_minor: Optional[int] = None
    final_amount_minor: Optional[int] = None
    currency: str = "USD"

class UsageEventItem(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    customer_id: str
    project_id: str
    credential_id: str
    policy_id: Optional[str] = None
    request: Dict[str, Any]
    usage: UsageMeasurement
    commercial: UsageCommercial
    signature: SignatureBlock

class UsageBatch(BaseModel):
    batch_id: str
    events: List[UsageEventItem]


def _map_error_class_to_state(success: bool, timeout: bool, error_class: Optional[str]) -> ProbeResultState:
    if success:
        return ProbeResultState.success
    if timeout:
        return ProbeResultState.timeout
    if error_class == "dns_error":
        return ProbeResultState.dns_error
    if error_class == "tls_error":
        return ProbeResultState.tls_error
    if error_class == "transport_error":
        return ProbeResultState.transport_error
    return ProbeResultState.http_error


@router.post("/probe-events")
async def ingest_probe_events(
    batch: ProbeBatch = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept one or more signed probe events from Cloudflare global workers.
    """
    accepted = 0
    rejected = 0
    deduplicated = 0

    now = datetime.now(timezone.utc)

    for event in batch.events:
        # 1. Reject events > 10 mins in future
        if event.occurred_at > now + timedelta(minutes=10):
            rejected += 1
            continue

        # 2. Check for duplicate event_id
        stmt = select(ProbeEvent.id).where(ProbeEvent.event_id == event.event_id)
        existing = await db.execute(stmt)
        if existing.first():
            deduplicated += 1
            continue

        # 3. Verify Signature
        try:
            # Reconstruct the raw dict for signature verification
            # The producer's public key is stored in the event signature block
            public_key_b64 = event.signature.key_id
            
            # Use exact pydantic dump for canonicalization
            raw_event = event.model_dump(mode="json")
            VNPEventVerifier.verify_event_signature(raw_event, public_key_b64)
            
        except VNPSecurityError as e:
            logger.warning(f"Signature verification failed for {event.event_id}: {e}")
            rejected += 1
            continue

        # 4. Insert into DB
        try:
            new_probe = ProbeEvent(
                event_id=event.event_id,
                worker_id=event.producer.get("worker_id", "unknown"),
                worker_region=event.producer.get("region", "unknown"),
                runtime=event.producer.get("runtime", "unknown"),
                api_id=event.target.get("api_id"),
                api_region_code=event.target.get("region_code"),
                endpoint_url=event.target.get("endpoint_url"),
                occurred_at=event.occurred_at,
                dns_ms=event.measurement.dns_ms,
                connect_ms=event.measurement.connect_ms,
                tls_ms=event.measurement.tls_ms,
                ttfb_ms=event.measurement.ttfb_ms,
                total_ms=event.measurement.total_ms,
                status_code=event.measurement.status_code,
                result_state=_map_error_class_to_state(
                    event.measurement.success, 
                    event.measurement.timeout, 
                    event.measurement.error_class
                ),
                success=event.measurement.success,
                timeout=event.measurement.timeout,
                error_class=event.measurement.error_class,
                signature_alg=event.signature.alg,
                signature_key_id=event.signature.key_id,
                signature_value=event.signature.sig,
                received_at=now
            )
            db.add(new_probe)
            accepted += 1
        except Exception as e:
            logger.error(f"Failed to insert probe event {event.event_id}: {e}")
            rejected += 1

    await db.commit()
    
    return {
        "accepted": accepted,
        "rejected": rejected,
        "deduplicated": deduplicated
    }


@router.post("/usage-events")
async def ingest_usage_events(
    batch: UsageBatch = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept billable usage events from the SDK or Gateway.
    """
    accepted = 0
    rejected = 0
    deduplicated = 0

    now = datetime.now(timezone.utc)

    for event in batch.events:
        if event.occurred_at > now + timedelta(minutes=10):
            rejected += 1
            continue

        stmt = select(UsageEvent.id).where(UsageEvent.event_id == event.event_id)
        existing = await db.execute(stmt)
        if existing.first():
            deduplicated += 1
            continue

        try:
            new_usage = UsageEvent(
                event_id=event.event_id,
                customer_id=event.customer_id,
                project_id=event.project_id,
                credential_id=event.credential_id,
                policy_id=event.policy_id,
                request_id=event.request.get("request_id"),
                api_id=event.request.get("api_id"),
                provider_id=event.request.get("provider_id"),
                provider_region=event.request.get("provider_region"),
                sdk_region=event.request.get("sdk_region"),
                route_snapshot_id=event.request.get("route_snapshot_id"),
                billable_units=event.usage.billable_units,
                unit_type=event.usage.unit_type,
                success=event.usage.success,
                response_ms=event.usage.response_ms,
                http_status=event.usage.http_status,
                retry_count=event.usage.retry_count,
                failover_count=event.usage.failover_count,
                preauth_amount_minor=event.commercial.preauth_amount_minor,
                final_amount_minor=event.commercial.final_amount_minor,
                currency=event.commercial.currency,
                occurred_at=event.occurred_at,
                signature_alg=event.signature.alg,
                signature_key_id=event.signature.key_id,
                signature_value=event.signature.sig,
                received_at=now
            )
            db.add(new_usage)
            accepted += 1
        except Exception as e:
            logger.error(f"Failed to insert usage event {event.event_id}: {e}")
            rejected += 1

    await db.commit()
    
    return {
        "accepted": accepted,
        "rejected": rejected,
        "deduplicated": deduplicated
    }
