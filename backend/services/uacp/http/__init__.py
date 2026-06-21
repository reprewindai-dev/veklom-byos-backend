"""UACP HTTP Service - FastAPI service with auth guards and replay cache."""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from backend.services.uacp.core import UACPDecisionKernel
from backend.core.services.redis_cache import redis_cache
from backend.core.security.auth import get_current_user
from backend.core.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.db.models.ai import ExecutionLog
from backend.db.models.billing import BudgetRule

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uacp", tags=["UACP"])


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------

class DecideRequest(BaseModel):
    input: Dict[str, Any]
    trace_id: Optional[str] = None
    workspace_id: str


class DecideResponse(BaseModel):
    decision: Dict[str, Any]
    latency_ms: float
    quota: Dict[str, Any]
    observability: Dict[str, Any]


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------

def enforce_aud(token_claims: dict, expected: str = "veklom.uacp") -> None:
    """
    Enforce aud claim in JWT token.

    Args:
        token_claims: JWT claims dictionary
        expected: Expected aud value

    Raises:
        HTTPException: If aud is missing or incorrect
    """
    aud = token_claims.get("aud")
    if aud != expected:
        logger.warning(f"Invalid aud: {aud} (expected {expected})")
        raise HTTPException(status_code=401, detail="invalid aud")


async def check_replay(jti: str, trace_id: str) -> bool:
    """
    Check for replay attack using Redis cache.

    Args:
        jti: JWT ID
        trace_id: Trace identifier

    Returns:
        True if first time, False if replay detected

    Raises:
        HTTPException: If replay detected
    """
    key = f"replay:{jti}"

    # Try to set key (only succeeds if not exists)
    if await redis_cache.set(key, trace_id, ttl=900):  # 15 minutes
        return True
    else:
        logger.warning(f"Replay detected for jti: {jti}")
        raise HTTPException(status_code=409, detail="replay detected")


# ---------------------------------------------------------------------------
# Decision endpoint
# ---------------------------------------------------------------------------

@router.post("/v1/decide")
async def decide(
    request: DecideRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    UACP decision endpoint with auth guards and replay protection.

    Auth: Bearer <JWT with sub, jti, aud=veklom.uacp>
    Body: { "input": {...}, "trace_id": "...", "workspace_id": "..." }
    Resp: { "decision": {...}, "latency_ms": n,
            "quota": {...}, "observability": {...} }
    """
    start_time = time.time()

    # Extract JWT claims for auth enforcement
    token_claims = getattr(user, "claims", {})
    jti = token_claims.get("jti")
    sub = token_claims.get("sub")

    if not jti:
        raise HTTPException(status_code=401, detail="missing jti")

    # Enforce aud claim
    enforce_aud(token_claims, expected="veklom.uacp")

    # Check replay
    trace_id = request.trace_id or \
        f"trace_{datetime.now(timezone.utc).timestamp()}"
    await check_replay(jti, trace_id)

    # Extract plan components
    intent = request.input.get("intent", {})
    v2_plan = request.input.get("v2_plan", {})
    v3_context = request.input.get("v3_context", {})

    # Evaluate decision using core kernel
    kernel = UACPDecisionKernel()
    result = kernel.evaluate(
        intent, v2_plan, v3_context, request.workspace_id, trace_id
    )

    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000

    # Calculate quota tracking
    try:

        now = datetime.now(timezone.utc)
        month_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        if month_start.month == 12:
            next_month_start = month_start.replace(
                year=month_start.year + 1, month=1
            )
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)

        spend = await db.scalar(
            select(func.coalesce(func.sum(ExecutionLog.cost), 0.0))
            .where(
                ExecutionLog.workspace_id == request.workspace_id,
                ExecutionLog.created_at >= month_start
            )
        ) or 0.0

        budget = await db.scalar(
            select(BudgetRule.limit_usd)
            .where(
                BudgetRule.workspace_id == request.workspace_id,
                BudgetRule.is_active.is_(True)
            )
        )

        budget_limit = float(budget) if budget else 150.0
        remaining = max(0.0, budget_limit - float(spend))
        reset_at = next_month_start.isoformat()
    except Exception as e:
        logger.error(f"Failed to calculate quota: {e}")
        remaining = 1000.0
        reset_at = "2026-05-29T00:00:00Z"

    # Build response
    response = DecideResponse(
        decision=result.to_dict(),
        latency_ms=latency_ms,
        quota={
            "remaining": remaining,
            "reset_at": reset_at
        },
        observability={
            "trace_id": trace_id,
            "jti": jti,
            "sub": sub,
            "decision_hash": result.audit_hash,
            "workspace_id": request.workspace_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Log structured observability data
    logger.info(
        f"[UACP HTTP] Decision: {result.decision} | "
        f"trace_id: {trace_id} | workspace_id: {request.workspace_id} | "
        f"latency_ms: {latency_ms:.2f} | jti: {jti}"
    )

    return response


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "uacp-http",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
