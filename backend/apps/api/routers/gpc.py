"""GPC (Governed Plan Compiler) routes — proxied from uacpgemini."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.core.security.auth import get_current_user
from backend.core.services.autonomous_worker import run_gpc_background
import asyncio

router = APIRouter(prefix="/gpc", tags=["GPC"])


@router.get("/plans")
async def list_plans(user=Depends(get_current_user)):
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


@router.post("/intent-to-plan")
async def intent_to_plan(body: dict, user=Depends(get_current_user)):
    intent = body.get("intent", "")
    plan_id = str(uuid.uuid4())[:8]
    return {
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
        "compliance": body.get("compliance", []),
        "provider": body.get("provider", "gemini"),
        "model": body.get("model", "gemini-3-flash-preview"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/runs")
async def list_runs(user=Depends(get_current_user)):
    return []


@router.post("/runs")
async def start_run(body: dict, user=Depends(get_current_user)):
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
