"""
GFR Router — Gradient Field Router API
For Veklom BYOS Backend

Endpoints:
  POST /api/v1/gfr/telemetry      — Scientist agents (063-067) push CPU/queue telemetry
  POST /api/v1/gfr/route          — Request a routing decision for a workload
  GET  /api/v1/gfr/field/snapshot — Full field snapshot (Agent-072 evidence replay)
  GET  /api/v1/gfr/field/status   — Lightweight status (Agent-129 Neural Orchestrator)
  GET  /api/v1/gfr/evidence/tail  — Last N evidence records from oprun trail
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from backend.core.services.agent_telemetry import (
    AgentTelemetryService,
    evidence_store,
)
from backend.core.services.gfr_engine import gfr

router = APIRouter(prefix="/gfr", tags=["GFR — Gradient Field Router"])


# --- Schemas ---

class TelemetryPayload(BaseModel):
    agent_id: int = Field(..., description="Agent ID (e.g. 63 for latency scientist)")
    agent_codename: str = Field(..., description="Human-readable codename e.g. 'latency-scientist'")
    cpu_load: float = Field(..., ge=0.0, le=1.0, description="Normalised CPU load 0.0-1.0")
    queue_depth: float = Field(..., ge=0.0, le=1.0, description="Normalised queue depth 0.0-1.0")
    row: Optional[int] = Field(None, description="Grid row override (uses registry if omitted)")
    col: Optional[int] = Field(None, description="Grid col override (uses registry if omitted)")

    @field_validator("cpu_load", "queue_depth")
    @classmethod
    def clamp_floats(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class RouteRequest(BaseModel):
    agent_id: int = Field(..., description="Agent requesting routing (e.g. 121, 129)")
    origin_row: Optional[int] = Field(None, description="Override origin row")
    origin_col: Optional[int] = Field(None, description="Override origin col")


class BatchTelemetryPayload(BaseModel):
    updates: list[TelemetryPayload]
    triggered_by: str = Field(default="batch", description="Source agent codename")


# --- Endpoints ---

@router.post("/telemetry", summary="Ingest scientist agent telemetry")
async def ingest_telemetry(payload: TelemetryPayload):
    """
    Called by Scientist agents 063-067 after each measurement cycle.
    Updates the gradient field and records to the oprun evidence trail.
    """
    try:
        snap = AgentTelemetryService.ingest(
            agent_id=payload.agent_id,
            agent_codename=payload.agent_codename,
            cpu_load=payload.cpu_load,
            queue_depth=payload.queue_depth,
            row=payload.row,
            col=payload.col,
        )
        return {
            "status": "ok",
            "field_snapshot": {
                "timestamp": snap.timestamp,
                "active_nodes": snap.active_nodes,
                "hotspot_count": snap.hotspot_count,
                "triggered_by": snap.triggered_by,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telemetry/batch", summary="Batch-ingest telemetry for multiple nodes")
async def ingest_telemetry_batch(payload: BatchTelemetryPayload):
    """
    Atomic batch update — useful when Swarm Architect (Agent-123)
    or Neural Orchestrator (Agent-129) pushes a full cluster snapshot.
    """
    try:
        updates = [
            {
                "row": AgentTelemetryService.resolve_node(u.agent_id, u.row, u.col)[0],
                "col": AgentTelemetryService.resolve_node(u.agent_id, u.row, u.col)[1],
                "cpu_load": u.cpu_load,
                "queue_depth": u.queue_depth,
            }
            for u in payload.updates
        ]
        gfr.update_field_batch(updates, triggered_by=payload.triggered_by)
        snap = gfr.snapshot(triggered_by=payload.triggered_by)
        return {
            "status": "ok",
            "nodes_updated": len(updates),
            "hotspot_count": snap.hotspot_count,
            "timestamp": snap.timestamp,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route", summary="Request routing decision for a workload")
async def route_workload(payload: RouteRequest):
    """
    Called by Agent-121 (Gladiator Optimizer) and Agent-129 (Neural Orchestrator)
    to get the optimal destination node for a workload via gradient descent.
    """
    try:
        decision = AgentTelemetryService.route_workload(
            agent_id=payload.agent_id,
            origin_row=payload.origin_row,
            origin_col=payload.origin_col,
        )
        return {
            "agent_id": decision.agent_id,
            "origin": {"row": decision.origin_row, "col": decision.origin_col},
            "destination": {"row": decision.dest_row, "col": decision.dest_col},
            "at_equilibrium": decision.at_equilibrium,
            "timestamp": decision.timestamp,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/field/snapshot", summary="Full field snapshot for evidence replay")
async def field_snapshot(triggered_by: str = Query(default="api")):
    """
    Returns the full NxN field matrix, gradients, and metadata.
    Used by Agent-072 (Evidence) for oprun evidence replay.
    """
    snap = gfr.snapshot(triggered_by=triggered_by)
    return {
        "timestamp": snap.timestamp,
        "triggered_by": snap.triggered_by,
        "active_nodes": snap.active_nodes,
        "hotspot_count": snap.hotspot_count,
        "field": snap.field,
        "gradient_y": snap.gradient_y,
        "gradient_x": snap.gradient_x,
    }


@router.get("/field/status", summary="Lightweight field status for Neural Orchestrator")
async def field_status():
    """
    Returns mean/max/min pressure, hotspot count, and equilibrium flag.
    Polled by Agent-129 (Neural Orchestrator) for macro routing decisions.
    """
    return gfr.status()


@router.get("/evidence/tail", summary="Last N oprun evidence records")
async def evidence_tail(n: int = Query(default=50, ge=1, le=500)):
    """
    Returns the last N records from the in-process oprun evidence trail.
    In production these will also be persisted via EvidenceArtifact model.
    """
    return {"records": evidence_store.tail(n)}


@router.delete("/field/reset", summary="Reset field to floor pressure (admin)")
async def reset_field():
    """Reset all nodes to FLOOR_VALUE. Used during cluster re-provisioning."""
    gfr.reset_field()
    return {"status": "reset", "message": "All nodes reset to floor pressure."}
