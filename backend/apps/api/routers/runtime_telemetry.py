import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from backend.core.database.database import get_db
from backend.db.models.vnp import Api, RegionalTelemetry, Incident, AuditLog, AlertConfig, ProbeEvent

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
    
    # Optional: fetch a real block anchor count or trust beacon merkle from Ledger
    return {
        "apis": api_list,
        "trustBeaconMerkle": "db_hash_not_implemented",
        "blockAnchored": len(api_list) * 42 # dummy block anchored for now
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
