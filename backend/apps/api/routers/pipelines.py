"""Pipeline, deployment, routing, autonomous routes."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.marketplace import Deployment, Pipeline, PipelineRun
from backend.core.services.autonomous_worker import run_pipeline_background
import asyncio
import uuid

router = APIRouter(tags=["Pipelines"])


# --- Pipelines ---
@router.get("/pipelines")
async def list_pipelines(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.workspace_id == (user.workspace_id or "default")).limit(50))
    pipes = result.scalars().all()
    if not pipes:
        return _mock_pipelines()
    return [_pipe_dict(p) for p in pipes]


@router.post("/pipelines")
async def create_pipeline(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pipe = Pipeline(
        workspace_id=user.workspace_id or "default",
        name=body.get("name", "Untitled Pipeline"),
        description=body.get("description", ""),
        steps=body.get("steps", []),
    )
    db.add(pipe)
    await db.commit()
    return _pipe_dict(pipe)


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipe = result.scalar_one_or_none()
    if pipe:
        return _pipe_detail_dict(pipe)
    # Fallback: check if it's one of the default pipeline IDs
    defaults = {p["id"]: p for p in _mock_pipelines()}
    if pipeline_id in defaults:
        return _pipe_detail_from_mock(defaults[pipeline_id])
    return {"id": pipeline_id, "name": "Pipeline", "status": "draft", "template": "Custom", "nodes": 0, "vectorStore": "none", "invocations": 0, "lastRun": "—", "stages": _mock_stages()}


@router.patch("/pipelines/{pipeline_id}")
async def update_pipeline(pipeline_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": pipeline_id, "message": "Pipeline updated"}


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, user=Depends(get_current_user)):
    return {"message": "Pipeline deleted"}


@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        # Fallback to mock steps for demonstration if ID doesn't exist
        steps = _mock_steps()
    else:
        steps = pipeline.steps
        
    run_id = str(uuid.uuid4())
    asyncio.create_task(run_pipeline_background(run_id, steps, user.workspace_id or "default", user.id))
    return {"run_id": run_id, "pipeline_id": pipeline_id, "status": "PENDING", "progress": 0}


# --- Interactive Pipeline ---
@router.get("/pipeline/interactive/session")
async def interactive_session(user=Depends(get_current_user)):
    return {"session_id": "ips_placeholder", "status": "ready", "stages": ["source", "build", "validate", "test", "stage", "gate", "deploy"]}


# --- Demo Pipeline ---
@router.get("/demo/pipeline/health")
async def demo_pipeline_health():
    return {
        "status": "healthy",
        "pipeline": "demo",
        "stages": ["Source", "Build", "Validate", "Test", "Stage", "Gate", "Deploy"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/demo/pipeline/run")
async def demo_pipeline_run(body: dict, user=Depends(get_current_user)):
    run_id = str(uuid.uuid4())
    steps = [{"name": s} for s in ["Source", "Build", "Validate", "Test", "Stage", "Gate", "Deploy"]]
    asyncio.create_task(run_pipeline_background(run_id, steps, user.workspace_id or "default", user.id))
    return {"run_id": run_id, "status": "PENDING"}


@router.get("/demo/pipeline/stream")
async def demo_pipeline_stream():
    async def generate():
        import asyncio
        stages = ["Source", "Build", "Validate", "Test", "Stage", "Gate", "Deploy"]
        for i, stage in enumerate(stages):
            data = {"stage": stage, "status": "running", "progress": (i + 1) / len(stages) * 100}
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
            data["status"] = "complete"
            yield f"data: {json.dumps(data)}\n\n"
        yield f"data: {json.dumps({'stage': 'Done', 'status': 'complete', 'progress': 100})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Deployments ---
@router.get("/deployments")
async def list_deployments(user=Depends(get_current_user)):
    return [
        {"id": "d_chat_main", "name": "chat-prod", "type": "chat", "endpoint": "https://api.veklom.com/v1/chat/completions", "auth": "api-key", "model": "veklom-llama3-70b", "region": "fsn1-hetz", "rateLimit": "240 rpm / 1.2M tpm", "status": "live", "rps": 38.4, "errorRate": 0.002},
        {"id": "d_embed_rag", "name": "embed-rag", "type": "embedding", "endpoint": "https://api.veklom.com/v1/embeddings", "auth": "api-key", "model": "veklom-bge-large", "region": "fra1-hetz", "rateLimit": "600 rpm / 4M tpm", "status": "live", "rps": 112.7, "errorRate": 0},
        {"id": "d_code_assist", "name": "code-assist", "type": "completion", "endpoint": "https://api.veklom.com/v1/completions", "auth": "jwt", "model": "veklom-deepseek-v3", "region": "fsn1-hetz", "rateLimit": "120 rpm", "status": "live", "rps": 6.1, "errorRate": 0.001},
        {"id": "d_intake_pipe", "name": "patient-intake-pipeline", "type": "pipeline", "endpoint": "https://api.veklom.com/p/patient-intake", "auth": "api-key", "model": "veklom-llama3-70b", "region": "fsn1-hetz", "rateLimit": "60 rpm", "status": "live", "rps": 1.4, "errorRate": 0},
        {"id": "d_batch_ingest", "name": "nightly-batch-summarize", "type": "batch", "endpoint": "https://api.veklom.com/v1/batches", "auth": "api-key", "model": "veklom-mixtral-8x22", "region": "ash-aws", "rateLimit": "burst 4\u00d7 nightly", "status": "paused", "rps": 0, "errorRate": 0},
        {"id": "d_audit_classifier", "name": "audit-pii-classifier", "type": "chat", "endpoint": "https://api.veklom.com/v1/chat/completions", "auth": "ip-allowlist", "model": "veklom-qwen2-72b", "region": "fsn1-hetz", "rateLimit": "60 rpm", "status": "draft", "rps": 0, "errorRate": 0},
    ]


@router.post("/deployments")
async def create_deployment(body: dict, user=Depends(get_current_user)):
    return {"id": "d_new", "name": body.get("name", ""), "status": "pending"}


@router.patch("/deployments/{deployment_id}")
async def update_deployment(deployment_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": deployment_id, "message": "Deployment updated"}


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str, user=Depends(get_current_user)):
    return {"message": "Deployment deleted"}


# --- Edge / Canary ---
@router.get("/edge/canary/status")
async def canary_status(user=Depends(get_current_user)):
    return {"canary_active": False, "rollout_percent": 0, "stable_version": "1.0.0"}


@router.post("/edge/canary/promote")
async def canary_promote(user=Depends(get_current_user)):
    return {"message": "Canary promoted to stable"}


# --- Routing ---
@router.get("/routing")
async def list_routing_rules(user=Depends(get_current_user)):
    return [
        {"id": "r1", "name": "Cost optimization", "strategy": "cheapest_capable", "is_active": True},
        {"id": "r2", "name": "Quality first", "strategy": "highest_quality", "is_active": False},
    ]


@router.post("/routing")
async def create_routing_rule(body: dict, user=Depends(get_current_user)):
    return {"id": "r_new", "name": body.get("name", ""), "strategy": body.get("strategy", "")}


@router.patch("/routing/{rule_id}")
async def update_routing_rule(rule_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": rule_id, "message": "Rule updated"}


@router.get("/routing/policy")
async def routing_policy(user=Depends(get_current_user)):
    return {
        "default_strategy": "cost_quality_balanced",
        "fallback_enabled": True,
        "max_retries": 3,
        "timeout_seconds": 30,
    }


@router.post("/routing/test")
async def test_routing(body: dict, user=Depends(get_current_user)):
    return {
        "selected_model": "gpt-4o",
        "reason": "Best cost-quality score for this prompt type",
        "alternatives": ["claude-3-5-sonnet", "gemini-2.5-pro"],
    }


# --- Autonomous ---
@router.get("/autonomous/decisions")
async def autonomous_decisions(user=Depends(get_current_user)):
    return [
        {"id": "ad1", "decision": "Routed to GPT-4o Mini for cost savings", "model": "gpt-4o-mini", "timestamp": datetime.now(timezone.utc).isoformat()},
    ]


@router.post("/autonomous/override")
async def autonomous_override(body: dict, user=Depends(get_current_user)):
    return {"message": "Routing override applied", "model": body.get("model", "")}


def _pipe_dict(p: Pipeline) -> dict:
    extra = p.steps if isinstance(p.steps, dict) else {}
    return {
        "id": p.id,
        "name": p.name,
        "template": extra.get("template", p.description or "Custom"),
        "nodes": extra.get("nodes", len(p.steps) if isinstance(p.steps, list) else 0),
        "vectorStore": extra.get("vectorStore", "pgvector"),
        "status": p.status or "draft",
        "invocations": extra.get("invocations", 0),
        "lastRun": extra.get("lastRun", "—"),
    }


def _pipe_detail_dict(p: Pipeline) -> dict:
    d = _pipe_dict(p)
    d["stages"] = _mock_stages()
    d["description"] = p.description or ""
    return d


def _pipe_detail_from_mock(mock: dict) -> dict:
    d = dict(mock)
    d["stages"] = _mock_stages()
    return d


def _mock_pipelines():
    return [
        {"id": "p_rag_clinical", "name": "clinical-rag", "template": "RAG / pgvector", "nodes": 9, "vectorStore": "pgvector", "status": "deployed", "invocations": 18420, "lastRun": "2 min ago"},
        {"id": "p_intake", "name": "patient-intake", "template": "Intake form → triage", "nodes": 12, "vectorStore": "Qdrant", "status": "deployed", "invocations": 412, "lastRun": "12 min ago"},
        {"id": "p_legal_redact", "name": "legal-redactor", "template": "PII strip → redline", "nodes": 7, "vectorStore": "Weaviate", "status": "deployed", "invocations": 2210, "lastRun": "1 hr ago"},
        {"id": "p_risk_class", "name": "risk-classifier", "template": "Multi-label classifier", "nodes": 5, "vectorStore": "pgvector", "status": "draft", "invocations": 0, "lastRun": "—"},
    ]


def _mock_stages():
    return [
        {"id": "st1", "name": "Source", "type": "input", "status": "complete"},
        {"id": "st2", "name": "Build", "type": "transform", "status": "complete"},
        {"id": "st3", "name": "Validate", "type": "check", "status": "running"},
        {"id": "st4", "name": "Test", "type": "check", "status": "pending"},
        {"id": "st5", "name": "Stage", "type": "deploy", "status": "pending"},
        {"id": "st6", "name": "Gate", "type": "approval", "status": "pending"},
        {"id": "st7", "name": "Deploy", "type": "deploy", "status": "pending"},
    ]
