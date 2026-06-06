"""Pipeline, deployment, routing, autonomous routes."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
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


def _default_pipeline_graph(template: str = "clinical-rag") -> dict:
    if template == "clinical-rag":
        return {
            "nodes": [
                {"id": "demo-input", "type": "input", "position": {"x": 40, "y": 220}, "data": {"label": "Input", "nodeType": "input"}},
                {"id": "demo-policy", "type": "routing", "position": {"x": 230, "y": 220}, "data": {"label": "Policy Gate", "nodeType": "policy-gate"}},
                {"id": "demo-agent", "type": "langchain", "position": {"x": 450, "y": 190}, "data": {"label": "LangChain Agent", "nodeType": "langchain_agent"}},
                {"id": "demo-json", "type": "output", "position": {"x": 700, "y": 220}, "data": {"label": "JSON Formatter", "nodeType": "json-format"}},
                {"id": "demo-audit", "type": "output", "position": {"x": 930, "y": 220}, "data": {"label": "Audit Signer", "nodeType": "audit-signer"}},
            ],
            "edges": [
                {"id": "e-demo-input-policy", "source": "demo-input", "target": "demo-policy", "animated": True},
                {"id": "e-demo-policy-agent", "source": "demo-policy", "target": "demo-agent", "animated": True},
                {"id": "e-demo-agent-json", "source": "demo-agent", "target": "demo-json", "animated": True},
                {"id": "e-demo-json-audit", "source": "demo-json", "target": "demo-audit", "animated": True},
            ],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "node_configs": {
                "demo-input": {
                    "text": "Summarize Veklom's governed inference pipeline for an enterprise buyer. Redact any PII such as investor@example.com before output.",
                    "requireEvidence": True,
                },
                "demo-policy": {
                    "policy": "sovereign_default",
                    "strategy": "redact",
                    "requireEvidence": True,
                    "redactPii": True,
                },
                "demo-agent": {
                    "model_provider": "ollama",
                    "model_name": "qwen2.5:3b",
                    "system_prompt": "You are the Veklom governed inference agent. Produce concise enterprise-ready output and respect policy-gated context.",
                    "tools_allowed": ["marketplace_tool"],
                    "blocked_tools": ["code_executor"],
                    "max_iterations": 3,
                    "timeout_seconds": 45,
                    "temperature": 0.2,
                    "redact_pii": True,
                    "requireEvidence": True,
                },
                "demo-json": {
                    "outputSchema": "signed_json",
                    "requireEvidence": True,
                },
                "demo-audit": {
                    "requireEvidence": True,
                },
            },
        }
    return {
        "nodes": [],
        "edges": [],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "node_configs": {},
    }


# --- Pipeline Node Database ---
FULL_PIPELINE_NODE_CATALOG = {
    "categories": [
        {
            "id": "veklom", "label": "Veklom Governance",
            "nodes": [
                {"id": "policy-gate", "name": "Policy Gate", "type": "gate", "description": "Enforce policy before risky execution", "certification": {"status": "real", "adapter": "policy_gate"}},
                {"id": "audit-signer", "name": "Audit Signer", "type": "output", "description": "Seal trace evidence with SHA-256 proof", "certification": {"status": "real", "adapter": "audit_signer"}},
                {"id": "evidence-pack", "name": "Evidence Pack", "type": "output", "description": "Compile proof, cost, policy, and trace receipt", "certification": {"status": "real", "adapter": "evidence_pack"}},
                {"id": "pgl-register", "name": "PGL Register", "type": "gate", "description": "Register sealed proof in the governance ledger", "certification": {"status": "real", "adapter": "pgl_register"}},
                {"id": "repo-risk-gate", "name": "Repo Risk Gate", "type": "gate", "description": "Assess GitHub repository risk before deployment", "certification": {"status": "configured", "adapter": "repo_risk_gate", "requires": ["repo_url"]}},
                {"id": "cost-gate", "name": "Cost Gate", "type": "gate", "description": "Block runs over allowed node or total cost", "certification": {"status": "configured", "adapter": "cost_gate", "requires": ["max_cost_usd"]}},
                {"id": "budget-gate", "name": "Budget Gate", "type": "gate", "description": "Enforce monthly or workspace budget thresholds", "certification": {"status": "configured", "adapter": "budget_gate", "requires": ["monthly_cap_usd"]}},
                {"id": "human-approval", "name": "Human Approval", "type": "gate", "description": "Pause deployment until an explicit approval is present", "certification": {"status": "configured", "adapter": "human_approval", "requires": ["approval_id"]}},
                {"id": "ask-human", "name": "ASK_HUMAN Gate", "type": "gate", "description": "Pause execution, freeze context, and resume only after explicit approval", "certification": {"status": "configured", "adapter": "ask_human", "requires": ["approval_id"]}},
                {"id": "pgl-lineage-anchor", "name": "PGL Lineage Anchor", "type": "gate", "description": "Anchor parent proof, execution graph, and receipt hash into lineage", "certification": {"status": "configured", "adapter": "pgl_lineage_anchor", "requires": ["parent_hash"]}},
                {"id": "x402-payment-gate", "name": "x402 Payment Gate", "type": "gate", "description": "Require payment proof before paid tool/model execution proceeds", "certification": {"status": "configured", "adapter": "x402_payment_gate", "requires": ["max_price_usd"]}},
                {"id": "evidence-receipt", "name": "Evidence Receipt", "type": "output", "description": "Seal run proof with cost, policy, trace, identity, and replay metadata", "certification": {"status": "real", "adapter": "evidence_receipt"}},
                {"id": "shadow-mode", "name": "Shadow Mode", "type": "runtime", "description": "Run candidate logic against mirrored traffic without production writes", "certification": {"status": "real", "adapter": "shadow_mode"}},
                {"id": "deploy-endpoint", "name": "Deploy Endpoint", "type": "output", "description": "Mark a completed governed run as endpoint-ready", "certification": {"status": "real", "adapter": "deploy_endpoint"}},
                {"id": "deploy-agent", "name": "Deploy Agent", "type": "output", "description": "Package pipeline as a governed agent contract", "certification": {"status": "real", "adapter": "deploy_agent"}},
                {"id": "lock-engine", "name": "Lock Engine", "type": "gate", "description": "Freeze the execution contract for replayable deploys", "certification": {"status": "real", "adapter": "lock_engine"}},
                {"id": "marketplace-tool", "name": "Marketplace Tool", "type": "tool", "description": "Invoke Veklom marketplace capabilities", "certification": {"status": "real", "adapter": "marketplace_tool"}},
            ],
        },
        {
            "id": "input", "label": "Input",
            "nodes": [
                {"id": "input", "name": "Input", "type": "input", "description": "Pipeline input text or upstream payload", "certification": {"status": "real", "adapter": "input"}},
                {"id": "doc-loader", "name": "Document Loader", "type": "input", "description": "Load text from config.text or a governed external URL", "certification": {"status": "configured", "adapter": "document_loader", "requires": ["text or url"]}},
            ],
        },
        {
            "id": "agents", "label": "Agents",
            "nodes": [
                {"id": "agent-node", "name": "Agent Node", "type": "agent", "description": "Single governed model/tool agent", "certification": {"status": "configured", "adapter": "agent_node", "requires": ["model_provider", "model_name"]}},
                {"id": "agent-team", "name": "Agent Team", "type": "agent", "description": "Coordinate multiple governed agents", "certification": {"status": "configured", "adapter": "agent_team", "requires": ["agents"]}},
                {"id": "supervisor-agent", "name": "Supervisor Agent", "type": "agent", "description": "Route and review agent work", "certification": {"status": "configured", "adapter": "supervisor_agent", "requires": ["model_provider", "model_name"]}},
                {"id": "critic-agent", "name": "Critic Agent", "type": "agent", "description": "Evaluate output against policy and quality rules", "certification": {"status": "configured", "adapter": "critic_agent", "requires": ["model_provider", "model_name"]}},
                {"id": "planner-agent", "name": "Planner Agent", "type": "agent", "description": "Produce governed execution plans", "certification": {"status": "configured", "adapter": "planner_agent", "requires": ["model_provider", "model_name"]}},
                {"id": "agent-handoff", "name": "Agent Handoff", "type": "agent", "description": "Package context for another agent or human", "certification": {"status": "real", "adapter": "agent_handoff"}},
                {"id": "pgl-register-agent", "name": "PGL Register Agent", "type": "agent", "description": "Promote a tested agent workflow into PGL", "certification": {"status": "real", "adapter": "pgl_register_agent"}},
                {"id": "langchain_agent", "name": "LangChain Agent", "type": "agent", "description": "ReAct tool-calling agent with governed tools", "certification": {"status": "configured", "adapter": "langchain_agent", "requires": ["model_provider", "model_name"]}},
            ],
        },
        {
            "id": "models", "label": "Models",
            "nodes": [
                {"id": "llm-openai", "name": "OpenAI LLM", "type": "model", "provider": "openai", "description": "GPT-4o, GPT-4o-mini", "certification": {"status": "configured", "adapter": "llm", "requires": ["OPENAI_API_KEY"]}},
                {"id": "llm-groq", "name": "Groq LLM", "type": "model", "provider": "groq", "description": "Llama 3.1 8B Instant", "certification": {"status": "configured", "adapter": "llm", "requires": ["GROQ_API_KEY"]}},
                {"id": "llm-ollama", "name": "Ollama LLM", "type": "model", "provider": "ollama", "description": "Local models - Qwen, Llama, Mistral", "certification": {"status": "configured", "adapter": "llm", "requires": ["OLLAMA_BASE_URL"]}},
                {"id": "llm-gemini", "name": "Gemini LLM", "type": "model", "provider": "gemini", "description": "Gemini 2.5 Flash / Pro", "certification": {"status": "configured", "adapter": "llm", "requires": ["GEMINI_API_KEY"]}},
                {"id": "llm-anthropic", "name": "Anthropic LLM", "type": "model", "provider": "anthropic", "description": "Claude via configured provider gateway", "certification": {"status": "configured", "adapter": "llm", "requires": ["ANTHROPIC_API_KEY"]}},
                {"id": "llm-openai-compatible", "name": "OpenAI-Compatible Model", "type": "model", "provider": "openai-compatible", "description": "Custom OpenAI-compatible endpoint", "certification": {"status": "configured", "adapter": "llm", "requires": ["base_url"]}},
                {"id": "embed-bge", "name": "BGE-M3 Embedding", "type": "embedding", "provider": "ollama", "description": "Multi-lingual embeddings through Ollama", "certification": {"status": "configured", "adapter": "embedding", "requires": ["OLLAMA_BASE_URL"]}},
                {"id": "embed-openai", "name": "OpenAI Embedding", "type": "embedding", "provider": "openai", "description": "text-embedding-3-small/large", "certification": {"status": "configured", "adapter": "embedding", "requires": ["OPENAI_API_KEY"]}},
            ],
        },
        {
            "id": "retrieval", "label": "Retrieval",
            "nodes": [
                {"id": "pgvector", "name": "pgvector Store", "type": "vector_store", "description": "PostgreSQL vector similarity storage/search", "certification": {"status": "configured", "adapter": "pgvector", "requires": ["embedding"]}},
                {"id": "qdrant", "name": "Qdrant Store", "type": "vector_store", "description": "Qdrant cloud/self-hosted vector DB", "certification": {"status": "configured", "adapter": "qdrant", "requires": ["url", "collection", "embedding"]}},
                {"id": "weaviate", "name": "Weaviate Store", "type": "vector_store", "description": "Weaviate vector DB", "certification": {"status": "configured", "adapter": "weaviate", "requires": ["url", "class_name", "embedding"]}},
                {"id": "chunker", "name": "Document Chunker", "type": "transform", "description": "Split docs into overlapping chunks", "certification": {"status": "real", "adapter": "chunker"}},
                {"id": "reranker", "name": "Re-Ranker", "type": "transform", "description": "Score-based re-ranking for top-k results", "certification": {"status": "real", "adapter": "reranker"}},
                {"id": "hybrid-search", "name": "Hybrid Search", "type": "retrieval", "description": "BM25 + vector fusion over upstream records", "certification": {"status": "real", "adapter": "hybrid_search"}},
            ],
        },
        {
            "id": "integrations", "label": "Integrations",
            "nodes": [
                {"id": "webhook", "name": "Webhook", "type": "integration", "description": "Deliver signed results to customer systems", "certification": {"status": "configured", "adapter": "webhook", "requires": ["url"]}},
                {"id": "http-call", "name": "HTTP Request", "type": "integration", "description": "Call external REST APIs with audit", "certification": {"status": "configured", "adapter": "http_request", "requires": ["url"]}},
                {"id": "email-send", "name": "Email", "type": "integration", "description": "Send governed result to email API/webhook", "certification": {"status": "configured", "adapter": "integration_webhook", "requires": ["url"]}},
                {"id": "slack-send", "name": "Slack", "type": "integration", "description": "Post governed result to Slack webhook", "certification": {"status": "configured", "adapter": "integration_webhook", "requires": ["url"]}},
                {"id": "github-action", "name": "GitHub", "type": "integration", "description": "Open issue/dispatch webhook with evidence", "certification": {"status": "configured", "adapter": "integration_webhook", "requires": ["url"]}},
                {"id": "stripe-event", "name": "Stripe", "type": "integration", "description": "Send billing or usage event to Stripe-connected workflow", "certification": {"status": "configured", "adapter": "integration_webhook", "requires": ["url"]}},
            ],
        },
        {
            "id": "data", "label": "Data",
            "nodes": [
                {"id": "sql-query", "name": "SQL Query", "type": "data", "description": "Execute read-only SQL against configured DBs", "certification": {"status": "configured", "adapter": "sql_query", "requires": ["query"]}},
                {"id": "file-read", "name": "File Reader", "type": "data", "description": "Read documents from governed URL or text payload", "certification": {"status": "configured", "adapter": "file_reader", "requires": ["text or url"]}},
            ],
        },
        {
            "id": "output", "label": "Output",
            "nodes": [
                {"id": "json-format", "name": "JSON Formatter", "type": "output", "description": "Structure output as JSON schema", "certification": {"status": "real", "adapter": "json_formatter"}},
                {"id": "markdown-render", "name": "Markdown Render", "type": "output", "description": "Render output as Markdown", "certification": {"status": "real", "adapter": "markdown_renderer"}},
                {"id": "pii-redact", "name": "PII Redactor", "type": "output", "description": "Strip/mask PII before response", "certification": {"status": "real", "adapter": "pii_redactor"}},
                {"id": "audit-log", "name": "Audit Logger", "type": "output", "description": "Write run audit event into the trace", "certification": {"status": "real", "adapter": "audit_logger"}},
            ],
        },
        {
            "id": "runtime", "label": "Runtime",
            "nodes": [
                {"id": "retry-logic", "name": "Retry Logic", "type": "runtime", "description": "Record retry contract for deploy/runtime", "certification": {"status": "real", "adapter": "retry_logic"}},
                {"id": "circuit-breaker", "name": "Circuit Breaker", "type": "runtime", "description": "Block unsafe failure loops", "certification": {"status": "real", "adapter": "circuit_breaker"}},
                {"id": "rate-limiter", "name": "Rate Limiter", "type": "runtime", "description": "Attach request limits to deployable artifact", "certification": {"status": "real", "adapter": "rate_limiter"}},
            ],
        },
        {
            "id": "custom", "label": "Custom",
            "nodes": [
                {"id": "custom-http", "name": "Custom HTTP Node", "type": "custom", "description": "Private governed HTTP adapter", "certification": {"status": "configured", "adapter": "http_request", "requires": ["url"]}},
                {"id": "custom-python", "name": "Custom Python Node", "type": "custom", "description": "Sandbox-tested Python adapter", "certification": {"status": "configured", "adapter": "code_executor", "requires": ["sandbox_url"]}},
                {"id": "custom-mcp-tool", "name": "Custom MCP Tool", "type": "custom", "description": "Governed MCP tool contract", "certification": {"status": "configured", "adapter": "mcp_tool_contract", "requires": ["server_url"]}},
                {"id": "custom-node-package", "name": "Upload Node Package", "type": "custom", "description": "Private node package requiring sandbox test", "certification": {"status": "configured", "adapter": "private_node_package", "requires": ["package_url", "sandbox_url"]}},
            ],
        },
    ]
}


def _dedupe_node_catalog(catalog: dict) -> dict:
    seen: set[str] = set()
    categories = []
    for category in catalog.get("categories", []):
        nodes = []
        for node in category.get("nodes", []):
            node_id = node.get("id")
            if not node_id or node_id in seen:
                continue
            seen.add(node_id)
            nodes.append(node)
        if nodes:
            categories.append({**category, "nodes": nodes})
    return {"categories": categories}


@router.get("/pipelines/nodes")
async def list_pipeline_nodes(user=Depends(get_current_user)):
    return _dedupe_node_catalog(FULL_PIPELINE_NODE_CATALOG)
    return {
        "categories": [
            {
                "id": "input", "label": "Input",
                "nodes": [
                    {"id": "input", "name": "Input", "type": "input", "description": "Pipeline input text or upstream payload"},
                    {"id": "doc-loader", "name": "Document Loader", "type": "input", "description": "Load text from config.text or a governed external URL"},
                ],
            },
            {
                "id": "langchain", "label": "LangChain",
                "nodes": [
                    {"id": "langchain_agent", "name": "LangChain Agent", "type": "agent", "description": "ReAct tool-calling agent with governed tools"},
                    {"id": "lc-parser", "name": "Output Parser", "type": "output", "description": "Structured Pydantic parsing"},
                ],
            },
            {
                "id": "models", "label": "Models",
                "nodes": [
                    {"id": "llm-openai", "name": "OpenAI LLM", "type": "model", "provider": "openai", "description": "GPT-4o, GPT-4o-mini"},
                    {"id": "llm-groq", "name": "Groq LLM", "type": "model", "provider": "groq", "description": "Llama 3.1 8B Instant (fast)"},
                    {"id": "llm-ollama", "name": "Ollama LLM", "type": "model", "provider": "ollama", "description": "Local models — Qwen, Llama, Mistral"},
                    {"id": "llm-gemini", "name": "Gemini LLM", "type": "model", "provider": "gemini", "description": "Gemini 2.5 Flash / Pro"},
                ]
            },
            {
                "id": "retrieval", "label": "Transform",
                "nodes": [
                    {"id": "chunker", "name": "Document Chunker", "type": "transform", "description": "Split docs into overlapping chunks"},
                ]
            },
            {
                "id": "tools", "label": "Tools",
                "nodes": [
                    {"id": "web-search", "name": "Web Search", "type": "tool", "description": "Brave/SerpAPI web search"},
                    {"id": "http-call", "name": "HTTP Request", "type": "tool", "description": "Call external REST APIs"},
                    {"id": "sql-query", "name": "SQL Query", "type": "tool", "description": "Execute SQL against configured DBs"},
                    {"id": "file-read", "name": "File Reader", "type": "tool", "description": "Read documents from S3/local storage"},
                    {"id": "marketplace-tool", "name": "Marketplace Tool", "type": "tool", "description": "Search Veklom marketplace tools"},
                ]
            },
            {
                "id": "routing", "label": "Routing",
                "nodes": [
                    {"id": "policy-gate", "name": "Policy Gate", "type": "gate", "description": "Apply compliance policy before execution"},
                ]
            },
            {
                "id": "output", "label": "Output",
                "nodes": [
                    {"id": "json-format", "name": "JSON Formatter", "type": "output", "description": "Structure output as JSON schema"},
                    {"id": "markdown-render", "name": "Markdown Render", "type": "output", "description": "Render output as Markdown"},
                    {"id": "pii-redact", "name": "PII Redactor", "type": "output", "description": "Strip/mask PII before response"},
                    {"id": "audit-log", "name": "Audit Logger", "type": "output", "description": "Log to immutable audit trail"},
                    {"id": "audit-signer", "name": "Audit Signer", "type": "output", "description": "SHA-256 seal the evidence trace"},
                    {"id": "webhook", "name": "Webhook", "type": "output", "description": "POST results to external URL"},
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


async def _get_or_create_pipeline(pipeline_id: str, workspace_id: str, db: AsyncSession) -> Pipeline | None:
    if pipeline_id in ("null", "undefined", "none", "", None):
        # Try to resolve to the latest active pipeline for the workspace
        result = await db.execute(
            select(Pipeline)
            .where(Pipeline.workspace_id == workspace_id)
            .order_by(Pipeline.created_at.desc())
            .limit(1)
        )
        pipe = result.scalar_one_or_none()
        if pipe:
            return pipe
        pipeline_id = "clinical-rag"

    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.workspace_id == workspace_id))
    pipe = result.scalar_one_or_none()
    if pipe:
        return pipe

    known_templates = {
        "clinical-rag": ("Clinical RAG", "Healthcare"),
        "legal-redactor": ("Legal Redactor", "Legal"),
        "code-review": ("Code Review Pipeline", "Engineering"),
        "batch-summarizer": ("Batch Summarizer", "Operations"),
        "semantic-search": ("Semantic Search", "Search"),
        "pii-strip-proxy": ("PII Strip Proxy", "Privacy")
    }
    if pipeline_id in known_templates:
        # Check if a pipeline with this template already exists for this workspace to avoid duplicates and primary key conflicts
        result = await db.execute(select(Pipeline).where(Pipeline.workspace_id == workspace_id))
        for p in result.scalars().all():
            if isinstance(p.steps, dict) and p.steps.get("template") == pipeline_id:
                return p

        name, cat = known_templates[pipeline_id]
        import hashlib
        # Generate a deterministic unique ID based on workspace and template to prevent concurrent insertion races
        seed_hash = hashlib.sha256(f"{workspace_id}:{pipeline_id}".encode()).hexdigest()
        deterministic_id = f"{seed_hash[:8]}-{seed_hash[8:12]}-{seed_hash[12:16]}-{seed_hash[16:20]}-{seed_hash[20:32]}"

        # Use deterministic ID, so that multiple workspaces can own their own instance of this template safely
        pipe = Pipeline(
            id=deterministic_id,
            workspace_id=workspace_id,
            name=name,
            description=f"PHI-safe {name} pipeline.",
            steps={
                "template": pipeline_id,
                "nodes": 9 if "rag" in pipeline_id else 6,
                "vectorStore": "pgvector",
                "invocations": 0,
                "lastRun": "—",
                "graph": _default_pipeline_graph(pipeline_id),
            }
        )
        try:
            async with db.begin_nested():
                db.add(pipe)
            await db.commit()
            await db.refresh(pipe)
            return pipe
        except Exception:
            # The begin_nested context manager automatically rolled back the savepoint.
            # Double check if another concurrent request inserted it in the meantime
            result = await db.execute(select(Pipeline).where(Pipeline.workspace_id == workspace_id))
            for p in result.scalars().all():
                if isinstance(p.steps, dict) and p.steps.get("template") == pipeline_id:
                    return p
    return None


# --- Pipelines ---
@router.get("/pipelines")
async def list_pipelines(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_or_create_pipeline("clinical-rag", user.workspace_id or "default", db)
    result = await db.execute(select(Pipeline).where(Pipeline.workspace_id == (user.workspace_id or "default")).limit(50))
    pipes = result.scalars().all()
    # Seed default pipelines if none exist
    if not pipes:
        for pid in ("clinical-rag", "legal-redactor", "code-review"):
            await _get_or_create_pipeline(pid, user.workspace_id or "default", db)
        result = await db.execute(select(Pipeline).where(Pipeline.workspace_id == (user.workspace_id or "default")).limit(50))
        pipes = result.scalars().all()
    pipes = sorted(pipes, key=lambda p: 0 if isinstance(p.steps, dict) and p.steps.get("template") == "clinical-rag" else 1)
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
    from fastapi import HTTPException
    pipe = await _get_or_create_pipeline(pipeline_id, user.workspace_id or "default", db)
    if not pipe:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return _pipe_detail_dict(pipe)


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
    pipe = await _get_or_create_pipeline(pipeline_id, user.workspace_id or "default", db)
    if pipe and isinstance(pipe.steps, dict) and "graph" in pipe.steps:
        return pipe.steps["graph"]
    if pipe and isinstance(pipe.steps, dict):
        graph = _default_pipeline_graph(pipe.steps.get("template", "clinical-rag"))
        if graph["nodes"]:
            steps = dict(pipe.steps)
            steps["graph"] = graph
            pipe.steps = steps
            await db.commit()
            return graph
    return {
        "nodes": [],
        "edges": [],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "node_configs": {},
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
    """
    Queue a pipeline run for execution with workspace isolation and persistent tracking.
    
    Creates a `PipelineRun` record in a queued state, schedules background execution, and returns identifiers and initial status.
    
    Returns:
        dict: Response containing:
            - `run_id` (str): Generated run identifier.
            - `pipeline_id` (str): The pipeline identifier.
            - `status` (str): Initial run status, `"queued"`.
            - `progress` (int): Initial progress value, `0`.
            - `message` (str): Human-readable status message.
    """
    from fastapi import HTTPException
    
    # Verify pipeline belongs to user's workspace (multi-tenant safety)
    pipeline = await _get_or_create_pipeline(pipeline_id, user.workspace_id or "default", db)
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found or access denied")
        
    steps = pipeline.steps or {}
    run_id = str(uuid.uuid4())
    
    # Create a PipelineRun record for tracking
    from backend.db.models.marketplace import PipelineRun
    run = PipelineRun(
        id=run_id,
        pipeline_id=pipeline.id,
        workspace_id=user.workspace_id or "default",
        user_id=user.id,
        status="queued",
        steps=steps,
    )
    db.add(run)
    await db.commit()
    
    # Start graph-backed execution. The worker reads steps["graph"], topologically
    # orders nodes, and executes registered adapters. Legacy pipelines without a
    # graph still fall back to their saved step list.
    asyncio.create_task(run_pipeline_background(run_id, steps, user.workspace_id or "default", user.id))
    
    return {
        "run_id": run_id,
        "pipeline_id": pipeline.id,
        "status": "queued",
        "progress": 0,
        "message": "Pipeline run queued"
    }


@router.get("/pipelines/{pipeline_id}/runs")
async def list_pipeline_runs(pipeline_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Return the recent run history for the specified pipeline, scoped to the caller's workspace.
    
    Returns:
        dict: {
            "pipeline_id": str,
            "runs": [
                {
                    "id": str,
                    "status": str,
                    "created_at": str | None,  # ISO 8601 timestamp or None
                    "updated_at": str | None,  # ISO 8601 timestamp or None
                },
                ...
            ]
        }
    
    Raises:
        HTTPException: 404 if the pipeline does not exist or is not accessible in the caller's workspace.
    """
    from fastapi import HTTPException
    from backend.db.models.marketplace import PipelineRun
    
    # Verify pipeline belongs to user's workspace
    pipeline = await _get_or_create_pipeline(pipeline_id, user.workspace_id or "default", db)
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found or access denied")
    
    pipeline_id = pipeline.id
    
    # Get runs for this pipeline in user's workspace
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.pipeline_id == pipeline_id, PipelineRun.workspace_id == (user.workspace_id or "default"))
        .order_by(PipelineRun.started_at.desc())
        .limit(50)
    )
    runs = result.scalars().all()
    
    return {
        "pipeline_id": pipeline_id,
        "runs": [
            {
                "id": r.id,
                "status": r.status,
                "created_at": r.started_at.isoformat() if r.started_at else None,
                "updated_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]
    }


@router.get("/pipelines/{pipeline_id}/runs/{run_id}")
async def get_pipeline_run(pipeline_id: str, run_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Return detailed information for a pipeline run that belongs to the caller's workspace.
    
    Returns:
        dict: Run details containing keys:
          - `id`: run identifier
          - `pipeline_id`: associated pipeline identifier
          - `status`: run status
          - `steps`: saved steps payload for the run
          - `result`: run result payload (if any)
          - `created_at`: ISO 8601 timestamp string or `None`
          - `updated_at`: ISO 8601 timestamp string or `None`
    
    Raises:
        HTTPException: 404 if the pipeline or the run is not found or access is denied.
    """
    from fastapi import HTTPException
    from backend.db.models.marketplace import PipelineRun
    
    # Verify pipeline belongs to user's workspace
    pipeline = await _get_or_create_pipeline(pipeline_id, user.workspace_id or "default", db)
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found or access denied")
    
    pipeline_id = pipeline.id
    
    # Get the specific run
    result = await db.execute(
        select(PipelineRun)
        .where(
            PipelineRun.id == run_id,
            PipelineRun.pipeline_id == pipeline_id,
            PipelineRun.workspace_id == (user.workspace_id or "default")
        )
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or access denied")
    
    return {
        "id": run.id,
        "pipeline_id": run.pipeline_id,
        "status": run.status,
        "steps": run.steps,
        "result": run.output,
        "created_at": run.started_at.isoformat() if run.started_at else None,
        "updated_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.post("/pipelines/{pipeline_id}/runs/{run_id}/approve")
async def approve_pipeline_run(pipeline_id: str, run_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Approve an ASK_HUMAN pause and resume the frozen pipeline context."""
    pipeline = await _get_or_create_pipeline(pipeline_id, user.workspace_id or "default", db)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found or access denied")

    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id,
            PipelineRun.pipeline_id == pipeline.id,
            PipelineRun.workspace_id == (user.workspace_id or "default"),
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or access denied")
    if run.status != "waiting_approval":
        raise HTTPException(status_code=409, detail=f"Run is not waiting for approval; current status is {run.status}")

    output = run.output or {}
    approval = output.get("approval") or {}
    approval_id = body.get("approval_id") or approval.get("approval_id")
    if not approval_id:
        raise HTTPException(status_code=400, detail="approval_id is required")
    if approval.get("approval_id") and approval_id != approval.get("approval_id"):
        raise HTTPException(status_code=400, detail="approval_id does not match the pending approval")

    decision = (body.get("decision") or body.get("status") or "approved").lower()
    approved_by = body.get("approved_by") or getattr(user, "email", None) or user.id
    frozen_context = output.get("frozen_context") or {}
    resume = output.get("resume") or {}
    start_index = int(resume.get("start_index") or approval.get("step_index") or 0)

    approvals = dict(frozen_context.get("approvals") or {})
    approvals[approval_id] = {
        "status": decision,
        "approved_by": approved_by,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "comment": body.get("comment") or "",
    }
    frozen_context["approvals"] = approvals

    if decision not in {"approved", "allow", "allowed"}:
        run.status = "failed"
        run.error = f"approval_rejected: {approval_id} rejected by {approved_by}"
        run.current_step = "Gate"
        run.completed_at = datetime.now(timezone.utc)
        run.output = {**output, "approval": {**approval, "status": "rejected", "approved_by": approved_by}}
        await db.commit()
        return {"status": "rejected", "run_id": run.id, "approval_id": approval_id}

    run.status = "queued"
    run.progress = max(run.progress or 0, 60)
    run.current_step = "Gate"
    run.error = None
    run.output = {**output, "approval": {**approval, "status": "approved", "approved_by": approved_by}, "frozen_context": frozen_context}
    await db.commit()

    asyncio.create_task(
        run_pipeline_background(
            run.id,
            run.steps or {},
            user.workspace_id or "default",
            user.id,
            resume_context=frozen_context,
            start_index=start_index,
        )
    )

    return {"status": "resuming", "run_id": run.id, "approval_id": approval_id, "start_index": start_index}


@router.get("/pipelines/{pipeline_id}/runs/{run_id}/stream")
async def stream_pipeline_run(pipeline_id: str, run_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Stream server-sent events for a pipeline run's lifecycle and step progress.
    
    Streams JSON-formatted SSE messages that report run-level states and per-stage progress until a terminal state is emitted. Event payloads are JSON objects containing at minimum a `type` (e.g., `run.queued`, `run.running`, `step.running`, `step.completed`, `run.completed`), `run_id`, and `status`; completed events may include `progress`, `output`, `evidence_id`, and `proof_hash`.
    
    Returns:
        StreamingResponse: An HTTP streaming response that yields server-sent event data strings containing the JSON payloads described above.
    
    Raises:
        HTTPException: If the pipeline or the specified run does not exist in the caller's workspace or access is denied.
    """
    from fastapi import HTTPException
    from backend.db.models.marketplace import PipelineRun
    
    # Verify pipeline belongs to user's workspace
    pipeline = await _get_or_create_pipeline(pipeline_id, user.workspace_id or "default", db)
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found or access denied")
    
    pipeline_id = pipeline.id
    
    # Get the specific run
    result = await db.execute(
        select(PipelineRun)
        .where(
            PipelineRun.id == run_id,
            PipelineRun.pipeline_id == pipeline_id,
            PipelineRun.workspace_id == (user.workspace_id or "default")
        )
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or access denied")
    
    async def generate():
        import asyncio
        yield f"data: {json.dumps({'type': 'run.queued', 'run_id': run_id, 'status': 'queued', 'message': 'Pipeline run queued'})}\n\n"
        
        last_step = None
        while True:
            await asyncio.sleep(1)
            result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            r = result.scalar_one_or_none()
            if not r:
                break
            
            if r.current_step and r.current_step != last_step and r.current_step not in ("Initializing autonomous pipeline engine...", "Done"):
                if last_step and last_step not in ("Initializing autonomous pipeline engine...", "Done"):
                    # Complete the previous step
                    yield f"data: {json.dumps({'type': 'step.completed', 'stage': last_step})}\n\n"
                
                # Start the new step
                yield f"data: {json.dumps({'type': 'step.running', 'stage': r.current_step})}\n\n"
                last_step = r.current_step
                
            data = {
                'type': f'run.{r.status}', 
                'run_id': r.id, 
                'status': r.status, 
                'progress': r.progress
            }
            if r.status == "completed":
                if last_step and last_step not in ("Initializing autonomous pipeline engine...", "Done"):
                    yield f"data: {json.dumps({'type': 'step.completed', 'stage': last_step})}\n\n"
                
                out_data = r.output or {}
                receipt = out_data.get('receipt') or {}
                data['output'] = out_data.get('result', '')
                data['evidence_id'] = out_data.get('evidence_id', f'evd_{r.id[:8]}')
                data['proof_hash'] = out_data.get('proof_hash', f'0x{r.id[:16]}')
                data['receipt_id'] = receipt.get('receipt_id')
                data['total_cost_usd'] = receipt.get('total_cost_usd')
                data['total_tokens'] = receipt.get('total_tokens')
                data['deployable'] = receipt.get('deployable')
                yield f"data: {json.dumps(data)}\n\n"
                break
            elif r.status == "waiting_approval":
                out_data = r.output or {}
                data['approval'] = out_data.get('approval')
                data['evidence_id'] = out_data.get('evidence_id', f'evd_{r.id[:8]}')
                data['trace'] = out_data.get('trace', [])
                yield f"data: {json.dumps(data)}\n\n"
                break
            elif r.status == "failed":
                out_data = r.output or {}
                receipt = out_data.get('receipt') or {}
                data['output'] = out_data.get('result', '')
                data['evidence_id'] = out_data.get('evidence_id', f'evd_{r.id[:8]}')
                data['proof_hash'] = out_data.get('proof_hash', f'0x{r.id[:16]}')
                data['receipt_id'] = receipt.get('receipt_id')
                data['error'] = r.error
                yield f"data: {json.dumps(data)}\n\n"
                break
    
    return StreamingResponse(generate(), media_type="text/event-stream")


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
async def demo_pipeline_run(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run_id = str(uuid.uuid4())
    # Use a real pipeline if available, otherwise use default steps
    result = await db.execute(select(Pipeline).where(Pipeline.workspace_id == (user.workspace_id or "default")).limit(1))
    pipeline = result.scalar_one_or_none()
    if pipeline:
        steps = pipeline.steps or {}
    else:
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
async def list_deployments(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all deployments for the workspace."""
    result = await db.execute(
        select(Deployment).where(Deployment.workspace_id == (user.workspace_id or "default")).order_by(Deployment.created_at.desc())
    )
    deployments = result.scalars().all()

    return [_dep_dict(d) for d in deployments]


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


@router.post("/deployments/{deployment_id}/pause")
async def pause_deployment(deployment_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Pause a deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.workspace_id == (user.workspace_id or "default")))
    dep = result.scalar_one_or_none()
    if dep:
        dep.status = "paused"
        dep.health_status = "stopped"
        await db.commit()
    return {"id": deployment_id, "status": "paused"}


@router.post("/deployments/{deployment_id}/resume")
async def resume_deployment(deployment_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Resume a paused deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.workspace_id == (user.workspace_id or "default")))
    dep = result.scalar_one_or_none()
    if dep:
        dep.status = "live"
        dep.health_status = "healthy"
        await db.commit()
    return {"id": deployment_id, "status": "live"}


@router.get("/deployments/{deployment_id}/webhooks")
async def list_deployment_webhooks(deployment_id: str, user=Depends(get_current_user)):
    """List webhooks for a deployment (not configured yet)."""
    return {"deployment_id": deployment_id, "webhooks": [], "message": "Webhooks not configured yet"}


@router.post("/deployments/{deployment_id}/webhooks")
async def create_deployment_webhook(deployment_id: str, body: dict, user=Depends(get_current_user)):
    """Create a webhook for a deployment (not configured yet)."""
    return {"deployment_id": deployment_id, "message": "Webhook creation not configured yet", "status": "not_implemented"}


@router.get("/deployments/{deployment_id}/code")
async def get_deployment_code(deployment_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get code snippets for a deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.workspace_id == (user.workspace_id or "default")))
    dep = result.scalar_one_or_none()
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")

    endpoint = dep.endpoint_url or f"https://api.veklom.com/v1/deployments/{deployment_id}"
    cfg = dep.config_json or {}
    model = cfg.get("model", "llama3.1")

    return {
        "deployment_id": deployment_id,
        "endpoint": endpoint,
        "snippets": {
            "curl": f"""curl -X POST {endpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{{
    "model": "{model}",
    "messages": [{{"role": "user", "content": "Hello"}}]
  }}'""",
            "python": f"""import requests

response = requests.post(
    "{endpoint}",
    headers={{
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_API_KEY"
    }},
    json={{
        "model": "{model}",
        "messages": [{{"role": "user", "content": "Hello"}}]
    }}
)
print(response.json())""",
            "javascript": f"""fetch("{endpoint}", {{
  method: "POST",
  headers: {{
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_API_KEY"
  }},
  body: JSON.stringify({{
    model: "{model}",
    messages: [{{role: "user", content: "Hello"}}]
  }})
}}).then(r => r.json()).then(console.log)"""
        }
    }


# --- Edge / Canary ---
@router.get("/edge/canary/status")
async def canary_status(user=Depends(get_current_user)):
    return {"canary_active": False, "rollout_percent": 0, "stable_version": "1.0.0"}


@router.post("/edge/canary/promote")
async def canary_promote(user=Depends(get_current_user)):
    return {"message": "Canary promoted to stable"}


# --- Routing ---
@router.get("/routing")
async def list_routing_rules(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.marketplace import Pipeline as _P
    result = await db.execute(
        select(_P).where(
            _P.workspace_id == (user.workspace_id or "default"),
            _P.description == "routing_rule"
        )
    )
    rules = result.scalars().all()
    if not rules:
        # Return sensible defaults if no rules have been created yet
        return [
            {"id": "r1", "name": "Cost optimization", "strategy": "cheapest_capable", "is_active": True},
            {"id": "r2", "name": "Quality first", "strategy": "highest_quality", "is_active": False},
        ]
    return [
        {
            "id": r.id,
            "name": r.name,
            "strategy": (r.steps or {}).get("strategy", ""),
            "is_active": (r.steps or {}).get("is_active", True),
        }
        for r in rules
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


# Model-routing test moved off /routing/test (now owned by providers.py for
# provider-key/connectivity testing) to its own canonical path.
@router.post("/routing/model/test")
async def test_model_routing(body: dict, user=Depends(get_current_user)):
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
    stages = []
    if isinstance(p.steps, dict) and "stages" in p.steps:
        stages = p.steps["stages"]
    elif isinstance(p.steps, list):
        stages = [{"id": f"st{i}", "name": step.get("name", f"Stage {i}"), "type": step.get("type", "transform"), "status": "pending"} for i, step in enumerate(p.steps)]
    d["stages"] = stages
    d["description"] = p.description or ""
    return d


# --- Deployments from GitHub trigger ---
@router.post("/deployments/from-github")
async def trigger_github_deployment(workspace_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Manually trigger a redeployment from GitHub, calling the Coolify build API if configured,
    and creating a Deployment record tracking the run.
    """
    import os
    import httpx
    
    # Normally check if user belongs to workspace_id
    if user.workspace_id and user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    # If this is a tenant workspace (not the root admin workspace), trigger GitHub Sync instead
    # The root workspace id is usually "default" or empty for superadmins
    if workspace_id and workspace_id != "default":
        from backend.apps.api.routers.workspace import sync_github_workspace
        return await sync_github_workspace(user=user, db=db)
        
    coolify_token = os.getenv("COOLIFY_API_TOKEN")
    coolify_url = os.getenv("COOLIFY_SERVER_URL", "http://5.78.135.11:8000")
    resource_uuid = os.getenv("COOLIFY_RESOURCE_UUID")
    
    status = "success"
    error_msg = ""
    
    if coolify_token and resource_uuid:
        try:
            url = f"{coolify_url.rstrip('/')}/api/v1/deploy"
            params = {"uuid": resource_uuid, "force": "true"}
            headers = {"Authorization": f"Bearer {coolify_token}"}
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers, timeout=10.0)
                if resp.status_code not in (200, 201):
                    status = "failed"
                    error_msg = f"Coolify API returned {resp.status_code}: {resp.text}"
        except Exception as e:
            status = "failed"
            error_msg = f"Failed to connect to Coolify: {str(e)}"
    else:
        status = "failed"
        error_msg = "Coolify environment variables (COOLIFY_API_TOKEN, COOLIFY_RESOURCE_UUID) not configured"
        
    # Create deployment history record in database
    new_dep = Deployment(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        name=f"GitHub Redeploy Triggered",
        deployment_type="web",
        endpoint_url="https://veklom.com",
        status="live" if status == "success" else "failed",
        config_json={
            "trigger": "manual_github",
            "error": error_msg,
            "canary_active": False,
            "region": "hetzner-fsn1",
        }
    )
    db.add(new_dep)
    await db.commit()
    await db.refresh(new_dep)
    
    return {
        "success": status == "success",
        "deployment_id": new_dep.id,
        "message": "Deployment triggered successfully" if status == "success" else f"Deployment failed: {error_msg}"
    }


