import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timezone

from backend.core.database.database import get_db
from backend.db.models.vnp import (
    Api,
    RegionalTelemetry,
    Incident,
    AuditLog,
    AlertConfig,
    Validator,
    SettlementEntry,
    LedgerEntryType,
)
from backend.apps.api.routers.vnp import build_vnp_verification_stack, get_vnp_evidence_counts

router = APIRouter(prefix="/vnp", tags=["runtime", "vnp"])

from sqlalchemy.orm import selectinload

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    # Fetch real APIs from database with their provider relationship eagerly loaded
    apis_result = await db.execute(select(Api).options(selectinload(Api.provider)))
    apis = apis_result.scalars().all()
    
    # We can fetch latest regional telemetry to construct full ApiState if needed,
    # but for now we'll just format the `Api` model attributes.
    api_list = []
    for api in apis:
        api_list.append({
            "id": str(api.id),
            "name": api.name,
            "provider": api.provider.legal_name if hasattr(api, 'provider') and api.provider else "Unknown Provider",
            "compositeScore": float(api.current_composite_score),
            "status": api.status.value,
        })

    validator_count_result = await db.execute(
        select(func.count(Validator.id)).where(Validator.status == "active")
    )
    active_validators = int(validator_count_result.scalar_one() or 0)

    api_count_result = await db.execute(
        select(func.count(Api.id)).where(Api.status == "active")
    )
    active_apis = int(api_count_result.scalar_one() or 0)

    evidence_counts = await get_vnp_evidence_counts(db)
    total_probes = evidence_counts["total_physical_measurements"]

    slash_result = await db.execute(
        select(func.coalesce(func.sum(SettlementEntry.amount_minor), 0))
        .where(SettlementEntry.entry_type == LedgerEntryType.slash)
    )
    total_slashed_minor = int(slash_result.scalar_one() or 0)

    settlement_count_result = await db.execute(select(func.count(SettlementEntry.id)))
    settlement_entries = int(settlement_count_result.scalar_one() or 0)

    avg_score_result = await db.execute(
        select(func.coalesce(func.avg(Api.current_composite_score), 100.0))
        .where(Api.status == "active")
    )
    avg_composite_score = round(float(avg_score_result.scalar_one() or 100.0), 2)

    # Fetch the latest on_chain_anchor across all telemetry for the network-wide beacon
    global_telemetry_stmt = select(RegionalTelemetry).where(RegionalTelemetry.on_chain_anchor.isnot(None)).order_by(RegionalTelemetry.measured_at.desc()).limit(1)
    global_tel_result = await db.execute(global_telemetry_stmt)
    latest_global_tel = global_tel_result.scalar_one_or_none()

    trust_beacon_merkle = latest_global_tel.on_chain_anchor if latest_global_tel else None
    block_anchored = 1 if trust_beacon_merkle else 0

    return {
        "apis": api_list,
        "network_status": "operational",
        "active_validators": active_validators,
        "active_apis": active_apis,
        "total_probes_recorded": total_probes,
        "probe_events": evidence_counts["probe_events"],
        "signed_probe_events": evidence_counts["total_signed_telemetry"],
        "signed_probe_event_rows": evidence_counts["signed_probe_events"],
        "signed_edge_observations": evidence_counts["signed_edge_observations"],
        "realtime_physical_probes": evidence_counts["realtime_physical_probes"],
        "total_physical_probes_recorded": total_probes,
        "verification_stack": build_vnp_verification_stack(evidence_counts),
        "total_slashed_minor": total_slashed_minor,
        "avg_composite_score": avg_composite_score,
        "settlement_entries": settlement_entries,
        "vnp_settlement_entries": evidence_counts["vnp_settlement_entries"],
        "canonical_settlement_entries": evidence_counts["canonical_settlement_entries"],
        "canonical_settled_entries": evidence_counts["canonical_settled_entries"],
        "canonical_settlement_tx_entries": evidence_counts["canonical_settlement_tx_entries"],
        "banker_settlement_entries": evidence_counts["banker_settlement_entries"],
        "x402_settlement_evidence": evidence_counts["x402_settlement_evidence"],
        "trustBeaconMerkle": trust_beacon_merkle,
        "trustBeaconStatus": "Anchored to Base L2" if trust_beacon_merkle else "Needs proof",
        "blockAnchored": block_anchored,
        "blockAnchoredStatus": "Verified" if block_anchored else "Needs proof",
        "protocol_version": "1.0.0",
        "methodology": "VNP Methodology v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/alerts/config")
async def get_alert_configs(db: AsyncSession = Depends(get_db)):
    configs_result = await db.execute(select(AlertConfig))
    configs = configs_result.scalars().all()
    return [
        {
            "id": str(c.id),
            "targetApi": c.target_api,
            "metricType": c.metric_type,
            "condition": c.condition,
            "thresholdValue": c.threshold_value,
            "region": c.region,
            "actions": c.actions,
            "enabled": c.enabled
        } for c in configs
    ]

@router.post("/alerts/config")
async def add_alert_config(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    new_config = AlertConfig(
        target_api=body.get("targetApi", "all"),
        metric_type=body.get("metricType", "latency_p99"),
        condition=body.get("condition", ">"),
        threshold_value=float(body.get("thresholdValue", 0)),
        region=body.get("region", "global"),
        actions=body.get("actions", ["log", "slack"]),
        enabled=True
    )
    db.add(new_config)
    await db.commit()
    return {"status": "ok", "id": str(new_config.id)}

@router.get("/alerts/triggered")
async def get_triggered_alerts(db: AsyncSession = Depends(get_db)):
    # Incidents map to triggered alerts
    incidents_result = await db.execute(select(Incident).order_by(desc(Incident.opened_at)).limit(50))
    incidents = incidents_result.scalars().all()
    
    return [
        {
            "id": str(i.id),
            "apiName": i.title,
            "region": "global",
            "metric": i.severity,
            "value": 0,
            "threshold": 0,
            "timestamp": i.opened_at.isoformat(),
            "status": "triggered" if i.state.value == "open" else "resolved"
        } for i in incidents
    ]

@router.get("/audit-logs")
async def get_audit_logs(db: AsyncSession = Depends(get_db)):
    logs_result = await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(100))
    logs = logs_result.scalars().all()
    
    return [
        {
            "id": str(l.id),
            "timestamp": l.created_at.isoformat(),
            "tenant": "provider" if l.actor_type.value == "provider" else "unknown",
            "actor": str(l.actor_id),
            "action": l.action,
            "entity": l.scope_type,
            "transaction": str(l.scope_id)
        } for l in logs
    ]

async def event_stream(db: AsyncSession) -> AsyncGenerator[str, None]:
    # In a real heavy-duty production setting, this would use Postgres LISTEN/NOTIFY or Redis PubSub.
    # For now, we will poll the DB for new ProbeEvents every 2 seconds to simulate a live SSE stream.
    last_timestamp = datetime.utcnow()
    
    while True:
        await asyncio.sleep(2)
        try:
            # Refresh session to see new commits
            # await db.refresh() 
            query = select(ProbeEvent).where(ProbeEvent.created_at > last_timestamp).order_by(ProbeEvent.created_at)
            events_result = await db.execute(query)
            events = events_result.scalars().all()
            
            for event in events:
                last_timestamp = max(last_timestamp, event.created_at)
                # Format exactly as frontend expects: 
                # { id: "37c5b55e37c5d44d", type: "MEASUREMENT", text: "[US-E] GPT-4o - p99: 148.7ms..." }
                data_id = str(event.id)[:16]
                lat = event.latency_ms if event.latency_ms else 0
                text = f"[{event.region}] Probe - p99: {lat:.1f}ms, err: {100 if event.error_reason else 0}%"
                
                yield f"data: {{\"id\": \"{data_id}\", \"type\": \"MEASUREMENT\", \"text\": \"{text}\"}}\n\n"
        except Exception as e:
            # Yield error or pass
            pass

@router.get("/stream")
async def sse_stream(db: AsyncSession = Depends(get_db)):
    return StreamingResponse(event_stream(db), media_type="text/event-stream")
