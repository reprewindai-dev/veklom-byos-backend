"""Veklom Nexus Protocol — real benchmark scoring from ExecutionLog."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User

router = APIRouter(prefix="/nexus", tags=["Nexus Protocol"])

# VNP Threshold Definitions — the standard, never mocked
VNP_THRESHOLDS = {
    "latency_ms": 150,          # Max acceptable latency
    "throughput_tps": 50,       # Min acceptable tokens/sec
    "cost_per_inference_usdc": 0.05,  # Max acceptable cost
}


class CertificationRequest(BaseModel):
    api_name: str
    provider: str
    endpoint_url: str
    claimed_latency: int
    claimed_throughput: int


def _vnp_status(avg_latency: float, avg_cost: float) -> str:
    """Derive NEXUS-CERTIFIED or FAILING from real aggregated metrics."""
    if avg_latency <= VNP_THRESHOLDS["latency_ms"] and avg_cost <= VNP_THRESHOLDS["cost_per_inference_usdc"]:
        return "NEXUS-CERTIFIED"
    return "FAILING"


def _vnp_score(avg_latency: float, avg_cost: float, total_tokens: float) -> int:
    """Compute a 0-100 VNP score.
    Latency contributes 50 pts, cost 30 pts, throughput proxy 20 pts.
    """
    latency_score = max(0.0, 50.0 * (1.0 - avg_latency / 500.0))
    cost_score = max(0.0, 30.0 * (1.0 - avg_cost / 0.10))
    throughput_score = min(20.0, 20.0 * (total_tokens / 10000.0))
    return round(latency_score + cost_score + throughput_score)


@router.get("/standard")
async def nexus_standard():
    """Returns the official Veklom Nexus Protocol threshold definitions."""
    return {
        "standard": "veklom-nexus-v1",
        "thresholds": VNP_THRESHOLDS,
        "description": "Veklom Nexus Protocol sets the benchmark standard for sovereign AI agent API performance.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/benchmark")
async def nexus_benchmark():
    """Returns Veklom Nexus Protocol benchmark metadata."""
    return {
        "standard": "veklom-nexus-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/leaderboard")
async def nexus_leaderboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the real Nexus Protocol leaderboard aggregated from ExecutionLog."""
    try:
        from backend.db.models.ai import ExecutionLog

        result = await db.execute(
            select(
                ExecutionLog.model,
                func.avg(ExecutionLog.latency_ms).label("avg_latency"),
                func.avg(ExecutionLog.cost_usd).label("avg_cost"),
                func.sum(ExecutionLog.total_tokens).label("total_tokens"),
                func.count(ExecutionLog.id).label("total_requests"),
            )
            .where(ExecutionLog.status == "completed")
            .group_by(ExecutionLog.model)
            .order_by(func.avg(ExecutionLog.latency_ms).asc())
        )
        rows = result.all()

        if not rows:
            return {
                "leaderboard": {},
                "note": "No completed executions yet — leaderboard will populate as requests are processed.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        leaderboard: Dict[str, Any] = {}
        for row in rows:
            provider = row.model or "unknown"
            avg_latency = float(row.avg_latency or 0)
            avg_cost = float(row.avg_cost or 0)
            total_tokens = int(row.total_tokens or 0)
            score = _vnp_score(avg_latency, avg_cost, total_tokens)
            leaderboard[provider] = {
                "latency": round(avg_latency, 2),
                "cost": round(avg_cost, 6),
                "total_tokens": total_tokens,
                "total_requests": int(row.total_requests or 0),
                "score": score,
                "status": _vnp_status(avg_latency, avg_cost),
            }

        # Sort descending by score
        sorted_board = dict(
            sorted(leaderboard.items(), key=lambda x: x[1]["score"], reverse=True)
        )

        return {
            "leaderboard": sorted_board,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to aggregate leaderboard: {str(e)}")


@router.get("/score/{provider}")
async def nexus_score(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns real benchmark metrics for a specific provider from ExecutionLog."""
    try:
        from backend.db.models.ai import ExecutionLog

        result = await db.execute(
            select(
                func.avg(ExecutionLog.latency_ms).label("avg_latency"),
                func.avg(ExecutionLog.cost_usd).label("avg_cost"),
                func.sum(ExecutionLog.total_tokens).label("total_tokens"),
                func.count(ExecutionLog.id).label("total_requests"),
            )
            .where(
                and_(
                    ExecutionLog.model == provider.lower(),
                    ExecutionLog.status == "completed",
                )
            )
        )
        row = result.one_or_none()

        if not row or row.total_requests == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider}' not found in Nexus benchmark index — no completed executions recorded.",
            )

        avg_latency = float(row.avg_latency or 0)
        avg_cost = float(row.avg_cost or 0)
        total_tokens = int(row.total_tokens or 0)
        score = _vnp_score(avg_latency, avg_cost, total_tokens)

        return {
            "provider": provider.lower(),
            "nexus_standard": "veklom-nexus-v1",
            "metrics": {
                "latency": round(avg_latency, 2),
                "cost": round(avg_cost, 6),
                "total_tokens": total_tokens,
                "total_requests": int(row.total_requests),
                "score": score,
                "status": _vnp_status(avg_latency, avg_cost),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to score provider: {str(e)}")


@router.get("/providers")
async def nexus_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all providers that have completed executions in the DB."""
    try:
        from backend.db.models.ai import ExecutionLog

        result = await db.execute(
            select(ExecutionLog.model)
            .where(ExecutionLog.status == "completed")
            .distinct()
        )
        providers = [row[0] for row in result.all() if row[0]]
        return {"providers": providers}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list providers: {str(e)}")


@router.post("/certify")
async def nexus_certify(request: CertificationRequest):
    """Endpoint for third-party API submissions to be certified by VNP."""
    certified = (
        request.claimed_latency <= VNP_THRESHOLDS["latency_ms"]
        and request.claimed_throughput >= VNP_THRESHOLDS["throughput_tps"]
    )
    return {
        "submission_id": f"cert-{int(datetime.now(timezone.utc).timestamp())}",
        "api_name": request.api_name,
        "provider": request.provider,
        "status": "APPROVED" if certified else "REJECTED",
        "reason": (
            "Meets VNP standards"
            if certified
            else "Fails to meet VNP latency or throughput standards"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
