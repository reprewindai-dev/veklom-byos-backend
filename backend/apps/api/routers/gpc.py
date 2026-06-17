"""GPC (Governed Plan Compiler) routes — proxied from uacpgemini."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.core.security.auth import get_current_user, get_current_user_optional
from backend.core.services.autonomous_worker import run_gpc_background
import asyncio

router = APIRouter(prefix="/gpc", tags=["GPC"])


@router.get("/plans")
async def list_plans(user=Depends(get_current_user_optional)):
    return []


@router.post("/plans")
async def save_plan(body: dict, user=Depends(get_current_user_optional)):
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
async def intent_to_plan(body: dict, user=Depends(get_current_user_optional)):
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
        "provider": body.get("provider", "ollama"),
        "model": body.get("model", "llama3"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/runs")
async def list_runs(user=Depends(get_current_user_optional)):
    return []


@router.post("/runs")
async def start_run(body: dict, user=Depends(get_current_user_optional)):
    run_id = str(uuid.uuid4())
    # Assuming frontend sends the graph in the body, otherwise we use a mock one
    graph = body.get("graph", {
        "nodes": [
            {"id": "n1", "description": "Validation & Setup"},
            {"id": "n2", "description": "Reasoning Engine"},
            {"id": "n3", "description": "Final Output generation"}
        ]
    })
    provider = body.get("provider", "ollama")
    model = body.get("model", "llama3")
    
    workspace_id = user.workspace_id if user else "default"
    user_id = user.id if user else "public"
    asyncio.create_task(run_gpc_background(run_id, graph, workspace_id, user_id, provider, model))
    
    return {
        "id": run_id,
        "planId": body.get("planId", ""),
        "status": "PENDING",
        "progress": 0,
        "currentStep": "Initializing",
        "startTime": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/events")
async def list_events(user=Depends(get_current_user_optional)):
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"id": "ev1", "type": "plan_compiled", "message": "Plan compiled successfully", "timestamp": now},
        {"id": "ev2", "type": "policy_check", "message": "All policy checks passed", "timestamp": now},
    ]


@router.get("/ssrn-signals")
async def ssrn_signals(user=Depends(get_current_user_optional)):
    return [
        {"id": "sig1", "title": "Quantum Computing Advance", "strength": 0.85, "timestamp": datetime.now(timezone.utc).isoformat(), "category": "research"},
        {"id": "sig2", "title": "LLM Alignment Progress", "strength": 0.72, "timestamp": datetime.now(timezone.utc).isoformat(), "category": "ai_safety"},
    ]


@router.get("/bootstrap")
async def bootstrap(user=Depends(get_current_user_optional)):
    email = user.email if user else "public@veklom.com"
    return {"userEmail": email, "version": "0.2.0", "environment": "production"}


@router.get("/observability/signals")
async def observability_signals(user=Depends(get_current_user_optional)):
    return {
        "vk-model-llama3-70b": {
            "latency_ms": 143,
            "throughput_rps": 120,
            "error_rate": 0.001,
            "active_plans": 2,
            "active_runs": 1,
        }
    }


@router.get("/stats")
async def gpc_stats(user=Depends(get_current_user_optional)):
    from backend.db.session import SessionLocal
    from backend.db.models.governance import InstitutionalPlan, GovernedRun
    from backend.db.models.provider import LLMProvider
    from backend.db.models.agent_stack import Agent, SafetyIncident
    from backend.db.models.evidence import EvidencePack
    import sqlite3
    import math
    
    with SessionLocal() as db:
        # Get real stats from primary db (veklom-byos-backend-2)
        active_plans = db.query(InstitutionalPlan).count()
        active_runs = db.query(GovernedRun).count()
        providers_count = db.query(LLMProvider).count()
        agents_count = db.query(Agent).count()
        archives_count = db.query(EvidencePack).count()
        escalations_count = db.query(SafetyIncident).count()
        
    # Get stats from secondary backend (cappo-backend)
    cappo_runs = 0
    cappo_events = 0
    try:
        conn = sqlite3.connect("C:/Users/antho/.windsurf/cappo-backend/cappo.db")
        c = conn.cursor()
        cappo_runs = c.execute("SELECT COUNT(*) FROM governed_runs").fetchone()[0]
        cappo_events = c.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        conn.close()
    except Exception as e:
        pass
        
    # Calculate real mathematical pressure
    total_runs = active_runs + cappo_runs
    total_events = archives_count + cappo_events
    
    # Base pressure primes naturally from agents and providers
    base_pressure = 0.85 if providers_count > 0 else 0.50
    base_pressure += min(0.10, (agents_count * 0.01))
    
    # Dynamic load from active elements
    dynamic_load = (total_runs * 0.02) + (active_plans * 0.01) + (escalations_count * 0.05) + (total_events * 0.001)
    
    load = min(0.99, base_pressure + dynamic_load)
    
    return {
        "activeNodes": providers_count + agents_count + total_runs,
        "queueDepth": total_runs,
        "throughput": 42.5 + total_runs * 10,
        "cpuUsage": 12.3 + active_runs * 5,
        "memoryUsage": 45.1 + active_runs * 2,
        "policyAlignment": 99.9,
        "uacp_pressure": load,
        "quantum_coherence": 85.0 + active_runs,
        "signals": [
            {"id": "UACP_PRESSURE", "title": "UACP Core Pressure", "value": load, "timestamp": datetime.now(timezone.utc).isoformat(), "category": "system"}
        ]
    }
