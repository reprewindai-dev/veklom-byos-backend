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


# --- Pipeline Node Database ---
@router.get("/pipelines/nodes")
async def list_pipeline_nodes(user=Depends(get_current_user)):
    return {
        "categories": [
            {
                "id": "models", "label": "Models",
                "nodes": [
                    {"id": "llm-openai", "name": "OpenAI LLM", "type": "model", "provider": "openai", "description": "GPT-4o, GPT-4o-mini"},
                    {"id": "llm-groq", "name": "Groq LLM", "type": "model", "provider": "groq", "description": "Llama 3.1 8B Instant (fast)"},
                    {"id": "llm-ollama", "name": "Ollama LLM", "type": "model", "provider": "ollama", "description": "Local models — Qwen, Llama, Mistral"},
                    {"id": "llm-gemini", "name": "Gemini LLM", "type": "model", "provider": "gemini", "description": "Gemini 2.5 Flash / Pro"},
                    {"id": "embed-bge", "name": "BGE-M3 Embedding", "type": "embedding", "provider": "ollama", "description": "Multi-lingual 1024d embeddings"},
                    {"id": "embed-openai", "name": "OpenAI Embedding", "type": "embedding", "provider": "openai", "description": "text-embedding-3-small/large"},
                ]
            },
            {
                "id": "retrieval", "label": "Retrieval",
                "nodes": [
                    {"id": "pgvector", "name": "pgvector Store", "type": "vector_store", "description": "PostgreSQL vector similarity search"},
                    {"id": "qdrant", "name": "Qdrant Store", "type": "vector_store", "description": "Qdrant cloud/self-hosted vector DB"},
                    {"id": "chunker", "name": "Document Chunker", "type": "transform", "description": "Split docs into overlapping chunks"},
                    {"id": "reranker", "name": "Re-Ranker", "type": "transform", "description": "Cross-encoder re-ranking for top-k results"},
                    {"id": "hybrid-search", "name": "Hybrid Search", "type": "retrieval", "description": "BM25 + vector fusion search"},
                ]
            },
            {
                "id": "tools", "label": "Tools",
                "nodes": [
                    {"id": "web-search", "name": "Web Search", "type": "tool", "description": "Brave/SerpAPI web search"},
                    {"id": "code-exec", "name": "Code Executor", "type": "tool", "description": "Sandboxed Python/JS execution"},
                    {"id": "http-call", "name": "HTTP Request", "type": "tool", "description": "Call external REST APIs"},
                    {"id": "sql-query", "name": "SQL Query", "type": "tool", "description": "Execute SQL against configured DBs"},
                    {"id": "file-read", "name": "File Reader", "type": "tool", "description": "Read documents from S3/local storage"},
                ]
            },
            {
                "id": "routing", "label": "Routing",
                "nodes": [
                    {"id": "policy-gate", "name": "Policy Gate", "type": "gate", "description": "Apply compliance policy before execution"},
                    {"id": "cost-router", "name": "Cost Router", "type": "router", "description": "Route to cheapest capable model"},
                    {"id": "fallback", "name": "Fallback Chain", "type": "router", "description": "Try providers in order until success"},
                    {"id": "load-balancer", "name": "Load Balancer", "type": "router", "description": "Round-robin across providers"},
                    {"id": "classifier", "name": "Intent Classifier", "type": "router", "description": "Route based on query classification"},
                ]
            },
            {
                "id": "output", "label": "Output",
                "nodes": [
                    {"id": "json-format", "name": "JSON Formatter", "type": "output", "description": "Structure output as JSON schema"},
                    {"id": "pii-redact", "name": "PII Redactor", "type": "output", "description": "Strip/mask PII before response"},
                    {"id": "audit-log", "name": "Audit Logger", "type": "output", "description": "Log to immutable audit trail"},
                    {"id": "webhook", "name": "Webhook", "type": "output", "description": "POST results to external URL"},
                    {"id": "stream-out", "name": "Stream Output", "type": "output", "description": "SSE streaming response"},
                ]
            },
        ]
    }


# --- Pipeline Templates ---
@router.get("/pipelines/templates")
async def list_pipeline_templates(user=Depends(get_current_user)):
    return {
        "templates": [
            {"id": "clinical-rag", "name": "Clinical RAG", "description": "PHI-safe RAG over clinical PDFs with redaction, chunking, and signed evidence export.", "vectorStore": "pgvector", "nodes": 9, "compliance": ["HIPAA", "SOC2"], "category": "Healthcare"},
            {"id": "legal-redactor", "name": "Legal Redactor", "description": "Strip PII, redline contracts, and emit signed redaction reports.", "vectorStore": "pgvector", "nodes": 7, "compliance": ["GDPR", "SOC2"], "category": "Legal"},
            {"id": "code-review", "name": "Code Review Pipeline", "description": "Security and style analysis — integrates with GitHub PRs.", "vectorStore": "qdrant", "nodes": 6, "compliance": ["SOC2"], "category": "Engineering"},
            {"id": "batch-summarizer", "name": "Batch Summarizer", "description": "Nightly batch summarisation with Mixtral 8x22B and audit trail.", "vectorStore": "pgvector", "nodes": 5, "compliance": [], "category": "Operations"},
            {"id": "semantic-search", "name": "Semantic Search", "description": "Multi-stage embedding, rerank, and retrieval pipeline.", "vectorStore": "qdrant", "nodes": 8, "compliance": [], "category": "Search"},
            {"id": "pii-strip-proxy", "name": "PII Strip Proxy", "description": "Inline PII detection and redaction for all LLM traffic.", "vectorStore": "pgvector", "nodes": 4, "compliance": ["GDPR", "CCPA", "HIPAA"], "category": "Privacy"},
        ]
    }


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
    from fastapi import HTTPException
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    steps_payload = {
        "template": body.get("template", "Custom"),
        "nodes": body.get("nodes", 0),
        "vectorStore": body.get("vectorStore", "pgvector"),
        "invocations": 0,
        "lastRun": "—",
    }
    pipe = Pipeline(
        workspace_id=user.workspace_id or "default",
        name=name,
        description=body.get("description", ""),
        steps=steps_payload,
    )
    db.add(pipe)
    await db.commit()
    await db.refresh(pipe)
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
async def update_pipeline(pipeline_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.workspace_id == (user.workspace_id or "default")))
    pipe = result.scalar_one_or_none()
    if pipe:
        if "name" in body:
            pipe.name = body["name"]
        if "description" in body:
            pipe.description = body["description"]
        if "status" in body:
            pipe.status = body["status"]
        extra = pipe.steps if isinstance(pipe.steps, dict) else {}
        for k in ("template", "vectorStore", "nodes", "invocations", "lastRun"):
            if k in body:
                extra[k] = body[k]
        pipe.steps = extra
        await db.commit()
        await db.refresh(pipe)
        return _pipe_dict(pipe)
    return {"id": pipeline_id, "updated": True}


@router.get("/pipelines/{pipeline_id}/graph")
async def get_pipeline_graph(pipeline_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get the saved graph state (nodes, edges, viewport) for a pipeline."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipe = result.scalar_one_or_none()
    if pipe and isinstance(pipe.steps, dict) and "graph" in pipe.steps:
        return pipe.steps["graph"]
    # Return default graph for the mock pipelines
    return {
        "nodes": [
            {"id": "input-1", "type": "input", "position": {"x": 50, "y": 200}, "data": {"label": "Input", "nodeType": "input"}},
            {"id": "policy-1", "type": "gate", "position": {"x": 250, "y": 200}, "data": {"label": "Policy Gate", "nodeType": "policy-gate"}},
            {"id": "embed-1", "type": "embedding", "position": {"x": 450, "y": 120}, "data": {"label": "BGE-M3 Embedding", "nodeType": "embed-bge"}},
            {"id": "retrieve-1", "type": "retrieval", "position": {"x": 450, "y": 280}, "data": {"label": "pgvector", "nodeType": "pgvector"}},
            {"id": "rerank-1", "type": "transform", "position": {"x": 650, "y": 200}, "data": {"label": "Re-Ranker", "nodeType": "reranker"}},
            {"id": "llm-1", "type": "model", "position": {"x": 850, "y": 200}, "data": {"label": "Llama 3.1 70B", "nodeType": "llm-ollama"}},
            {"id": "output-1", "type": "output", "position": {"x": 1050, "y": 200}, "data": {"label": "Output", "nodeType": "stream-out"}},
        ],
        "edges": [
            {"id": "e-input-policy", "source": "input-1", "target": "policy-1", "animated": True},
            {"id": "e-policy-embed", "source": "policy-1", "target": "embed-1", "animated": True},
            {"id": "e-policy-retrieve", "source": "policy-1", "target": "retrieve-1", "animated": True},
            {"id": "e-embed-rerank", "source": "embed-1", "target": "rerank-1", "animated": True},
            {"id": "e-retrieve-rerank", "source": "retrieve-1", "target": "rerank-1", "animated": True},
            {"id": "e-rerank-llm", "source": "rerank-1", "target": "llm-1", "animated": True},
            {"id": "e-llm-output", "source": "llm-1", "target": "output-1", "animated": True},
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


@router.put("/pipelines/{pipeline_id}/graph")
@router.post("/pipelines/{pipeline_id}/graph")
async def save_pipeline_graph(pipeline_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Save graph state (nodes, edges, viewport, node_configs) for a pipeline."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.workspace_id == (user.workspace_id or "default")))
    pipe = result.scalar_one_or_none()
    if not pipe:
        # Create pipeline if it doesn't exist
        pipe = Pipeline(
            id=pipeline_id,
            workspace_id=user.workspace_id or "default",
            name=body.get("name", "Untitled Pipeline"),
            description="",
            steps={},
        )
        db.add(pipe)

    steps = pipe.steps if isinstance(pipe.steps, dict) else {}
    steps["graph"] = {
        "nodes": body.get("nodes", []),
        "edges": body.get("edges", []),
        "viewport": body.get("viewport", {"x": 0, "y": 0, "zoom": 1}),
        "node_configs": body.get("node_configs", {}),
    }
    pipe.steps = steps
    await db.commit()
    return {"saved": True, "pipeline_id": pipeline_id, "nodes_count": len(steps["graph"]["nodes"]), "edges_count": len(steps["graph"]["edges"])}


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.workspace_id == (user.workspace_id or "default")))
    pipe = result.scalar_one_or_none()
    if pipe:
        await db.delete(pipe)
        await db.commit()
    return {"deleted": True, "id": pipeline_id}


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
async def create_deployment(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cfg = {"model": body.get("model", ""), "auth": body.get("auth", "api-key"), "region": body.get("region", "fsn1-hetz"), "rateLimit": body.get("rateLimit", "")}
    dep = Deployment(
        workspace_id=user.workspace_id or "default",
        name=body.get("name", "New Deployment"),
        deployment_type=body.get("type", "chat"),
        endpoint_url=body.get("endpoint", ""),
        status=body.get("status", "draft"),
        config_json=cfg,
    )
    db.add(dep)
    await db.commit()
    await db.refresh(dep)
    return _dep_dict(dep)


@router.patch("/deployments/{deployment_id}")
async def update_deployment(deployment_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.workspace_id == (user.workspace_id or "default")))
    dep = result.scalar_one_or_none()
    if dep:
        if "name" in body: dep.name = body["name"]
        if "status" in body: dep.status = body["status"]
        if "endpoint" in body: dep.endpoint_url = body["endpoint"]
        cfg = dep.config_json or {}
        for k in ("model", "auth", "region", "rateLimit"):
            if k in body: cfg[k] = body[k]
        dep.config_json = cfg
        await db.commit()
        await db.refresh(dep)
        return _dep_dict(dep)
    return {"id": deployment_id, "updated": True}


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.workspace_id == (user.workspace_id or "default")))
    dep = result.scalar_one_or_none()
    if dep:
        await db.delete(dep)
        await db.commit()
    return {"deleted": True, "id": deployment_id}


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
async def create_routing_rule(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.marketplace import Pipeline as _P
    rule_id = str(uuid.uuid4())
    rule = _P(
        workspace_id=user.workspace_id or "default",
        name=body.get("name", "Routing Rule"),
        description="routing_rule",
        steps={"strategy": body.get("strategy", ""), "is_active": True, "rule_id": rule_id},
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "name": rule.name, "strategy": body.get("strategy", ""), "is_active": True}


@router.patch("/routing/{rule_id}")
async def update_routing_rule(rule_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.marketplace import Pipeline as _P
    result = await db.execute(select(_P).where(_P.id == rule_id, _P.workspace_id == (user.workspace_id or "default")))
    rule = result.scalar_one_or_none()
    if rule and rule.description == "routing_rule":
        if "name" in body: rule.name = body["name"]
        steps = rule.steps or {}
        for k in ("strategy", "is_active"):
            if k in body: steps[k] = body[k]
        rule.steps = steps
        await db.commit()
        return {"id": rule.id, "name": rule.name, "strategy": steps.get("strategy"), "is_active": steps.get("is_active", True), "updated": True}
    return {"id": rule_id, "updated": True}


@router.get("/routing/policy")
async def routing_policy(user=Depends(get_current_user)):
    return {
        "default_strategy": "cost_quality_balanced",
        "fallback_enabled": True,
        "max_retries": 3,
        "timeout_seconds": 30,
    }


@router.post("/routing/policy")
async def set_routing_policy(body: dict, user=Depends(get_current_user)):
    return {
        "default_strategy": body.get("default_strategy", "cost_quality_balanced"),
        "fallback_enabled": body.get("fallback_enabled", True),
        "max_retries": body.get("max_retries", 3),
        "timeout_seconds": body.get("timeout_seconds", 30),
        "updated": True,
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


def _dep_dict(d: Deployment) -> dict:
    cfg = d.config_json or {}
    return {
        "id": d.id,
        "name": d.name,
        "type": d.deployment_type or "chat",
        "endpoint": d.endpoint_url or "",
        "auth": cfg.get("auth", "api-key"),
        "model": cfg.get("model", ""),
        "region": cfg.get("region", "fsn1-hetz"),
        "rateLimit": cfg.get("rateLimit", "—"),
        "status": d.status or "draft",
        "rps": cfg.get("rps", 0),
        "errorRate": cfg.get("errorRate", 0),
    }


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
