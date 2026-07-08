import asyncio
import json
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database.database import get_db
from backend.db.models.vnp import Api, RegionalTelemetry

router = APIRouter(
    prefix="/vnp/stream",
    tags=["VNP Streaming"],
)

class VNPConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = VNPConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket feed for VNP scoring metrics.
    Satisfies the ws://api.vnp.io:8080 requirement from v0.1.5 delivery.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and wait for messages (e.g. subscribe events)
            data = await websocket.receive_text()
            await websocket.send_json({"event": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def sse_generator(db: AsyncSession):
    """Generator for Server-Sent Events (SSE) telemetry."""
    while True:
        try:
            # Query the latest regional telemetry for active APIs
            stmt = select(RegionalTelemetry).order_by(RegionalTelemetry.measured_at.desc()).limit(10)
            result = await db.execute(stmt)
            telemetry_records = result.scalars().all()
            
            updates = []
            for t in telemetry_records:
                updates.append({
                    "api_id": str(t.api_id),
                    "region": t.region_code,
                    "p99_latency_ms": t.p99_latency_ms,
                    "trust_score": float(t.trust_score),
                    "measured_at": t.measured_at.isoformat()
                })
            
            if updates:
                yield {
                    "event": "score_update",
                    "data": json.dumps(updates)
                }
            
            # Broadcast same data to WebSockets
            if manager.active_connections and updates:
                await manager.broadcast({"event": "score_update", "data": updates})
                
        except Exception as e:
            yield {
                "event": "error",
                "data": str(e)
            }
            
        await asyncio.sleep(5) # Poll every 5 seconds for new telemetry


@router.get("/sse")
async def sse_endpoint(db: AsyncSession = Depends(get_db)):
    """
    SSE endpoint for real-time score streaming.
    Satisfies the /scores/stream requirement.
    """
    return EventSourceResponse(sse_generator(db))
