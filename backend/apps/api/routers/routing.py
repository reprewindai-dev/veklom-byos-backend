"""Deterministic runtime routing contract routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

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
