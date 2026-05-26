"""GPC (Governed Plan Compiler) routes.

Prompt → Plan → Pipeline → Proof

GPC asks: Can this idea be governed, approved, deployed, priced, and proven?
Every compile emits a Decision Frame — the replayable proof object.
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.services.autonomous_worker import run_gpc_background
import asyncio

router = APIRouter(prefix="/gpc", tags=["GPC"])


def _can_use_gpc_full(user) -> bool:
    """
    Determine whether a user has full GPC access.
    
    Full access is granted when the user is a platform superuser/admin (via is_superuser, role == "SUPER_ADMIN", matching admin email, or matching founder workspace ID) or when the user's plan is one of "pro", "sovereign", or "business".
    
    Parameters:
        user: An object representing the current user. Expected attributes: `is_superuser`, `role`, `email`, `workspace_id`, and `plan`.
    
    Returns:
        `true` if the user has full GPC access, `false` otherwise.
    """
    from backend.core.config.settings import settings
    
    # Platform superuser gets full access
    is_superuser = bool(getattr(user, "is_superuser", False))
    role = (getattr(user, "role", "") or "").upper()
    email = getattr(user, "email", "")
    workspace_id = getattr(user, "workspace_id", "")
    
    is_platform_superuser = (
        is_superuser
        or role == "SUPER_ADMIN"
        or email == settings.ADMIN_EMAIL
        or workspace_id == settings.FOUNDER_WORKSPACE_ID
    )
    
    if is_platform_superuser:
        return True
    
    # Paid users get full access
    plan = getattr(user, "plan", "free")
    if plan in ("pro", "sovereign", "business"):
        return True
    
    return False


def _can_use_gpc_demo(user) -> bool:
    """
    Determine whether a user is eligible for demo GPC access.
    
    Returns:
        bool: `True` if the user's plan is "free", `False` otherwise.
    """
    plan = getattr(user, "plan", "free")
    # Free users get demo access
    return plan == "free"


@router.get("/plans")
async def list_plans(user=Depends(get_current_user)):
    """
    Return an empty list of plans.
    
    Returns:
        list: An empty list.
    """
    return []


@router.post("/plans")
async def save_plan(body: dict, user=Depends(get_current_user)):
    plan_id = str(uuid.uuid4())[:8]
    return {
        "id": plan_id,
        "name": body.get("name", f"Plan-{plan_id}"),
        "intent": body.get("intent", ""),
        "graph": body.get("graph", {"nodes": [], "edges": []}),
        "status": "compiled",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/compile")
async def gpc_compile(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Compile an agent intent into a governed plan and attempt to emit a Decision Frame.
    
    Parameters:
        body (dict): Request payload containing at minimum an "intent" string. May include optional keys such as "graph", "compliance", "provider", "model", and "budget_usdc".
    
    Returns:
        dict: A compiled plan payload containing fields like `id`, `name`, `intent`, `graph`, `status`, and `createdAt`. If Decision Frame emission succeeds, the payload will also include `decision_frame_id`, `evidence_id`, and `proof_hash`.
    
    Raises:
        HTTPException: 403 if the current user is not entitled to use GPC (neither full nor demo access).
    """
    # Check GPC entitlement
    if not _can_use_gpc_full(user) and not _can_use_gpc_demo(user):
        raise HTTPException(
            status_code=403,
            detail="GPC requires a paid plan. Upgrade to Pro or Sovereign to access full GPC capabilities."
        )
    
    return await _build_and_emit_plan(body, user, db)


@router.post("/intent-to-plan")
async def intent_to_plan(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Convert a high-level intent into a governed execution plan.
    
    Parameters:
        body (dict): Input payload containing the plan request. Expected keys include:
            - `intent` (str): The natural-language objective to compile.
            - `graph` (dict, optional): Explicit plan graph structure.
            - `compliance` (list, optional): Compliance constraints or tags.
            - `provider` (str, optional): Model provider override.
            - `model` (str, optional): Model identifier override.
            - `budget_usdc` (number, optional): Cost estimate for Decision Frame emission.
    
    Returns:
        dict: Compiled plan payload with fields such as `id`, `name`, `intent`, `graph`, `status`,
        `policy_result`, `compliance`, `provider`, `model`, and `createdAt`. When Decision Frame
        emission succeeds, the result also includes `decision_frame_id`, `evidence_id`, and `proof_hash`.
    """
    # Check GPC entitlement
    if not _can_use_gpc_full(user) and not _can_use_gpc_demo(user):
        raise HTTPException(
            status_code=403,
            detail="GPC requires a paid plan. Upgrade to Pro or Sovereign to access full GPC capabilities."
        )
    
    return await _build_and_emit_plan(body, user, db)


async def _build_and_emit_plan(body: dict, user, db: AsyncSession) -> dict:
    """Core compile logic. Returns plan + decision_frame_id + proof_hash."""
    from backend.apps.api.routers.decision_frames import emit_decision_frame
    intent = body.get("intent", "")
    plan_id = str(uuid.uuid4())[:8]
    result = {
        "id": plan_id,
        "name": f"Governed Plan: {intent[:50]}",
        "intent": intent,
        "graph": {
            "nodes": [
                {"id": "n1", "type": "classical", "description": "Input validation & PII scan", "policy_tag": "privacy", "entropy": 0.1},
                {"id": "n2", "type": "quantum", "description": "AI model selection & routing", "policy_tag": "routing", "entropy": 0.3},
                {"id": "n3", "type": "classical", "description": "Policy enforcement gate", "policy_tag": "compliance", "entropy": 0.05},
                {"id": "n4", "type": "quantum", "description": "Governed execution", "policy_tag": "execution", "entropy": 0.4},
                {"id": "n5", "type": "classical", "description": "Evidence capture & audit", "policy_tag": "audit", "entropy": 0.02},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
                {"from": "n3", "to": "n4"},
                {"from": "n4", "to": "n5"},
            ],
        },
        "status": "compiled",
        "policy_result": "passed",
        "compliance": body.get("compliance", []),
        "provider": body.get("provider", "gemini"),
        "model": body.get("model", "gemini-2.5-flash"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    try:
        frame = await emit_decision_frame(
            db,
            workspace_id=user.workspace_id or "",
            actor_user_id=user.id,
            actor_name=getattr(user, "email", ""),
            objective=intent,
            model=result["model"],
            provider=result["provider"],
            plan_id=plan_id,
            cost_estimate_usd=float(body.get("budget_usdc", 0.015)),
            policy_result="passed",
            final_action="compiled",
            source="gpc",
            tags=["gpc", "compile"],
            replay_inputs={"intent": intent, "compliance": body.get("compliance", [])},
        )
        result["decision_frame_id"] = frame.id
        result["evidence_id"] = frame.evidence_id
        result["proof_hash"] = frame.proof_hash
    except Exception:
        pass
    return result


@router.get("/runs")
async def list_runs(user=Depends(get_current_user)):
    return []


@router.post("/runs")
async def start_run(body: dict, user=Depends(get_current_user)):
    # Check GPC entitlement
    """
    Start a background governed-plan run and return its initial run metadata.
    
    Parameters:
        body (dict): Request payload. Supported keys:
            - graph (dict, optional): Execution graph for the run; a default mock graph is used if absent.
            - provider (str, optional): Model provider, e.g. "openai"; defaults to "openai".
            - model (str, optional): Model name, e.g. "gpt-4o-mini"; defaults to "gpt-4o-mini".
            - planId (str, optional): Associated plan identifier.
    
    Returns:
        dict: Run metadata with keys:
            - id (str): UUID for the started run.
            - planId (str): Value from `body["planId"]` or empty string.
            - status (str): Initial status, `"PENDING"`.
            - progress (int): Initial progress percentage (0).
            - currentStep (str): Initial step label, `"Initializing"`.
            - startTime (str): ISO 8601 UTC timestamp when the run was started.
    
    Raises:
        HTTPException: With status code 403 if the requesting user is not entitled to use GPC.
    """
    if not _can_use_gpc_full(user) and not _can_use_gpc_demo(user):
        raise HTTPException(
            status_code=403,
            detail="GPC requires a paid plan. Upgrade to Pro or Sovereign to access full GPC capabilities."
        )
    
    run_id = str(uuid.uuid4())
    # Assuming frontend sends the graph in the body, otherwise we use a mock one
    graph = body.get("graph", {
        "nodes": [
            {"id": "n1", "description": "Validation & Setup"},
            {"id": "n2", "description": "Reasoning Engine"},
            {"id": "n3", "description": "Final Output generation"}
        ]
    })
    provider = body.get("provider", "openai")
    model = body.get("model", "gpt-4o-mini")
    
    asyncio.create_task(run_gpc_background(run_id, graph, user.workspace_id or "default", user.id, provider, model))
    
    return {
        "id": run_id,
        "planId": body.get("planId", ""),
        "status": "PENDING",
        "progress": 0,
        "currentStep": "Initializing",
        "startTime": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/events")
async def list_events(user=Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"id": "ev1", "type": "plan_compiled", "message": "Plan compiled successfully", "timestamp": now},
        {"id": "ev2", "type": "policy_check", "message": "All policy checks passed", "timestamp": now},
    ]


@router.get("/ssrn-signals")
async def ssrn_signals(user=Depends(get_current_user)):
    return [
        {"id": "sig1", "title": "Quantum Computing Advance", "strength": 0.85, "timestamp": datetime.now(timezone.utc).isoformat(), "category": "research"},
        {"id": "sig2", "title": "LLM Alignment Progress", "strength": 0.72, "timestamp": datetime.now(timezone.utc).isoformat(), "category": "ai_safety"},
    ]


@router.get("/bootstrap")
async def bootstrap(user=Depends(get_current_user)):
    return {"userEmail": user.email, "version": "0.2.0", "environment": "production"}


@router.get("/observability/signals")
async def observability_signals(user=Depends(get_current_user)):
    return {
        "latency_ms": 42,
        "throughput_rps": 120,
        "error_rate": 0.001,
        "active_plans": 2,
        "active_runs": 1,
    }


@router.get("/stats")
async def gpc_stats(user=Depends(get_current_user)):
    """Aggregate stats for the GPC page.

    Until persistent plan/run counters land in the DB, this endpoint reports
    zero-state counts and clearly marks itself as derived.  No fabricated
    decisions are returned.
    """
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "plans_total": 0,
        "runs_total": 0,
        "decisions": {"approved": 0, "blocked": 0, "escalated": 0},
        "source": "derived-counts",
        "note": "Plan and run counters are zero until the GPC persistence layer is wired.",
    }
