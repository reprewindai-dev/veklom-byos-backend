"""Veklom Nexus Protocol — real benchmark scoring from ExecutionLog."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import hashlib

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
from backend.db.models.vnp import Api, RegionalTelemetry, ProbeEvent

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


from pydantic import Field
import uuid
from backend.core.services.seked_service import seked_service
from backend.db.models.benchmarks import NexusBenchmarkRun

class BenchmarkEvaluationRequest(BaseModel):
    agent_id: str
    provider: str
    policy_adherence_score: float = Field(..., ge=0, le=100)
    evidence_integrity_score: float = Field(..., ge=0, le=100)
    latency_ms: float = Field(..., ge=0)
    cost_efficiency_score: float = Field(..., ge=0, le=100)

class BenchmarkEvaluationResponse(BaseModel):
    run_id: str
    overall_score: float
    status: str
    privilege_revoked: bool
    message: str

# Configurable threshold for dynamic revocation
DYNAMIC_REVOCATION_THRESHOLD = 70.0

@router.post("/benchmark/evaluate", response_model=BenchmarkEvaluationResponse)
async def evaluate_benchmark(
    request: BenchmarkEvaluationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluates an agent's benchmark run and dynamically revokes privileges 
    if the score falls below the VNP threshold.
    """
    # 1. Calculate overall score (weighted average)
    latency_score = max(0.0, 100.0 - ((request.latency_ms / 2000.0) * 100)) # Simple mapping for score
    
    overall_score = (
        (request.policy_adherence_score * 0.4) +
        (request.evidence_integrity_score * 0.4) +
        (request.cost_efficiency_score * 0.2)
    ) - max(0, (request.latency_ms - 2000) / 100)
    
    overall_score = max(0.0, min(100.0, overall_score))
    
    privilege_revoked = False
    run_status = "passed"
    message = "Agent benchmark passed successfully."
    
    # Check hard floors and composite
    if overall_score < DYNAMIC_REVOCATION_THRESHOLD or request.policy_adherence_score < 80.0 or request.evidence_integrity_score < 90.0:
        run_status = "revoked"
        privilege_revoked = True
        
        if overall_score < DYNAMIC_REVOCATION_THRESHOLD:
            reason = f"Composite score {overall_score:.2f} is below the {DYNAMIC_REVOCATION_THRESHOLD} threshold."
        elif request.policy_adherence_score < 80.0:
            reason = f"Policy adherence score {request.policy_adherence_score:.2f} is below the 80.0 critical floor."
        else:
            reason = f"Evidence integrity score {request.evidence_integrity_score:.2f} is below the 90.0 critical floor."
            
        message = f"Privileges revoked: {reason}"
        
        # We need a run_id first to pass to SEKED
        run_id = f"nbm_{uuid.uuid4().hex[:12]}"
        
        await seked_service.revoke_agent_privileges(
            db=db,
            agent_id=request.agent_id,
            provider=request.provider,
            reason=message,
            run_id=run_id
        )
    elif overall_score < 80.0:
        run_status = "degraded"
        message = f"Agent benchmark degraded. Score: {overall_score:.2f}."
        run_id = f"nbm_{uuid.uuid4().hex[:12]}"
    else:
        run_id = f"nbm_{uuid.uuid4().hex[:12]}"
        
    run_record = NexusBenchmarkRun(
        id=run_id,
        agent_id=request.agent_id,
        provider=request.provider,
        policy_adherence_score=request.policy_adherence_score,
        evidence_integrity_score=request.evidence_integrity_score,
        latency_score=latency_score,
        cost_efficiency_score=request.cost_efficiency_score,
        composite_score=overall_score,
        threshold_used=DYNAMIC_REVOCATION_THRESHOLD,
        result_state=run_status,
        triggered_revocation=privilege_revoked,
        evaluation_reason=message
    )
    db.add(run_record)
    await db.commit()
    
    return BenchmarkEvaluationResponse(
        run_id=run_record.id,
        overall_score=overall_score,
        status=run_status,
        privilege_revoked=privilege_revoked,
        message=message
    )

@router.get("/agent/{agent_id}/privilege")
async def get_agent_privilege(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Check the current privilege status of an agent."""
    is_active = await seked_service.check_agent_privilege(db, agent_id)
    return {"agent_id": agent_id, "is_active": is_active}

@router.get("/scores")
async def get_nexus_scores(db: AsyncSession = Depends(get_db)):
    """
    Returns API ScoreCards for the NexusProtocol UI.
    Queries vnp_apis and RegionalTelemetry dynamically.
    """
    stmt = select(Api).where(Api.status == "active")
    result = await db.execute(stmt)
    apis = result.scalars().all()

    # Dimension definitions with weights
    dimension_defs = [
        ("Performance",      15, "p50/p95 response latency across probe regions"),
        ("Reliability",      15, "HTTP 200 uptime consistency over 30d window"),
        ("Security Posture", 10, "TLS configuration, security headers, auth strength"),
        ("SLA Compliance",   10, "Acceptable boundary conformance per signed SLA"),
        ("Cost Efficiency",  10, "Effective cost per 1K governed requests"),
        ("Data Integrity",   10, "Schema validation, payload accuracy & type fidelity"),
        ("Governance",       10, "Policy adherence under Zero-Trust middleware"),
        ("Auditability",      8, "Log completeness, traceability and receipt coverage"),
        ("Resilience",        7, "Mean recovery time and retry success rate under load"),
        ("Interoperability",  5, "OpenAPI, x402 settlement, CORS standards compliance"),
    ]

    scorecards = []
    for api in apis:
        api_id_str = str(api.id)
        
        # Get actual telemetry from DB
        telemetry_stmt = select(RegionalTelemetry).where(RegionalTelemetry.api_id == api.id).order_by(RegionalTelemetry.measured_at.desc()).limit(1)
        tel_result = await db.execute(telemetry_stmt)
        latest_telemetry = tel_result.scalar_one_or_none()
        
        if latest_telemetry:
            # Map real DB metrics to 0-100 scales
            perf_score = max(0, 100 - (latest_telemetry.p99_latency_ms / 10))
            rel_score = float(latest_telemetry.uptime_percent)
            composite = float(latest_telemetry.trust_score)
            anchor_hash = latest_telemetry.on_chain_anchor or "0xPENDING"
            tx_hash = latest_telemetry.provenance_hash or "0xPENDING"
        else:
            perf_score = api.current_composite_score
            rel_score = api.current_composite_score
            composite = api.current_composite_score
            anchor_hash = "0xPENDING"
            tx_hash = "0xPENDING"

        dimensions = []
        weighted_sum = 0.0
        total_weight = 0

        for i, (name, weight, desc) in enumerate(dimension_defs):
            if name == "Performance":
                dim_score = perf_score
            elif name == "Reliability":
                dim_score = rel_score
            else:
                dim_score = composite # Fallback for unmeasured dimensions
                
            dim_score = max(0, min(100, int(dim_score)))
            dimensions.append({
                "name": name,
                "score": dim_score,
                "weight": weight,
                "desc": desc,
            })
            weighted_sum += dim_score * weight
            total_weight += weight

        overall = round(weighted_sum / total_weight) if total_weight else int(composite)
        grade = _nexus_grade(overall)

        scorecards.append({
            "id": api_id_str,
            "name": api.name,
            "provider": api_id_str.split("-")[0] if api.name else "Unknown",
            "score": overall,
            "grade": grade,
            "dimensions": dimensions,
            "anchorHash": anchor_hash,
            "txHash": tx_hash,
            "blockNumber": latest_telemetry.block_number if latest_telemetry else None,
            "chainId": latest_telemetry.chain_id if latest_telemetry else None,
            "contractAddress": latest_telemetry.contract_address if latest_telemetry else None,
            "confirmationState": latest_telemetry.confirmation_state if latest_telemetry else "pending",
            "lastUpdated": _time_ago(api.updated_at) if hasattr(api, "updated_at") and api.updated_at else "—",
        })

    # Fetch the latest on_chain_anchor across all telemetry for the network-wide beacon
    global_telemetry_stmt = select(RegionalTelemetry).where(RegionalTelemetry.on_chain_anchor.isnot(None)).order_by(RegionalTelemetry.measured_at.desc()).limit(1)
    global_tel_result = await db.execute(global_telemetry_stmt)
    latest_global_tel = global_tel_result.scalar_one_or_none()

    trust_beacon_merkle = latest_global_tel.on_chain_anchor if latest_global_tel else None
    
    # Never display Verified from a non-null Merkle root alone
    confirmed = (latest_global_tel and latest_global_tel.confirmation_state == "confirmed")
    block_anchored = 1 if confirmed else 0

    return {
        "apis": scorecards,
        "trustBeaconMerkle": trust_beacon_merkle,
        "trustBeaconStatus": "Anchored to Base L2" if confirmed else "Needs proof",
        "blockAnchored": block_anchored,
        "blockAnchoredStatus": "Verified" if confirmed else "Needs proof",
        "blockNumber": latest_global_tel.block_number if latest_global_tel else None,
        "chainId": latest_global_tel.chain_id if latest_global_tel else None,
        "contractAddress": latest_global_tel.contract_address if latest_global_tel else None,
    }


def _nexus_grade(score: int) -> str:
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    return "F"


def _time_ago(dt) -> str:
    if not dt:
        return "—"
    now = datetime.now(timezone.utc)
    diff = now - dt
    minutes = int(diff.total_seconds() / 60)
    if minutes < 1:
        return "just now"
    elif minutes < 60:
        return f"{minutes}m ago"
    elif minutes < 1440:
        return f"{minutes // 60}h ago"
    return f"{minutes // 1440}d ago"


@router.get("/nodes")
async def get_nexus_nodes(db: AsyncSession = Depends(get_db)):
    from backend.db.models.vnp import ApiRegion
    stmt = select(ApiRegion).where(ApiRegion.active == True)
    result = await db.execute(stmt)
    regions = result.scalars().all()
    
    nodes = []
    for idx, r in enumerate(regions):
        nodes.append({
            "id": r.region_code,
            "name": f"Node-{idx+1:02d} // {r.region_code.upper()}",
            "region": r.region_code,
            "latency": 0, # Will be updated by real probes
            "throughput": 0,
            "status": "active",
            "activeCycles": 1
        })
    return nodes
