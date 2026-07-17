"""
Veklom Telemetry — Agent Stability Index (ASI) & Context Divergence Score (CDS)
================================================================================
Enterprise-grade stability telemetry implementing the mathematical framework from
the Multi-Builder Convergence Geometry (MBCG) paper.

ASI (Agent Stability Index)
---------------------------
Rolling composite score across 12 behavioral dimensions in 4 quadrants.
Computed over a sliding N=50 interaction window per workspace.
Stored in Redis with 1h TTL. Alerts webhook if ASI_t < 0.75 for 3+ consecutive windows.

  ASI_t = 0.30 * avg(C_sem, C_path, C_conf)        # Response Consistency
        + 0.25 * avg(T_sel, T_seq, T_param)          # Tool Usage Patterns
        + 0.25 * avg(I_agree, I_handoff, I_role)     # Inter-Agent Coordination
        + 0.20 * avg(B_length, B_error, B_human)     # Behavioral Boundaries

CDS (Context Divergence Score)
-------------------------------
Cosine distance between context vectors of two agent sessions.
  CDS(i, j, t) = 1 - (c_i · c_j) / (||c_i|| * ||c_j||)

CDS > 0.35 triggers a context_drift warning in the VNP audit trail.
"""
from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASI_WINDOW_SIZE = 50          # Interactions per evaluation window
ASI_ALERT_THRESHOLD = 0.75    # Below this → drift detected
ASI_CONSECUTIVE_WINDOWS = 3   # Windows below threshold before alert fires
CDS_ALERT_THRESHOLD = 0.35    # Above this → context drift warning
ASI_CACHE_TTL = 3600          # Redis TTL: 1 hour
ASI_HISTORY_KEY_TTL = 86400   # Redis TTL for history: 24 hours

# ASI quadrant weights (must sum to 1.0)
WEIGHT_RESPONSE_CONSISTENCY = 0.30
WEIGHT_TOOL_USAGE = 0.25
WEIGHT_INTER_AGENT = 0.25
WEIGHT_BEHAVIORAL_BOUNDS = 0.20

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ASIDimensions:
    """
    All 12 dimensions of the Agent Stability Index.
    All values are floats in [0.0, 1.0] where 1.0 = perfectly stable.
    """
    # Quadrant 1 — Response Consistency (weight 0.30)
    c_sem: float = 1.0    # Output semantic similarity (embedding cosine sim)
    c_path: float = 1.0   # Decision path consistency
    c_conf: float = 1.0   # Output confidence score stability

    # Quadrant 2 — Tool Usage Patterns (weight 0.25)
    t_sel: float = 1.0    # Tool selection consistency
    t_seq: float = 1.0    # Tool sequencing consistency (Levenshtein normalized)
    t_param: float = 1.0  # Tool parameter stability

    # Quadrant 3 — Inter-Agent Coordination (weight 0.25)
    i_agree: float = 1.0  # Consensus agreement rate
    i_handoff: float = 1.0  # Handoff quality score
    i_role: float = 1.0   # Role boundary adherence

    # Quadrant 4 — Behavioral Boundaries (weight 0.20)
    b_length: float = 1.0  # Output length stability (inverse CV of token counts)
    b_error: float = 1.0   # Error rate stability
    b_human: float = 1.0   # Human escalation rate stability


@dataclass
class ASIResult:
    """Computed ASI score for a workspace at a given time."""
    workspace_id: str
    asi_t: float                    # Composite score in [0, 1]
    dimensions: ASIDimensions
    window_size: int
    evaluated_at: str               # ISO 8601
    alert: bool = False             # True if ASI_t < threshold
    consecutive_alert_windows: int = 0
    quadrant_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class CDSResult:
    """Computed CDS score between two agent sessions."""
    session_a: str
    session_b: str
    cds: float                      # Cosine distance in [0, 1]; 0 = identical
    alert: bool = False             # True if CDS > CDS_ALERT_THRESHOLD
    evaluated_at: str = ""
    vector_dims: int = 0


# ---------------------------------------------------------------------------
# ASI computation
# ---------------------------------------------------------------------------

def compute_asi(dimensions: ASIDimensions) -> Tuple[float, Dict[str, float]]:
    """
    Compute ASI_t from the 12 dimension values.

    Returns
    -------
    (asi_t, quadrant_scores)
        asi_t: float in [0, 1]
        quadrant_scores: dict with per-quadrant averages
    """
    q1 = (dimensions.c_sem + dimensions.c_path + dimensions.c_conf) / 3
    q2 = (dimensions.t_sel + dimensions.t_seq + dimensions.t_param) / 3
    q3 = (dimensions.i_agree + dimensions.i_handoff + dimensions.i_role) / 3
    q4 = (dimensions.b_length + dimensions.b_error + dimensions.b_human) / 3

    asi_t = (
        WEIGHT_RESPONSE_CONSISTENCY * q1
        + WEIGHT_TOOL_USAGE * q2
        + WEIGHT_INTER_AGENT * q3
        + WEIGHT_BEHAVIORAL_BOUNDS * q4
    )

    # Clamp to [0, 1] — floating point safety
    asi_t = max(0.0, min(1.0, round(asi_t, 6)))

    quadrant_scores = {
        "response_consistency": round(q1, 6),
        "tool_usage_patterns": round(q2, 6),
        "inter_agent_coordination": round(q3, 6),
        "behavioral_boundaries": round(q4, 6),
    }
    return asi_t, quadrant_scores


# ---------------------------------------------------------------------------
# CDS computation
# ---------------------------------------------------------------------------

def compute_cds(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Compute Context Divergence Score between two context vectors.

    CDS(i, j, t) = 1 - (c_i · c_j) / (||c_i|| * ||c_j||)

    Returns a float in [0, 1]:
      0.0 = identical context (no divergence)
      1.0 = orthogonal context (maximum divergence)
    """
    if not vector_a or not vector_b:
        return 1.0  # No context = maximum divergence

    # Pad shorter vector with zeros
    len_a, len_b = len(vector_a), len(vector_b)
    if len_a < len_b:
        vector_a = vector_a + [0.0] * (len_b - len_a)
    elif len_b < len_a:
        vector_b = vector_b + [0.0] * (len_a - len_b)

    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0

    cosine_similarity = dot / (norm_a * norm_b)
    # Clamp to [-1, 1] due to floating point errors, then map to [0, 1]
    cosine_similarity = max(-1.0, min(1.0, cosine_similarity))
    return round(1.0 - cosine_similarity, 6)


# ---------------------------------------------------------------------------
# Redis persistence helpers
# ---------------------------------------------------------------------------

def _get_redis():
    """Safely import and return the Redis client, or None."""
    try:
        from backend.core.redis_client import get_redis_client  # type: ignore
        return get_redis_client()
    except Exception:
        return None


def store_asi_result(result: ASIResult) -> None:
    """Persist ASI result to Redis. Swallows all exceptions."""
    r = _get_redis()
    if not r:
        return
    try:
        key_current = f"veklom:asi:{result.workspace_id}:current"
        key_history = f"veklom:asi:{result.workspace_id}:history"

        payload = {
            "workspace_id": result.workspace_id,
            "asi_t": result.asi_t,
            "alert": result.alert,
            "consecutive_alert_windows": result.consecutive_alert_windows,
            "quadrant_scores": result.quadrant_scores,
            "dimensions": {
                "c_sem": result.dimensions.c_sem,
                "c_path": result.dimensions.c_path,
                "c_conf": result.dimensions.c_conf,
                "t_sel": result.dimensions.t_sel,
                "t_seq": result.dimensions.t_seq,
                "t_param": result.dimensions.t_param,
                "i_agree": result.dimensions.i_agree,
                "i_handoff": result.dimensions.i_handoff,
                "i_role": result.dimensions.i_role,
                "b_length": result.dimensions.b_length,
                "b_error": result.dimensions.b_error,
                "b_human": result.dimensions.b_human,
            },
            "window_size": result.window_size,
            "evaluated_at": result.evaluated_at,
        }
        serialized = json.dumps(payload)

        # Current value (TTL 1h)
        r.set(key_current, serialized, ex=ASI_CACHE_TTL)

        # Append to 24h history ring (keep last 48 entries = every 30min over 24h)
        r.lpush(key_history, serialized)
        r.ltrim(key_history, 0, 47)
        r.expire(key_history, ASI_HISTORY_KEY_TTL)
    except Exception as exc:
        logger.debug("ASI Redis write failed: %s", exc)


def load_asi_result(workspace_id: str) -> Optional[Dict[str, Any]]:
    """Load the current ASI result from Redis."""
    r = _get_redis()
    if not r:
        return None
    try:
        key = f"veklom:asi:{workspace_id}:current"
        raw = r.get(key)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.debug("ASI Redis read failed: %s", exc)
    return None


def load_asi_history(workspace_id: str) -> List[Dict[str, Any]]:
    """Load the 24h ASI history ring from Redis."""
    r = _get_redis()
    if not r:
        return []
    try:
        key = f"veklom:asi:{workspace_id}:history"
        raw_list = r.lrange(key, 0, -1)
        return [json.loads(item) for item in raw_list]
    except Exception as exc:
        logger.debug("ASI history Redis read failed: %s", exc)
    return []


def get_consecutive_alert_windows(workspace_id: str) -> int:
    """Count consecutive windows where ASI_t < threshold in history."""
    history = load_asi_history(workspace_id)
    count = 0
    for entry in history:
        if entry.get("alert"):
            count += 1
        else:
            break
    return count


def store_cds_alert(session_a: str, session_b: str, cds: float, workspace_id: str) -> None:
    """Write a CDS drift alert to the VNP audit trail."""
    r = _get_redis()
    if not r:
        return
    try:
        event = {
            "type": "context.drift",
            "session_a": session_a,
            "session_b": session_b,
            "cds": cds,
            "workspace_id": workspace_id,
            "threshold": CDS_ALERT_THRESHOLD,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        }
        r.lpush("veklom:audit:cds", json.dumps(event))
        r.ltrim("veklom:audit:cds", 0, 4999)
    except Exception as exc:
        logger.debug("CDS alert write failed: %s", exc)


# ---------------------------------------------------------------------------
# Synthetic/baseline dimensions for workspaces without telemetry data
# ---------------------------------------------------------------------------

def baseline_dimensions() -> ASIDimensions:
    """
    Return conservative baseline dimensions for a workspace with no telemetry.
    All values set to 0.90 — slightly below perfect to indicate unverified state.
    """
    return ASIDimensions(
        c_sem=0.90, c_path=0.90, c_conf=0.90,
        t_sel=0.90, t_seq=0.90, t_param=0.90,
        i_agree=0.90, i_handoff=0.90, i_role=0.90,
        b_length=0.90, b_error=0.90, b_human=0.90,
    )


def evaluate_workspace_asi(workspace_id: str, dimensions: Optional[ASIDimensions] = None) -> ASIResult:
    """
    Compute and persist the ASI for a workspace.

    If no dimensions are provided, uses baseline (conservative defaults).
    In production, dimensions would be computed from real interaction logs.
    """
    dims = dimensions or baseline_dimensions()
    asi_t, quadrant_scores = compute_asi(dims)

    is_alert = asi_t < ASI_ALERT_THRESHOLD
    consecutive = get_consecutive_alert_windows(workspace_id) + (1 if is_alert else 0)

    result = ASIResult(
        workspace_id=workspace_id,
        asi_t=asi_t,
        dimensions=dims,
        window_size=ASI_WINDOW_SIZE,
        evaluated_at=datetime.now(tz=timezone.utc).isoformat(),
        alert=is_alert,
        consecutive_alert_windows=consecutive,
        quadrant_scores=quadrant_scores,
    )

    store_asi_result(result)
    return result
