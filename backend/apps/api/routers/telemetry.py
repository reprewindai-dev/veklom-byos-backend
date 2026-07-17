"""
Veklom Telemetry API Router
============================
Exposes Agent Stability Index (ASI) and Context Divergence Score (CDS)
endpoints for measuring and alerting on agent behavioral drift.

Endpoints
---------
GET  /api/v1/telemetry/asi             — Rolling ASI score for the workspace
GET  /api/v1/telemetry/asi/history     — 24h ASI history ring
GET  /api/v1/telemetry/cds             — CDS between two sessions
GET  /api/v1/telemetry/cds/matrix      — Pairwise CDS for all active sessions
POST /api/v1/telemetry/asi/record      — Record new dimension observations (internal)

Auth
----
All endpoints require a valid Bearer JWT (workspace scope enforced by ZeroTrustMiddleware).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from backend.core.telemetry.asi import (  # type: ignore
    ASIDimensions,
    CDS_ALERT_THRESHOLD,
    ASI_ALERT_THRESHOLD,
    CDSResult,
    compute_cds,
    evaluate_workspace_asi,
    load_asi_history,
    load_asi_result,
    store_cds_alert,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


# ---------------------------------------------------------------------------
# Dependency: extract workspace_id from JWT
# ---------------------------------------------------------------------------

def _workspace_id_from_request(request: Request) -> str:
    """
    Extract workspace_id from the JWT claims injected by ZeroTrustMiddleware.
    Falls back to 'unknown' if not present (should never happen post-auth).
    """
    return getattr(request.state, "workspace_id", None) or "unknown"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ASIDimensionObservation(BaseModel):
    """Observed dimension values for a single interaction window."""
    # Quadrant 1 — Response Consistency
    c_sem: float = Field(1.0, ge=0.0, le=1.0, description="Output semantic similarity")
    c_path: float = Field(1.0, ge=0.0, le=1.0, description="Decision path consistency")
    c_conf: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score stability")

    # Quadrant 2 — Tool Usage
    t_sel: float = Field(1.0, ge=0.0, le=1.0, description="Tool selection consistency")
    t_seq: float = Field(1.0, ge=0.0, le=1.0, description="Tool sequencing consistency")
    t_param: float = Field(1.0, ge=0.0, le=1.0, description="Tool parameter stability")

    # Quadrant 3 — Inter-Agent Coordination
    i_agree: float = Field(1.0, ge=0.0, le=1.0, description="Consensus agreement rate")
    i_handoff: float = Field(1.0, ge=0.0, le=1.0, description="Handoff quality score")
    i_role: float = Field(1.0, ge=0.0, le=1.0, description="Role boundary adherence")

    # Quadrant 4 — Behavioral Boundaries
    b_length: float = Field(1.0, ge=0.0, le=1.0, description="Output length stability")
    b_error: float = Field(1.0, ge=0.0, le=1.0, description="Error rate stability")
    b_human: float = Field(1.0, ge=0.0, le=1.0, description="Human escalation stability")


class CDSRequest(BaseModel):
    session_a: str = Field(..., description="First session ID")
    session_b: str = Field(..., description="Second session ID")
    vector_a: List[float] = Field(..., description="Context vector for session A")
    vector_b: List[float] = Field(..., description="Context vector for session B")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/asi",
    summary="Agent Stability Index",
    description=(
        "Rolling ASI score for the calling workspace. "
        "Computed across 12 behavioral dimensions in 4 quadrants. "
        "ASI_t < 0.75 for 3+ consecutive windows triggers drift alert."
    ),
)
async def get_asi(request: Request):
    """
    Agent Stability Index (ASI) for the calling workspace.

    Returns the current rolling ASI_t score, all 12 dimension values,
    per-quadrant averages, and alert status.

    If no telemetry data exists yet, returns conservative baseline values (0.90).
    """
    workspace_id = _workspace_id_from_request(request)

    # Check Redis cache first
    cached = load_asi_result(workspace_id)
    if cached:
        return {
            **cached,
            "source": "cache",
            "_links": {
                "history": {"href": "/api/v1/telemetry/asi/history", "method": "GET"},
                "cds": {"href": "/api/v1/telemetry/cds", "method": "GET"},
                "manifest": {"href": "/protocol.json", "method": "GET"},
            },
        }

    # Compute fresh with baseline dimensions
    result = await asyncio.get_event_loop().run_in_executor(
        None, evaluate_workspace_asi, workspace_id, None
    )

    return {
        "workspace_id": result.workspace_id,
        "asi_t": result.asi_t,
        "alert": result.alert,
        "consecutive_alert_windows": result.consecutive_alert_windows,
        "alert_threshold": ASI_ALERT_THRESHOLD,
        "quadrant_scores": result.quadrant_scores,
        "dimensions": {
            "response_consistency": {
                "c_sem": result.dimensions.c_sem,
                "c_path": result.dimensions.c_path,
                "c_conf": result.dimensions.c_conf,
            },
            "tool_usage_patterns": {
                "t_sel": result.dimensions.t_sel,
                "t_seq": result.dimensions.t_seq,
                "t_param": result.dimensions.t_param,
            },
            "inter_agent_coordination": {
                "i_agree": result.dimensions.i_agree,
                "i_handoff": result.dimensions.i_handoff,
                "i_role": result.dimensions.i_role,
            },
            "behavioral_boundaries": {
                "b_length": result.dimensions.b_length,
                "b_error": result.dimensions.b_error,
                "b_human": result.dimensions.b_human,
            },
        },
        "window_size": result.window_size,
        "evaluated_at": result.evaluated_at,
        "source": "computed",
        "_links": {
            "history": {"href": "/api/v1/telemetry/asi/history", "method": "GET"},
            "cds": {"href": "/api/v1/telemetry/cds", "method": "GET"},
            "manifest": {"href": "/protocol.json", "method": "GET"},
        },
    }


@router.get(
    "/asi/history",
    summary="ASI 24h History",
    description="24-hour rolling ASI history for the workspace. Up to 48 entries (one per 30 min).",
)
async def get_asi_history(request: Request):
    """24-hour ASI history ring for drift trend analysis."""
    workspace_id = _workspace_id_from_request(request)
    history = await asyncio.get_event_loop().run_in_executor(
        None, load_asi_history, workspace_id
    )
    return {
        "workspace_id": workspace_id,
        "history": history,
        "count": len(history),
        "alert_threshold": ASI_ALERT_THRESHOLD,
        "_links": {
            "current": {"href": "/api/v1/telemetry/asi", "method": "GET"},
            "cds": {"href": "/api/v1/telemetry/cds", "method": "GET"},
        },
    }


@router.get(
    "/cds",
    summary="Context Divergence Score",
    description=(
        "Cosine distance between context vectors of two active agent sessions. "
        "CDS > 0.35 triggers a context_drift warning in the VNP audit trail. "
        "Provide session_a and session_b query params, plus base64-encoded vectors."
    ),
)
async def get_cds(
    request: Request,
    session_a: str = Query(..., description="First session ID"),
    session_b: str = Query(..., description="Second session ID"),
):
    """
    Context Divergence Score (CDS) between two agent sessions.

    In production, context vectors are retrieved from the session mesh store.
    For sessions without stored vectors, a synthetic high-divergence score (0.50)
    is returned to indicate unverified state.

    CDS(i, j, t) = 1 - (c_i · c_j) / (||c_i|| * ||c_j||)
    """
    workspace_id = _workspace_id_from_request(request)

    # Retrieve context vectors from session mesh store
    vector_a, vector_b = await _retrieve_session_vectors(session_a, session_b, workspace_id)

    cds = compute_cds(vector_a, vector_b)
    is_alert = cds > CDS_ALERT_THRESHOLD

    if is_alert:
        await asyncio.get_event_loop().run_in_executor(
            None, store_cds_alert, session_a, session_b, cds, workspace_id
        )

    return {
        "session_a": session_a,
        "session_b": session_b,
        "cds": cds,
        "alert": is_alert,
        "alert_threshold": CDS_ALERT_THRESHOLD,
        "interpretation": _interpret_cds(cds),
        "vector_dims": len(vector_a),
        "evaluated_at": datetime.now(tz=timezone.utc).isoformat(),
        "_links": {
            "matrix": {"href": "/api/v1/telemetry/cds/matrix", "method": "GET"},
            "asi": {"href": "/api/v1/telemetry/asi", "method": "GET"},
            "sessions": {"href": f"/api/v1/sessions/{session_a}/audit", "method": "GET"},
        },
    }


@router.get(
    "/cds/matrix",
    summary="Pairwise CDS Matrix",
    description="Pairwise Context Divergence Score for all active sessions in the workspace.",
)
async def get_cds_matrix(request: Request):
    """
    Pairwise CDS matrix for all active sessions.

    Retrieves all active session IDs for the workspace and computes
    pairwise CDS for every combination. Returns a matrix and highlights
    any pairs exceeding the alert threshold.
    """
    workspace_id = _workspace_id_from_request(request)

    active_sessions = await _get_active_sessions(workspace_id)

    matrix: List[Dict[str, Any]] = []
    alert_pairs: List[Dict[str, Any]] = []

    for i, sess_a in enumerate(active_sessions):
        for sess_b in active_sessions[i + 1:]:
            vec_a, vec_b = await _retrieve_session_vectors(sess_a, sess_b, workspace_id)
            cds = compute_cds(vec_a, vec_b)
            entry = {
                "session_a": sess_a,
                "session_b": sess_b,
                "cds": cds,
                "alert": cds > CDS_ALERT_THRESHOLD,
                "interpretation": _interpret_cds(cds),
            }
            matrix.append(entry)
            if cds > CDS_ALERT_THRESHOLD:
                alert_pairs.append(entry)

    return {
        "workspace_id": workspace_id,
        "active_sessions": active_sessions,
        "session_count": len(active_sessions),
        "matrix": matrix,
        "alert_pairs": alert_pairs,
        "alert_threshold": CDS_ALERT_THRESHOLD,
        "evaluated_at": datetime.now(tz=timezone.utc).isoformat(),
        "_links": {
            "asi": {"href": "/api/v1/telemetry/asi", "method": "GET"},
        },
    }


@router.post(
    "/asi/record",
    summary="Record ASI Observation",
    description=(
        "Internal endpoint for recording new ASI dimension observations. "
        "Called by GPC executor and session mesh after each interaction window."
    ),
    status_code=status.HTTP_202_ACCEPTED,
)
async def record_asi_observation(body: ASIDimensionObservation, request: Request):
    """
    Record new ASI dimension values for the workspace.
    Computes a new ASI_t, persists to Redis, and fires alert if threshold breached.
    """
    workspace_id = _workspace_id_from_request(request)

    dims = ASIDimensions(
        c_sem=body.c_sem, c_path=body.c_path, c_conf=body.c_conf,
        t_sel=body.t_sel, t_seq=body.t_seq, t_param=body.t_param,
        i_agree=body.i_agree, i_handoff=body.i_handoff, i_role=body.i_role,
        b_length=body.b_length, b_error=body.b_error, b_human=body.b_human,
    )

    result = await asyncio.get_event_loop().run_in_executor(
        None, evaluate_workspace_asi, workspace_id, dims
    )

    # Fire drift alert if warranted (async, off hot path)
    if result.alert and result.consecutive_alert_windows >= 3:
        asyncio.create_task(_fire_drift_alert(workspace_id, result.asi_t, result.consecutive_alert_windows))

    return {
        "accepted": True,
        "workspace_id": workspace_id,
        "asi_t": result.asi_t,
        "alert": result.alert,
        "evaluated_at": result.evaluated_at,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _retrieve_session_vectors(
    session_a: str,
    session_b: str,
    workspace_id: str,
) -> tuple[list[float], list[float]]:
    """
    Retrieve context vectors for two sessions from the session mesh Redis store.
    Returns synthetic vectors if not found (conservative: 0.50 CDS).
    """
    try:
        r = await asyncio.get_event_loop().run_in_executor(None, _get_redis_sync)
        if r:
            key_a = f"veklom:session:{session_a}:context_vector"
            key_b = f"veklom:session:{session_b}:context_vector"
            import json as _json
            raw_a = r.get(key_a)
            raw_b = r.get(key_b)
            vec_a = _json.loads(raw_a) if raw_a else _synthetic_vector(session_a)
            vec_b = _json.loads(raw_b) if raw_b else _synthetic_vector(session_b)
            return vec_a, vec_b
    except Exception as exc:
        logger.debug("Session vector retrieval failed: %s", exc)
    return _synthetic_vector(session_a), _synthetic_vector(session_b)


def _get_redis_sync():
    try:
        from backend.core.redis_client import get_redis_client  # type: ignore
        return get_redis_client()
    except Exception:
        return None


def _synthetic_vector(session_id: str) -> list[float]:
    """
    Generate a deterministic synthetic context vector from a session ID.
    Used when no real vector is stored — produces moderate CDS (~0.35-0.50).
    """
    import hashlib
    h = hashlib.sha256(session_id.encode()).digest()
    return [((b / 255.0) * 2 - 1) for b in h[:32]]  # 32-dim vector in [-1, 1]


async def _get_active_sessions(workspace_id: str) -> list[str]:
    """Return active session IDs for a workspace from Redis."""
    try:
        r = await asyncio.get_event_loop().run_in_executor(None, _get_redis_sync)
        if r:
            key = f"veklom:workspace:{workspace_id}:active_sessions"
            import json as _json
            raw = r.get(key)
            if raw:
                return _json.loads(raw)
    except Exception as exc:
        logger.debug("Active sessions retrieval failed: %s", exc)
    return []


def _interpret_cds(cds: float) -> str:
    """Human-readable CDS interpretation."""
    if cds < 0.10:
        return "Minimal divergence — contexts are highly aligned"
    elif cds < 0.25:
        return "Low divergence — minor context differences, acceptable"
    elif cds < 0.35:
        return "Moderate divergence — approaching alert threshold, monitor closely"
    elif cds < 0.55:
        return "High divergence — context drift detected, sync recommended"
    else:
        return "Critical divergence — agents operating on incompatible world states"


async def _fire_drift_alert(workspace_id: str, asi_t: float, consecutive: int) -> None:
    """
    Fire a drift alert. Currently logs to VNP audit trail.
    Future: POST to workspace webhook URL if configured.
    """
    try:
        r = _get_redis_sync()
        if r:
            import json as _json
            event = {
                "type": "asi.drift_alert",
                "workspace_id": workspace_id,
                "asi_t": asi_t,
                "consecutive_windows": consecutive,
                "threshold": ASI_ALERT_THRESHOLD,
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }
            r.lpush("veklom:audit:asi_alerts", _json.dumps(event))
            r.ltrim("veklom:audit:asi_alerts", 0, 999)
    except Exception as exc:
        logger.debug("Drift alert write failed: %s", exc)
