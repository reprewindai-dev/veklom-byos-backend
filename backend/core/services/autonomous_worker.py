import asyncio
import hashlib
import ipaddress
import json
import logging
import socket
from datetime import datetime, timezone
from typing import Dict, Any
from urllib.parse import urlparse

import httpx
from backend.core.database.database import get_db_session
from backend.core.database.redis_client import redis_client
from backend.core.ai.provider_router import run_completion
from backend.core.privacy import pii as pii_engine
from backend.db.models.ai import ExecLog
from backend.db.models.marketplace import PipelineRun
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

async def _update_job_state(transaction_id: str, state: Dict[str, Any]):
    if not redis_client:
        return
    
    key = f"job:{transaction_id}"
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        await redis_client.set(key, json.dumps(state), ex=86400) # Expire in 24 hours
    except Exception as e:
        logger.error(f"Failed to update job state for {transaction_id}: {e}")

async def _log_execution(workspace_id: str, user_id: str, provider: str, model: str, latency: int, tokens: int, cost: float):
    try:
        async with get_db_session() as db:
            log_entry = ExecLog(
                user_id=user_id,
                workspace_id=workspace_id,
                model=model,
                provider=provider,
                prompt_tokens=tokens // 2,
                completion_tokens=tokens // 2,
                total_tokens=tokens,
                cost_usd=cost,
                latency_ms=latency,
                status="completed"
            )
            db.add(log_entry)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log execution: {e}")

async def _update_pipeline_run(run_id: str, updates: dict):
    try:
        async with get_db_session() as db:
            result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            run = result.scalar_one_or_none()
            if run:
                for k, v in updates.items():
                    setattr(run, k, v)
                if updates.get("status") in ("completed", "failed"):
                    run.completed_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as e:
        logger.error(f"Failed to update PipelineRun {run_id}: {e}")

async def run_pipeline_background(transaction_id: str, steps: Any, workspace_id: str, user_id: str):
    """Executes a pipeline autonomously in the background and updates Postgres."""
    await _update_pipeline_run(transaction_id, {
        "status": "running",
        "progress": 0,
        "current_step": "Initializing autonomous pipeline engine..."
    })

    execution = _build_execution_plan(steps)
    total_steps = len(execution)
    if total_steps == 0:
        await _update_pipeline_run(transaction_id, {
            "status": "completed",
            "progress": 100,
            "current_step": "Pipeline has no steps.",
            "output": {"result": "No steps to run."}
        })
        return

    context: Dict[str, Any] = {
        "text": "",
        "chunks": [],
        "records": [],
        "trace": [],
        "policy": {},
    }

    for i, step in enumerate(execution):
        stage = step.get("stage", step.get("name", f"Step {i+1}"))
        await _update_pipeline_run(transaction_id, {
            "current_step": stage,
            "progress": int((i / total_steps) * 100)
        })

        try:
            start_time = datetime.now()
            context = await _execute_pipeline_node(step, context)
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            provider = step.get("provider") or context.get("provider") or "pipeline"
            model = step.get("model") or context.get("model") or step.get("node_type", "adapter")
            tokens = int(context.get("tokens") or max(1, len(str(context.get("text", "")).split())))
            cost = float(context.get("cost") or 0)
            await _log_execution(workspace_id, user_id, provider, model, latency, tokens, cost)
            await asyncio.sleep(0.25)

        except Exception as e:
            node_label = step.get("label") or step.get("name") or step.get("node_type") or "node"
            logger.error(f"Pipeline node {node_label} failed: {e}")
            await _update_pipeline_run(transaction_id, {
                "status": "failed",
                "error": f"Failed at {node_label}: {str(e)}",
                "current_step": stage,
                "output": {"trace": context.get("trace", []), "failed_node": step}
            })
            return

    final_text = str(context.get("text", ""))
    proof_hash = hashlib.sha256(json.dumps(context.get("trace", []), sort_keys=True).encode()).hexdigest()
    await _update_pipeline_run(transaction_id, {
        "status": "completed",
        "progress": 100,
        "current_step": "Done",
        "output": {
            "result": final_text,
            "trace": context.get("trace", []),
            "evidence_id": f"evd_{transaction_id[:8]}",
            "proof_hash": f"0x{proof_hash[:16]}"
        }
    })


def _build_execution_plan(steps: Any) -> list[dict]:
    if isinstance(steps, dict) and isinstance(steps.get("graph"), dict):
        graph = steps["graph"]
        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []
        configs = graph.get("node_configs") or {}
        ordered = _topological_nodes(nodes, edges)
        return [_node_to_step(node, configs.get(node.get("id"), {})) for node in ordered]

    if isinstance(steps, list):
        return [
            {
                "id": step.get("id", f"step-{i}"),
                "label": step.get("name", f"Step {i + 1}"),
                "node_type": step.get("type", "llm-openai"),
                "stage": step.get("name", "Test"),
                "config": step,
            }
            for i, step in enumerate(steps)
        ]
    return []


def _topological_nodes(nodes: list[dict], edges: list[dict]) -> list[dict]:
    by_id = {n.get("id"): n for n in nodes if n.get("id")}
    indegree = {node_id: 0 for node_id in by_id}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in by_id}
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in by_id and target in by_id:
            outgoing[source].append(target)
            indegree[target] += 1
    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    ordered: list[dict] = []
    while queue:
        node_id = queue.pop(0)
        ordered.append(by_id[node_id])
        for target in outgoing[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(ordered) != len(by_id):
        raise ValueError("Pipeline graph contains a cycle")
    return ordered


def _node_to_step(node: dict, config: dict) -> dict:
    data = node.get("data") or {}
    node_type = data.get("nodeType") or node.get("nodeType") or node.get("type") or "node"
    return {
        "id": node.get("id"),
        "label": data.get("label") or node.get("label") or node.get("id"),
        "node_type": node_type,
        "stage": _stage_for_node(node_type, node.get("type")),
        "config": config or {},
    }


def _stage_for_node(node_type: str, category: str | None) -> str:
    n = (node_type or "").lower()
    c = (category or "").lower()
    if n in {"input", "source", "doc-loader", "document-loader", "file-read"}:
        return "Source"
    if c in {"retrieval", "tools"} or any(k in n for k in ("chunk", "embed", "qdrant", "pgvector", "weaviate", "search", "http", "sql", "file")):
        return "Build"
    if c == "routing" or any(k in n for k in ("policy", "router", "classifier", "fallback")):
        return "Validate"
    if c in {"models", "langchain"} or n.startswith("llm-") or n.startswith("lc-"):
        return "Test"
    if c == "output" or any(k in n for k in ("format", "render", "redact")):
        return "Stage"
    if "audit" in n:
        return "Gate"
    return "Deploy"


async def _execute_pipeline_node(step: dict, context: dict) -> dict:
    node_type = (step.get("node_type") or "").lower()
    config = step.get("config") or {}
    label = step.get("label") or node_type
    before = hashlib.sha256(str(context.get("text", "")).encode()).hexdigest()[:12]

    if node_type in {"input", "source"}:
        text = str(config.get("text") or config.get("input") or context.get("text") or "Initial Pipeline State.")
        context["text"] = text
        result = {"kind": "input", "chars": len(text)}

    elif node_type in {"doc-loader", "document-loader", "file-read"}:
        text = await _load_document(config)
        context["text"] = text
        result = {"kind": "document_loader", "chars": len(text)}

    elif node_type in {"chunker", "document-chunker"}:
        chunks = _chunk_text(str(context.get("text", "")), int(config.get("chunkSize") or config.get("chunk_size") or 900))
        context["chunks"] = chunks
        result = {"kind": "chunker", "chunks": len(chunks)}

    elif node_type in {"policy-gate", "pii-redact"}:
        masked = pii_engine.mask(str(context.get("text", "")), config.get("strategy", "redact"))
        context["text"] = masked.get("masked_text", context.get("text", ""))
        context["policy"] = {"pii_found": masked.get("pii_found", []), "redacted": bool(masked.get("pii_found"))}
        result = {"kind": "policy", **context["policy"]}

    elif node_type in {"http-call", "http-request"}:
        response = await _http_request_node(config, context)
        context["text"] = response
        result = {"kind": "http", "chars": len(response)}

    elif node_type in {"webhook"}:
        response = await _webhook_node(config, context)
        result = {"kind": "webhook", "status": response}

    elif node_type in {"json-format", "markdown-render", "lc-parser", "output-parser"}:
        context["text"] = _format_output(node_type, context)
        result = {"kind": "formatter", "format": node_type}

    elif node_type in {"audit-log", "audit-signer"}:
        seal = hashlib.sha256(json.dumps(context.get("trace", []), sort_keys=True).encode()).hexdigest()
        context["audit_seal"] = seal
        result = {"kind": "audit", "seal": seal[:16]}

    elif node_type.startswith("llm-") or node_type in {"lc-agent", "lc-langgraph", "lc-retrievalqa"}:
        completion = await _llm_node(node_type, config, context)
        context["text"] = completion["text"]
        context["provider"] = completion["provider"]
        context["model"] = completion["model"]
        context["tokens"] = completion["tokens"]
        context["cost"] = completion["cost"]
        result = {"kind": "llm", "provider": completion["provider"], "model": completion["model"]}

    else:
        raise ValueError(f"No execution adapter registered for node type '{node_type}'")

    after = hashlib.sha256(str(context.get("text", "")).encode()).hexdigest()[:12]
    context.setdefault("trace", []).append({
        "node_id": step.get("id"),
        "node_type": node_type,
        "label": label,
        "stage": step.get("stage"),
        "input_hash": before,
        "output_hash": after,
        "result": result,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    })
    return context


async def _load_document(config: dict) -> str:
    if config.get("text"):
        return str(config["text"])
    url = config.get("url")
    if not url:
        raise ValueError("Document Loader requires config.text or config.url")
    await _assert_safe_external_url(str(url))
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(str(url))
    response.raise_for_status()
    return response.text


def _chunk_text(text: str, size: int) -> list[str]:
    if not text:
        return []
    size = max(200, min(size, 4000))
    return [text[i:i + size] for i in range(0, len(text), size)]


async def _http_request_node(config: dict, context: dict) -> str:
    url = config.get("url")
    if not url:
        raise ValueError("HTTP Request requires config.url")
    method = str(config.get("method") or "GET").upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError("HTTP Request method is not allowed")
    await _assert_safe_external_url(str(url))
    body = config.get("body")
    if body is None and method in {"POST", "PUT", "PATCH"}:
        body = {"input": context.get("text", "")}
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        response = await client.request(method, str(url), json=body if isinstance(body, (dict, list)) else None, content=body if isinstance(body, str) else None)
    response.raise_for_status()
    return response.text


async def _webhook_node(config: dict, context: dict) -> int:
    url = config.get("url") or config.get("webhookUrl") or config.get("webhook_url")
    if not url:
        raise ValueError("Webhook requires config.url")
    await _assert_safe_external_url(str(url))
    payload = {"result": context.get("text", ""), "trace": context.get("trace", []), "audit_seal": context.get("audit_seal")}
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        response = await client.post(str(url), json=payload)
    response.raise_for_status()
    return response.status_code


async def _llm_node(node_type: str, config: dict, context: dict) -> dict:
    provider = config.get("provider") or node_type.replace("llm-", "")
    if node_type in {"lc-agent", "lc-langgraph", "lc-retrievalqa"}:
        provider = config.get("provider") or "ollama"
    prompt = config.get("prompt") or context.get("text") or "Run a governed Veklom pipeline step."
    if context.get("chunks"):
        prompt = f"{prompt}\n\nRetrieved context:\n" + "\n\n".join(context["chunks"][:5])
    result = await run_completion({
        "provider": provider,
        "model": config.get("model"),
        "temperature": config.get("temperature", 0.2),
        "messages": [{"role": "user", "content": str(prompt)}],
    }, stream=False)
    text = result.payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = result.payload.get("usage") or {}
    tokens = int(usage.get("total_tokens") or max(1, len(str(prompt).split()) + len(text.split())))
    return {
        "text": text,
        "provider": result.provider,
        "model": result.payload.get("model") or config.get("model") or node_type,
        "tokens": tokens,
        "cost": tokens * 0.00001,
    }


async def _assert_safe_external_url(raw_url: str) -> None:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Outbound node URL must be http(s) with a hostname")

    hostname = parsed.hostname.strip().lower()
    if hostname in {"localhost", "metadata.google.internal"} or hostname.endswith(".local"):
        raise ValueError("Outbound node URL targets a local or metadata hostname")

    addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    for family, _, _, _, sockaddr in addresses:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Outbound node URL resolves to a private or reserved network")


def _format_output(node_type: str, context: dict) -> str:
    if node_type == "json-format" or node_type in {"lc-parser", "output-parser"}:
        return json.dumps({"result": context.get("text", ""), "policy": context.get("policy", {}), "audit_seal": context.get("audit_seal")}, indent=2)
    return str(context.get("text", ""))

async def run_gpc_background(transaction_id: str, graph: Dict, workspace_id: str, user_id: str, provider: str, model: str):
    """Executes a Governed Plan Compiler (GPC) graph autonomously."""
    state = {
        "status": "PROCESSING",
        "progress": 0,
        "detail": "Bootstrapping GPC reasoning graph...",
        "destination_node": None
    }
    await _update_job_state(transaction_id, state)
    
    nodes = graph.get("nodes", [])
    total_nodes = len(nodes)
    if total_nodes == 0:
        state["status"] = "COMPLETED"
        state["progress"] = 100
        state["detail"] = "GPC Graph is empty."
        await _update_job_state(transaction_id, state)
        return
        
    context = "Initial invariant state."
    
    for i, node in enumerate(nodes):
        node_id = node.get("id", f"node_{i}")
        desc = node.get("description", "Node Execution")
        
        state["destination_node"] = node_id
        state["detail"] = f"Evaluating {desc}..."
        state["progress"] = int((i / total_nodes) * 100)
        await _update_job_state(transaction_id, state)
        
        try:
            start_time = datetime.now()
            prompt = f"GPC Node: {desc}. Evaluate according to invariant limits. Current Context: {context}"
            
            result = await run_completion({"provider": provider, "model": model, "messages": [{"role": "user", "content": prompt}]}, stream=False)
            
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            context = result.payload.get("choices", [{}])[0].get("message", {}).get("content", "Evaluated.")
            
            tokens = len(prompt.split()) + len(context.split())
            cost = tokens * 0.00002
            
            await _log_execution(workspace_id, user_id, result.provider, result.payload.get("model", model), latency, tokens, cost)
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"GPC execution failed at node {node_id}: {e}")
            state["status"] = "FAILED"
            state["detail"] = f"Invariant breach at {desc}: {str(e)}"
            await _update_job_state(transaction_id, state)
            return
            
    # Finalize
    state["status"] = "COMPLETED"
    state["progress"] = 100
    state["detail"] = "GPC Path compiled and successfully executed."
    import hashlib
    state["proof_hash"] = hashlib.sha256(context.encode()).hexdigest()[:16]
    await _update_job_state(transaction_id, state)
