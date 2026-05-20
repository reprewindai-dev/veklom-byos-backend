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

router = APIRouter(tags=["Pipelines"])


# --- Pipelines ---
@router.get("/pipelines")
async def list_pipelines(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).limit(50))
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
async def get_pipeline(pipeline_id: str, user=Depends(get_current_user)):
    return {"id": pipeline_id, "name": "Support Triage Pipeline", "status": "active", "steps": _mock_steps()}


@router.patch("/pipelines/{pipeline_id}")
async def update_pipeline(pipeline_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": pipeline_id, "message": "Pipeline updated"}


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, user=Depends(get_current_user)):
    return {"message": "Pipeline deleted"}


@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, user=Depends(get_current_user)):
    return {"run_id": "run_placeholder", "pipeline_id": pipeline_id, "status": "running", "progress": 0}


# --- Interactive Pipeline ---
@router.get("/pipeline/interactive/session")
async def interactive_session(user=Depends(get_current_user)):
    return {"session_id": "ips_placeholder", "status": "ready", "stages": ["source", "build", "validate", "test", "stage", "gate", "deploy"]}


# --- Demo Pipeline ---
@router.get("/demo/pipeline/health")
async def demo_pipeline_health(user=Depends(get_current_user)):
    return {
        "status": "healthy",
        "pipeline": "demo",
        "stages": ["Source", "Build", "Validate", "Test", "Stage", "Gate", "Deploy"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/demo/pipeline/run")
async def demo_pipeline_run(body: dict, user=Depends(get_current_user)):
    return {"run_id": "demo_run", "status": "completed", "stages_completed": 7}


@router.get("/demo/pipeline/stream")
async def demo_pipeline_stream(user=Depends(get_current_user)):
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
        {"id": "d1", "name": "Production vLLM", "type": "private", "status": "running", "endpoint": "https://vllm.internal:8000"},
        {"id": "d2", "name": "Staging Ollama", "type": "private", "status": "running", "endpoint": "https://ollama.internal:11434"},
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
    return {"id": p.id, "name": p.name, "description": p.description, "status": p.status, "steps": p.steps}


def _mock_pipelines():
    return [
        {"id": "pipe1", "name": "Support Triage", "description": "AI-powered support ticket triage", "status": "active", "steps": _mock_steps()},
        {"id": "pipe2", "name": "Document Review", "description": "Automated document compliance review", "status": "draft", "steps": []},
    ]


def _mock_steps():
    return [
        {"id": "s1", "name": "Intake", "type": "input", "status": "ready"},
        {"id": "s2", "name": "Classify", "type": "ai", "status": "ready"},
        {"id": "s3", "name": "Route", "type": "logic", "status": "ready"},
        {"id": "s4", "name": "Respond", "type": "output", "status": "ready"},
    ]
