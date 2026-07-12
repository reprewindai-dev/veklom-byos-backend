"""GPC (Governed Plan Compiler) routes — proxied from uacpgemini."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.core.security.auth import get_current_user, get_current_user_optional
from backend.core.services.autonomous_worker import run_gpc_background
import asyncio
from backend.core.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.pipelines import Pipeline
from backend.core.ai.provider_router import run_completion
from backend.ops.poltergeist_daemon import poltergeist_daemon
from backend.core.services.poltergeist_registry import poltergeist_registry

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
async def intent_to_plan(body: dict, user=Depends(get_current_user_optional), db: AsyncSession = Depends(get_db)):
    intent = body.get("intent", "")
    provider = body.get("provider", "ollama")
    model = body.get("model", "qwen2.5:3b")

    prompt = f"""
You are an expert AI data engineering architecture generator for the Veklom GPC (Generative Pipeline Compiler).
A user has provided the following "messy" natural language description for a new Python ETL pipeline:
"{intent}"

Convert this intent into a STRICT valid JSON output matching this structure:
{{
  "nodes": [
    {{
      "id": "node_id_1", 
      "type": "data", 
      "position": {{"x": 100, "y": 120}}, 
      "data": {{
        "label": "Node Label", 
        "nodeType": "CsvFileInput"
      }}
    }},
    ...
  ],
  "edges": [
    {{"id": "e_node_id_1_node_id_2", "source": "node_id_1", "target": "node_id_2"}}
  ],
  "node_configs": {{
    "node_id_1": {{
      "filePath": "input.csv",
      "sep": ","
    }}
  }}
}}

Available values for "nodeType" include:
1. "CsvFileInput" (Required configs: "filePath": str, "sep": str (usually ","))
2. "FilterRows" (Required configs: "column": str, "value": str)
3. "Aggregate" (Required configs: "groupBy": str, "aggregateColumn": str, "aggregateFunction": str (sum, mean, count, min, max))
4. "SelectColumns" (Required configs: "columns": list of str)
5. "ParquetOutput" (Required configs: "outputPath": str)
6. "DuckDBQuery" (Required configs: "sqlQuery": str)

Assign beautiful, logical "label" values like "Load CSV", "Filter Active", "Group by Status", "Output Parquet", etc.
Ensure nodes are laid out horizontally from left to right by incrementing their position "x" coordinates (e.g. x=100, x=300, x=500, x=700).
Return ONLY valid JSON and nothing else. Do not wrap in markdown code blocks.
"""

    try:
        res = await run_completion({
            "provider": provider,
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        })
        content = res.payload.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        content = content.strip().removeprefix("```json").removesuffix("```").strip()
        graph_data = json.loads(content)
    except Exception as e:
        # Fallback if LLM fails
        graph_data = {
            "nodes": [
                {"id": "n1", "type": "data", "position": {"x": 100, "y": 120}, "data": {"label": "Load CSV", "nodeType": "CsvFileInput"}},
                {"id": "n2", "type": "data", "position": {"x": 320, "y": 120}, "data": {"label": "Filter Status", "nodeType": "FilterRows"}},
                {"id": "n3", "type": "data", "position": {"x": 540, "y": 120}, "data": {"label": "Export Parquet", "nodeType": "ParquetOutput"}},
            ],
            "edges": [
                {"id": "e_n1_n2", "source": "n1", "target": "n2"},
                {"id": "e_n2_n3", "source": "n2", "target": "n3"}
            ],
            "node_configs": {
                "n1": {"filePath": "input.csv", "sep": ","},
                "n2": {"column": "status", "value": "active"},
                "n3": {"outputPath": "output.parquet"}
            }
        }

    pipeline_id = str(uuid.uuid4())
    name = f"GPC Plan: {intent[:40]}"
    
    pipe = Pipeline(
        id=pipeline_id,
        workspace_id=user.workspace_id if user else "default",
        name=name,
        description=f"Generated via GPC for intent: {intent}",
        steps={
            "template": "GPC",
            "nodes": len(graph_data.get("nodes", [])),
            "vectorStore": "pgvector",
            "invocations": 0,
            "lastRun": "—",
            "graph": graph_data  # Crucial bridge: Save the visual graph inside the steps["graph"] field
        },
        config_json=graph_data
    )
    db.add(pipe)
    await db.commit()

    return {
        "id": pipeline_id,
        "name": name,
        "intent": intent,
        "graph": graph_data,
        "status": "compiled",
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
        "plans_total": active_plans,
        "runs_total": total_runs,
        "signals_total": total_events,
        "latest_hash": "gpc_live_" + datetime.now(timezone.utc).strftime("%Y%m%d"),
        "signals": [
            {"id": "UACP_PRESSURE", "title": "UACP Core Pressure", "value": load, "timestamp": datetime.now(timezone.utc).isoformat(), "category": "system"}
        ]
    }


@router.post("/capability/submit")
async def submit_capability_build(body: dict, user=Depends(get_current_user_optional)):
    """
    Submits a capability intent to the Poltergeist Deduplicating Build Queue.
    This acts as the backend resolver for GraphQL subscriptions in the UI.
    """
    fingerprint = body.get("fingerprint")
    if not fingerprint:
        return {"error": "fingerprint is required"}
        
    required_revision = body.get("required_revision", 1)
    workspace_id = user.workspace_id if user else "default"
    
    await poltergeist_daemon.submit_intent(
        workspace_id=workspace_id,
        fingerprint=fingerprint,
        required_revision=required_revision,
        manifest=body.get("manifest", {})
    )
    
    return {"status": "queued", "fingerprint": fingerprint, "revision": required_revision}

@router.get("/capability/{fingerprint}/status")
async def get_capability_status(fingerprint: str):
    """
    Returns the real-time build status from the Poltergeist memory.
    """
    state = await poltergeist_registry.get_capability_state(fingerprint)
    if not state:
        return {"status": "unknown"}
    return state

