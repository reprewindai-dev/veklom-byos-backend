"""Deterministic runtime routing contract routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.runtime_contract import (
    ROUTING_POLICY_VERSION,
    classify_route,
    get_economic_pressure_model,
    get_operational_runtime_contract,
    get_routing_topology,
    get_stack_contract,
)
from backend.core.security.auth import get_current_user
from backend.core.security.entitlements import require_entitlement
from backend.services import smart_router as sr


router = APIRouter(
    prefix="/routing",
    tags=["Routing"],
    dependencies=[Depends(get_current_user), Depends(require_entitlement("starter"))],
)


class RoutingDecisionRequest(BaseModel):
    workload_class: Literal["interactive", "batch", "agent_chain", "retrieval", "verification"] = "interactive"
    estimated_tokens: int = Field(default=1000, ge=1, le=2_000_000)
    compliance_tags: list[str] = Field(default_factory=list, max_length=32)
    sovereignty_region: str | None = Field(default=None, max_length=64)
    max_latency_ms: int | None = Field(default=None, ge=1, le=600_000)
    budget_remaining_usd: float | None = Field(default=None, ge=0)
    requires_replay: bool = False


@router.get("")
async def routing_contract():
    """Return the deterministic infrastructure contract exposed by this backend."""
    contract = get_stack_contract()
    topology = get_routing_topology()
    return {
        "policy_version": ROUTING_POLICY_VERSION,
        "category": contract["category"],
        "thesis": contract["thesis"],
        "runtime_role": contract["repos"]["veklom-byos-backend"],
        "substrate_role": contract["repos"]["py03-irongrid"],
        "route_classes": topology["route_classes"],
        "non_negotiables": contract["non_negotiables"],
    }


@router.get("/topology")
async def routing_topology():
    """Return route classes, required inputs, and the py03-irongrid substrate contract."""
    return get_routing_topology()


@router.get("/economics")
async def routing_economics():
    """Return the infrastructure economics model behind deterministic routing."""
    return get_economic_pressure_model()


@router.get("/operational-runtime")
async def operational_runtime():
    """Return the governed operational runtime substrate contract."""
    return get_operational_runtime_contract()


@router.get("/stack")
async def stack_contract():
    """Return repo responsibility boundaries for Veklom, UACP, GPC, and py03-irongrid."""
    return get_stack_contract()


@router.post("/decision")
async def routing_decision(payload: RoutingDecisionRequest):
    """Classify a workload into a deterministic execution route."""
    route_class, reasons = classify_route(
        compliance_tags=payload.compliance_tags,
        max_latency_ms=payload.max_latency_ms,
        estimated_tokens=payload.estimated_tokens,
        sovereignty_region=payload.sovereignty_region,
    )
    topology = get_routing_topology()
    route = topology["route_classes"][route_class]
    controls = list(route["required_controls"])
    if payload.requires_replay and "evidence_capture" not in controls:
        controls.append("evidence_capture")

    return {
        "policy_version": ROUTING_POLICY_VERSION,
        "route_class": route_class,
        "substrate": topology["substrate"],
        "workload_class": payload.workload_class,
        "decision_reasons": reasons,
        "providers": route["providers"],
        "required_controls": controls,
        "replayable": True,
        "billing_required": True,
        "audit_required": True,
    }


class SmartRouteRequest(BaseModel):
    """Full requirement vector for the interpretable MCDM router."""
    security_clearance: int = Field(default=1, ge=1, le=3)
    estimated_tokens: int = Field(default=1000, ge=1, le=2_000_000)
    max_latency_ms: int = Field(default=600_000, ge=1, le=600_000)
    task_complexity: int = Field(default=5, ge=1, le=10)
    scores: dict[str, int] = Field(default_factory=dict)            # per-criterion 1..5 overrides
    weights: dict[str, float] | None = None                        # AHP weight override (governance lever)


def _req_from(user, body: SmartRouteRequest) -> "sr.RoutingRequirement":
    return sr.RoutingRequirement(
        workspace_id=getattr(user, "workspace_id", None) or "default",
        actor_id=str(getattr(user, "id", None) or "unknown"),
        security_clearance=body.security_clearance,
        estimated_tokens=body.estimated_tokens,
        max_latency_ms=body.max_latency_ms,
        task_complexity=body.task_complexity,
        scores=body.scores,
    )


@router.post("/select")
async def routing_select(
    body: SmartRouteRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Interpretable MCDM model selection (AHP + SAW + hard gates + risk-veto +
    confidence margin). Persists the decision to routing_decisions + a PGL ledger
    event so the choice is auditable back to weights and scores."""
    req = _req_from(user, body)
    return await sr.select_model(db, req, weights=body.weights)


@router.post("/test")
async def routing_test(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Manual-compatible model selection, now backed by the interpretable MCDM router.

    Maps the legacy `constraints.strategy` onto AHP criterion emphasis:
    cost_optimized -> cost, quality_optimized -> accuracy, speed_optimized -> time.
    """
    constraints = body.get("constraints", {})
    strategy = constraints.get("strategy", "cost_optimized")
    scores: dict[str, int] = {}
    if strategy == "cost_optimized":
        scores["cost"] = 5
    elif strategy == "quality_optimized":
        scores["accuracy"] = 5
    elif strategy == "speed_optimized":
        scores["time"] = 5
    req = sr.RoutingRequirement(
        workspace_id=getattr(user, "workspace_id", None) or "default",
        actor_id=str(getattr(user, "id", None) or "unknown"),
        estimated_tokens=int(body.get("estimated_tokens", 1000)),
        task_complexity=int(body.get("task_complexity", 5)),
        scores=scores,
    )
    result = await sr.select_model(db, req)
    if not result.get("selected_provider"):
        return {"selected_provider": None, "reasoning": result.get("reason", "no_viable_node"),
                "expected_cost": "0.000000", "alternatives_considered": result.get("rejected", [])}
    # Manual-contract shape (kept stable) + interpretable extras.
    return {
        "selected_provider": result["selected_provider"],
        "reasoning": result["reasoning"],
        "expected_cost": result["expected_cost"],
        "expected_quality_score": result["expected_quality_score"],
        "expected_latency_ms": result["expected_latency_ms"],
        "alternatives_considered": result["alternatives_considered"],
        "confidence": result["confidence"],
        "persisted": result.get("persisted", False),
    }
