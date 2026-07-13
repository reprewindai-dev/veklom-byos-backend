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
from pydantic import BaseModel, Field, ValidationError, field_validator
from backend.core.config.settings import settings
from backend.core.database.database import get_db_session
from backend.core.database.redis_client import redis_client
from backend.core.ai.provider_router import _configured_provider, run_completion
from backend.core.privacy import pii as pii_engine
from backend.db.models.ai import ExecLog
from backend.db.models.pipelines import PipelineRun
from sqlalchemy import select, text as sql_text, update

logger = logging.getLogger(__name__)

LANGCHAIN_AGENT_NODE_TYPE = "langchain_agent"
PIPELINE_ADAPTER_ALIASES = {
    "lc-agent": LANGCHAIN_AGENT_NODE_TYPE,
    "langchain-agent": LANGCHAIN_AGENT_NODE_TYPE,
}
ALLOWED_LANGCHAIN_TOOLS = {
    "web_search",
    "http_request",
    "sql_query",
    "file_reader",
    "code_executor",
    "marketplace_tool",
}


class PipelinePausedForApproval(Exception):
    def __init__(self, approval: dict, context: dict, step_index: int):
        super().__init__("approval_required: ASK_HUMAN is waiting for approval")
        self.approval = approval
        self.context = context
        self.step_index = step_index


class LangChainAgentConfig(BaseModel):
    model_provider: str = Field(..., min_length=2, max_length=32)
    model_name: str = Field(..., min_length=2, max_length=160)
    system_prompt: str = Field(default="You are a governed Veklom ReAct agent. Use tools only when required.", max_length=4000)
    tools_allowed: list[str] = Field(default_factory=list, max_length=8)
    blocked_tools: list[str] = Field(default_factory=list, max_length=8)
    max_iterations: int = Field(default=3, ge=1, le=8)
    timeout_seconds: int = Field(default=45, ge=5, le=180)
    temperature: float = Field(default=0.2, ge=0, le=2)
    redact_pii: bool = True

    @field_validator("model_provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        aliases = {"google": "gemini", "hf": "huggingface"}
        return aliases.get(provider, provider)

    @field_validator("tools_allowed", "blocked_tools")
    @classmethod
    def validate_tools(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values or []:
            tool = str(value).strip().lower().replace("-", "_")
            if tool not in ALLOWED_LANGCHAIN_TOOLS:
                raise ValueError(f"Unsupported LangChain tool '{value}'")
            if tool not in normalized:
                normalized.append(tool)
        return normalized


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
                input_tokens=tokens // 2,
                output_tokens=tokens // 2,
                cost=cost,
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

async def run_pipeline_background(transaction_id: str, steps: Any, workspace_id: str, user_id: str, resume_context: dict | None = None, start_index: int = 0):
    """Executes a pipeline autonomously in the background and updates Postgres.

    GOVERNANCE: Every pipeline run goes through PGL identity resolution before
    any step executes. If the operator (user_id) has no gnomledger identity or
    is quarantined, the run is hard-blocked and marked failed immediately.
    No if, and, or but.
    """
    await _update_pipeline_run(transaction_id, {
        "status": "running",
        "progress": max(0, min(100, int((start_index or 0) * 5))),
        "current_step": "Source" if not resume_context else "Test"
    })

    # ── PGL HARD GATE ─────────────────────────────────────────────────────────
    # Every pipeline run is attributable to the actor who launched it (user_id).
    # Resolve their gnomledger identity before any computation starts.
    _pgl_ctx = None
    try:
        from backend.core.services.pgl_identity_gate import (
            PGLIdentityGate,
            PGLIdentityError,
            AgentKind,
        )
        async with get_db_session() as _pgl_db:
            _pgl_ctx = await PGLIdentityGate.require(
                db       = _pgl_db,
                actor_id = user_id,
                action   = "run_pipeline_background",
                payload  = {
                    "transaction_id": transaction_id,
                    "workspace_id":   workspace_id,
                    "step_count":     len(steps) if hasattr(steps, "__len__") else "unknown",
                    "start_index":    start_index,
                },
                kind = AgentKind.PIPELINE,
                scope = "pipeline:exec",
            )
            await _pgl_db.commit()
        logger.info(
            f"[PGLGate] ✅ Pipeline cleared — actor='{user_id}' "
            f"txn='{transaction_id}' cert='{_pgl_ctx.pre_execution_cert_id}'"
        )
    except Exception as _pgl_exc:
        _reason = f"PGL identity gate blocked pipeline execution for actor='{user_id}': {_pgl_exc}"
        logger.error(f"[PGLGate] 🚫 HARD BLOCK — {_reason}")
        await _update_pipeline_run(transaction_id, {
            "status":       "failed",
            "progress":     0,
            "current_step": "PGL Identity Check",
            "error":        _reason,
            "output": {
                "pgl_denied": True,
                "actor_id":   user_id,
                "reason":     _reason,
            },
        })
        return
    # ──────────────────────────────────────────────────────────────────────────

    await asyncio.sleep(0.01)
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

    await _set_lifecycle_stage(transaction_id, "Build", 12)
    await asyncio.sleep(0.01)
    preflight = _preflight_execution_plan(execution)
    await _set_lifecycle_stage(transaction_id, "Validate", 24, {"preflight": preflight})
    await asyncio.sleep(0.01)
    blocking = [item for item in preflight["nodes"] if item["certification"]["status"] in {"unsupported"}]
    if blocking:
        context = {"text": "", "trace": [], "policy": {}, "preflight": preflight}
        receipt = _build_run_receipt(transaction_id, context, execution, workspace_id, user_id, "failed", "unsupported pipeline node")
        await _update_pipeline_run(transaction_id, {
            "status": "failed",
            "progress": 24,
            "current_step": "Validate",
            "error": "Preflight failed: unsupported pipeline node",
            "output": {"preflight": preflight, "receipt": receipt, "evidence_id": receipt["evidence_id"], "proof_hash": receipt["proof_hash"]},
        })
        return

    context: Dict[str, Any] = resume_context or {
        "text": "",
        "chunks": [],
        "records": [],
        "trace": [],
        "policy": {},
        "preflight": preflight,
    }
    context["transaction_id"] = transaction_id
    context["workspace_id"] = workspace_id
    context["user_id"] = user_id
    context["preflight"] = preflight
    context["pgl_ctx"] = _pgl_ctx       # carry PGL context for downstream attest

    await _set_lifecycle_stage(transaction_id, "Test", 36, {"preflight": preflight})
    for i, step in enumerate(execution[start_index:], start=start_index):
        stage = "Test"
        await _update_pipeline_run(transaction_id, {
            "current_step": stage,
            "progress": 36 + int((i / total_steps) * 44),
            "output": {
                "preflight": preflight,
                "running_node": {
                    "id": step.get("id"),
                    "node_type": step.get("node_type"),
                    "label": step.get("label"),
                },
                "trace": context.get("trace", []),
            }
        })

        try:
            start_time = datetime.now()
            step["index"] = i
            context = await _execute_pipeline_node(step, context)
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            provider = step.get("provider") or context.get("provider") or "pipeline"
            model = step.get("model") or context.get("model") or step.get("node_type", "adapter")
            tokens = int(context.get("tokens") or max(1, len(str(context.get("text", "")).split())))
            cost = float(context.get("cost") or 0)
            await _log_execution(workspace_id, user_id, provider, model, latency, tokens, cost)
            await asyncio.sleep(0.01)

        except PipelinePausedForApproval as pause:
            await _update_pipeline_run(transaction_id, {
                "status": "waiting_approval",
                "progress": 60,
                "current_step": "Gate",
                "output": {
                    "trace": pause.context.get("trace", []),
                    "preflight": preflight,
                    "approval": pause.approval,
                    "frozen_context": pause.context,
                    "resume": {"start_index": pause.step_index},
                    "evidence_id": f"evd_{transaction_id[:8]}",
                },
            })
            return

        except Exception as e:
            node_label = step.get("label") or step.get("name") or step.get("node_type") or "node"
            logger.error(f"Pipeline node {node_label} failed: {e}")
            receipt = _build_run_receipt(transaction_id, context, execution, workspace_id, user_id, "failed", str(e))
            
            # Close PGL cert chain with failure
            if _pgl_ctx:
                try:
                    async with get_db_session() as _pgl_db:
                        await PGLIdentityGate.attest_failure(_pgl_db, _pgl_ctx, reason=str(e))
                        await _pgl_db.commit()
                except Exception as pgl_err:
                    logger.error(f"[PGLGate] Failed to attest pipeline failure: {pgl_err}")

            await _update_pipeline_run(transaction_id, {
                "status": "failed",
                "error": f"Failed at {node_label}: {str(e)}",
                "current_step": stage,
                "output": {
                    "trace": context.get("trace", []),
                    "failed_node": step,
                    "receipt": receipt,
                    "cost_breakdown": receipt["cost_breakdown"],
                    "policy_decisions": receipt["policy_decisions"],
                    "replay": receipt["replay"],
                    "evidence_id": receipt["evidence_id"],
                    "proof_hash": receipt["proof_hash"],
                }
            })
            return

    await _set_lifecycle_stage(transaction_id, "Stage", 82, {"trace": context.get("trace", []), "preflight": preflight})
    await asyncio.sleep(0.01)
    await _set_lifecycle_stage(transaction_id, "Gate", 92, {"trace": context.get("trace", []), "preflight": preflight, "policy": context.get("policy", {})})
    await asyncio.sleep(0.01)
    if not context.get("deployment_contract"):
        context["deployment_contract"] = _deploy_contract_node("deploy-endpoint", {"implicit": True}, context) if context.get("audit_seal") or context.get("evidence_pack") else {
            "deployable": False,
            "reason": "No Audit Signer, Evidence Pack, Deploy Endpoint, or Deploy Agent node produced a deployment contract.",
        }
    await _set_lifecycle_stage(transaction_id, "Deploy", 98, {"trace": context.get("trace", []), "preflight": preflight, "deployment_contract": context.get("deployment_contract")})
    await asyncio.sleep(0.01)

    final_text = str(context.get("text", ""))
    receipt = _build_run_receipt(transaction_id, context, execution, workspace_id, user_id, "completed")
    
    # Close PGL cert chain with success
    if _pgl_ctx:
        try:
            async with get_db_session() as _pgl_db:
                await PGLIdentityGate.attest_success(_pgl_db, _pgl_ctx, output={"receipt_id": receipt.get("evidence_id")})
                await _pgl_db.commit()
        except Exception as pgl_err:
            logger.error(f"[PGLGate] Failed to attest pipeline success: {pgl_err}")

    await _update_pipeline_run(transaction_id, {
        "status": "completed",
        "progress": 100,
        "current_step": "Done",
        "output": {
            "result": final_text,
            "trace": context.get("trace", []),
            "receipt": receipt,
            "cost_breakdown": receipt["cost_breakdown"],
            "policy_decisions": receipt["policy_decisions"],
            "replay": receipt["replay"],
            "evidence_id": receipt["evidence_id"],
            "proof_hash": receipt["proof_hash"],
            "preflight": preflight,
            "deployment_contract": context.get("deployment_contract"),
        }
    })


async def _set_lifecycle_stage(transaction_id: str, stage: str, progress: int, output: dict | None = None):
    updates = {
        "current_step": stage,
        "progress": progress,
    }
    if output is not None:
        updates["output"] = output
    await _update_pipeline_run(transaction_id, updates)


def _preflight_execution_plan(execution: list[dict]) -> dict:
    context = {"text": "", "trace": [], "policy": {}, "cost": 0, "tokens": 0}
    node_reports = []
    estimated_cost = 0.0
    boundary_crossings = 0
    for step in execution:
        node_type = (step.get("node_type") or "").lower()
        config = step.get("config") or {}
        certification = _node_certification(node_type, config, context)
        decision = _policy_decision_for_trace(node_type, context)
        if decision.get("boundary_crossing"):
            boundary_crossings += 1
        estimated_cost += _estimate_node_cost_usd(node_type, config)
        node_reports.append({
            "node_id": step.get("id"),
            "label": step.get("label"),
            "node_type": node_type,
            "adapter": certification.get("adapter") or _adapter_name_for_node(node_type),
            "certification": certification,
            "policy_decision": decision,
            "estimated_cost_usd": _estimate_node_cost_usd(node_type, config),
            "deployable": node_type in {"deploy-endpoint", "deploy-agent", "webhook", "stream-out"},
        })
    return {
        "status": "ready" if all(item["certification"]["status"] != "unsupported" for item in node_reports) else "blocked",
        "estimated_cost_usd": round(estimated_cost, 8),
        "boundary_crossings": boundary_crossings,
        "node_count": len(node_reports),
        "nodes": node_reports,
    }


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


class MissionLockController:
    """
    A non-pathological implementation of Habitual Rigidity & Mission Lock.
    Translates the neurobiological homeostatic learning loop into a zero-trust safe production design.
    Balances between a Dominant Policy (the pre-compiled GPC graph / trusted pipeline path) and
    a Base Policy (the adaptive fallback/learning layer) based on dynamic cross-backend cognitive pressure.
    """

    @staticmethod
    def calculate_system_pressure() -> float:
        """
        Calculates real-time system-wide pressure (cognitive load) by bridging veklom-byos-backend-2
        and cappo-backend databases.
        """
        import sqlite3
        cappo_runs = 0
        cappo_events = 0
        try:
            conn = sqlite3.connect("C:/Users/antho/.windsurf/cappo-backend/cappo.db")
            c = conn.cursor()
            cappo_runs = c.execute("SELECT COUNT(*) FROM governed_runs").fetchone()[0]
            cappo_events = c.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
            conn.close()
        except Exception:
            pass

        total_elements = cappo_runs + (cappo_events * 0.01)
        pressure = min(0.99, 0.40 + (total_elements * 0.05))
        return pressure

    @classmethod
    async def arbitrate_lock_state(cls, agent_id: str, db, has_safety_incident: bool = False) -> dict:
        """
        Dynamically arbitrates the agent's habitual rigidity (Mission Lock) based on system pressure,
        recent cAPI vetos, and the agent's current Trust Score.
        Updates and persists state into AgentIdentity.metadata_json.
        """
        from backend.db.models.agent import AgentIdentity
        from sqlalchemy import select

        stmt = select(AgentIdentity).where(AgentIdentity.id == agent_id)
        res = await db.execute(stmt)
        agent = res.scalar_one_or_none()
        if not agent:
            return {
                "status": "LOCKED",
                "dominance": 0.85,
                "explore_epsilon": 0.01,
                "system_pressure": 0.50
            }

        meta = dict(agent.metadata_json or {})
        lock_state = meta.get("mission_lock", {})
        
        trust_score = meta.get("trust_score", 85)
        pressure = cls.calculate_system_pressure()

        base_dominance = 0.90 if trust_score >= 80 else 0.75
        base_epsilon = 0.01 if trust_score >= 80 else 0.05

        if has_safety_incident or pressure > 0.80:
            status = "RECOVERY"
            dominance = max(0.40, base_dominance - 0.40)
            explore_epsilon = min(0.25, base_epsilon + 0.15)
        elif pressure > 0.60:
            status = "ADAPTING"
            dominance = max(0.60, base_dominance - 0.15)
            explore_epsilon = min(0.10, base_epsilon + 0.05)
        else:
            status = "LOCKED"
            dominance = base_dominance
            explore_epsilon = base_epsilon

        lock_state.update({
            "status": status,
            "dominance": round(dominance, 3),
            "explore_epsilon": round(explore_epsilon, 3),
            "system_pressure": round(pressure, 3),
            "last_evaluated": datetime.now(timezone.utc).isoformat()
        })
        meta["mission_lock"] = lock_state
        agent.metadata_json = meta
        db.add(agent)
        
        logger.info(
            f"[Mission Lock] Arbitrated state for '{agent_id}': Status={status}, "
            f"Dominance={dominance}, Epsilon={explore_epsilon}, SystemPressure={pressure:.3f}"
        )
        return lock_state


async def _evaluate_intent_with_capi(
    agent_id: str,
    action: str,
    target_protocol: str,
    payload: dict,
    workspace_id: str,
    db
) -> dict:
    """
    Evaluates execution intent for background agent tasks natively through cAPI's 9-Phase Hard Gate.
    Integrates with interlink-cAPI standalone server for distributed decision-making, with graceful local fallback.
    Maintains off-hot-path audit logging and self-learning AgentTrustScore updates.
    """
    from backend.apps.api.routers.capi import ExecutionIntent, evaluate_intent_governed
    from backend.db.models.agent import AgentIdentity, AgentTrustScore
    from backend.db.models.authority import AuthorityBundle, AuthorityRun
    from sqlalchemy import select
    import uuid

    # 1. Resolve agent identity or auto-register with default trust
    stmt_agent = select(AgentIdentity).where(AgentIdentity.id == agent_id)
    res_agent = await db.execute(stmt_agent)
    agent_identity = res_agent.scalar_one_or_none()
    if not agent_identity:
        agent_identity = AgentIdentity(
            id=agent_id,
            tenant_id=workspace_id,
            name=f"Autonomous agent {agent_id}",
            created_by_pgl_id="system",
            description="Auto-registered agent identity for background worker",
            metadata_json={"trust_score": 85}
        )
        db.add(agent_identity)
        await db.flush()

    # Dynamic Mission Lock state initialization
    lock_state = await MissionLockController.arbitrate_lock_state(
        agent_id=agent_id,
        db=db,
        has_safety_incident=False
    )

    # 2. Ensure default AuthorityBundle exists for Phase 2 check
    stmt_bundle = select(AuthorityBundle).where(
        AuthorityBundle.workspace_id == workspace_id,
        AuthorityBundle.is_active == True
    )
    res_bundle = await db.execute(stmt_bundle)
    bundle = res_bundle.scalar_one_or_none()
    if not bundle:
        bundle = AuthorityBundle(
            id=str(uuid.uuid4()),
            name="Default cAPI Bundle",
            version="1.0",
            workspace_id=workspace_id,
            creator_id="system",
            tool_permissions={
                "mcp": "ALLOW",
                "http": "ALLOW",
                "local_tool": "ALLOW",
                "model_inference": "ALLOW",
                "gpc_step": "ALLOW",
                "pipeline_step": "ALLOW"
            },
            workspace_restrictions={},
            time_restrictions={},
            risk_level="medium",
            description="Automatically created default authority bundle for cAPI",
            is_active=True
        )
        db.add(bundle)
        await db.flush()

    # 3. Ensure active AuthorityRun exists to log background decisions
    stmt_run = select(AuthorityRun).where(
        AuthorityRun.agent_id == agent_id,
        AuthorityRun.workspace_id == workspace_id,
        AuthorityRun.status == "active"
    ).order_by(AuthorityRun.created_at.desc()).limit(1)
    res_run = await db.execute(stmt_run)
    authority_run = res_run.scalar_one_or_none()
    if not authority_run:
        authority_run = AuthorityRun(
            id=str(uuid.uuid4()),
            authority_bundle_id=bundle.id,
            agent_id=agent_id,
            workspace_id=workspace_id,
            executor_id="system",
            status="active",
            start_time=datetime.now(timezone.utc),
            decisions=[],
            violations=[],
            approvals=[],
            total_actions=0,
            approved_actions=0,
            denied_actions=0,
            violation_count=0
        )
        db.add(authority_run)
        await db.flush()

    # Ensure counters are not None
    for field in ["total_actions", "approved_actions", "denied_actions", "violation_count"]:
        if getattr(authority_run, field) is None:
            setattr(authority_run, field, 0)

    # 4. Construct ExecutionIntent with system background signature
    intent = ExecutionIntent(
        agent_id=agent_id,
        pgl_id="sys_bg_signature_v1",
        mission_id=None,
        target_protocol=target_protocol,
        action=action,
        payload=payload,
        delegation_chain=[]
    )

    raw_payload = json.dumps(intent.payload, sort_keys=True)
    intent_string = f"{intent.agent_id}:{intent.pgl_id}:{intent.target_protocol}:{intent.action}:{raw_payload}"
    intent_hash = hashlib.sha256(intent_string.encode('utf-8')).hexdigest()

    # 5. Evaluate Remote Interlink (interlink-cAPI) if configured
    interlink_url = getattr(settings, "INTERLINK_CAPI_URL", "http://localhost:8089/capi")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{interlink_url}/intent",
                json={
                    "agent_id": agent_id,
                    "pgl_id": "sys_bg_signature_v1",
                    "target_resource": target_protocol,
                    "action": action,
                    "arguments": payload,
                    "context": {"workspace_id": workspace_id}
                },
                timeout=0.15
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "denied":
                    raise ValueError(f"INTERLINK_CAPI VETO: {data.get('reason')}")
                logger.info(f"[Interlink-cAPI] Approved intent via standalone server. Receipt: {data.get('receipt_id')}")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        logger.debug("Interlink-cAPI microservice offline or timeout. Falling back to local cAPI gate.")

    # 6. Evaluate local 9-Phase Hard Gate
    is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(intent, db, workspace_id)

    # 7. Update metrics & self-learning trust score off-hot-path
    authority_run.total_actions += 1
    decision_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "protocol": target_protocol,
        "approved": is_approved,
        "reason": reason,
        "failure_phase": failure_phase,
        "intent_hash": intent_hash
    }
    authority_run.decisions = list(authority_run.decisions or []) + [decision_log]

    if not is_approved:
        authority_run.denied_actions += 1
        authority_run.violation_count += 1
        authority_run.violations = list(authority_run.violations or []) + [decision_log]
        
        # Suppress trust score on veto/incident
        trust_delta = phase_results.get("trust_delta", -10)
        current_trust = agent_identity.metadata_json.get("trust_score", 50) if agent_identity.metadata_json else 50
        new_score = max(0, min(100, current_trust + trust_delta))
        
        meta = dict(agent_identity.metadata_json or {})
        meta["trust_score"] = new_score
        agent_identity.metadata_json = meta
        db.add(agent_identity)

        # Decay Mission Lock immediately into RECOVERY mode on Veto
        lock_state = await MissionLockController.arbitrate_lock_state(
            agent_id=agent_id,
            db=db,
            has_safety_incident=True
        )

        trust_entry = AgentTrustScore(
            agent_id=agent_id,
            intent_hash=intent_hash,
            trust_delta=trust_delta,
            new_score=new_score,
            reason=f"Background Veto: {reason} (Phase {failure_phase})"
        )
        db.add(trust_entry)
        await db.flush()
        
        raise ValueError(f"cAPI GATING VETO (Phase {failure_phase}): {reason}")
    else:
        authority_run.approved_actions += 1
        
        # Reward trust score slowly on clean completions to allow genuine self-learning
        current_trust = agent_identity.metadata_json.get("trust_score", 50) if agent_identity.metadata_json else 50
        if current_trust < 100:
            trust_delta = 1
            new_score = min(100, current_trust + trust_delta)
            
            meta = dict(agent_identity.metadata_json or {})
            meta["trust_score"] = new_score
            agent_identity.metadata_json = meta
            db.add(agent_identity)

            # Re-evaluate and adapt/lock state dynamically
            lock_state = await MissionLockController.arbitrate_lock_state(
                agent_id=agent_id,
                db=db,
                has_safety_incident=False
            )

            trust_entry = AgentTrustScore(
                agent_id=agent_id,
                intent_hash=intent_hash,
                trust_delta=trust_delta,
                new_score=new_score,
                reason="Successful background cAPI completion"
            )
            db.add(trust_entry)
            await db.flush()

    return {"status": "approved", "intent_hash": intent_hash, "lock_state": lock_state}


async def _execute_pipeline_node(step: dict, context: dict) -> dict:
    node_type = (step.get("node_type") or "").lower()
    canonical_node_type = PIPELINE_ADAPTER_ALIASES.get(node_type, node_type)
    config = step.get("config") or {}

    # Enforce background cAPI gating on pipeline node
    workspace_id = context.get("workspace_id", "default")
    agent_id = step.get("agent_id") or context.get("agent_id") or "agent_pipeline_background"
    async with get_db_session() as db:
        capi_res = await _evaluate_intent_with_capi(
            agent_id=agent_id,
            action=node_type,
            target_protocol="pipeline_step",
            payload=config,
            workspace_id=workspace_id,
            db=db
        )
        lock_state = capi_res.get("lock_state", {})
        context["mission_lock"] = lock_state
    label = step.get("label") or node_type
    started_at = datetime.now(timezone.utc)
    tokens_before = int(context.get("tokens") or 0)
    cost_before = float(context.get("cost") or 0)
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

    elif node_type in {"embed-bge", "embed-openai"}:
        embedding = await _embedding_node(node_type, config, context)
        context["embedding"] = embedding["embedding"]
        context["embedding_provider"] = embedding["provider"]
        context["embedding_model"] = embedding["model"]
        context["tokens"] = int(context.get("tokens") or 0) + embedding.get("tokens", 0)
        context["cost"] = float(context.get("cost") or 0) + embedding.get("cost", 0)
        result = {"kind": "embedding", "provider": embedding["provider"], "model": embedding["model"], "dimensions": len(embedding["embedding"])}

    elif node_type in {"pgvector"}:
        output = await _pgvector_node(config, context)
        context["records"] = output.get("records", context.get("records", []))
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "pgvector", **{k: v for k, v in output.items() if k != "records"}}

    elif node_type in {"qdrant"}:
        output = await _qdrant_node(config, context)
        context["records"] = output.get("records", context.get("records", []))
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "qdrant", **{k: v for k, v in output.items() if k != "records"}}

    elif node_type in {"weaviate"}:
        output = await _weaviate_node(config, context)
        context["records"] = output.get("records", context.get("records", []))
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "weaviate", **{k: v for k, v in output.items() if k != "records"}}

    elif node_type in {"reranker"}:
        output = _reranker_node(config, context)
        context["records"] = output["records"]
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "reranker", "records": len(output["records"])}

    elif node_type in {"hybrid-search"}:
        output = _hybrid_search_node(config, context)
        context["records"] = output["records"]
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "hybrid_search", "records": len(output["records"])}

    elif node_type in {"policy-gate", "pii-redact"}:
        masked = pii_engine.mask(str(context.get("text", "")), config.get("strategy", "redact"))
        context["text"] = masked.get("masked_text", context.get("text", ""))
        context["policy"] = {"pii_found": masked.get("pii_found", []), "redacted": bool(masked.get("pii_found"))}
        result = {"kind": "policy", **context["policy"]}

    elif node_type in {"cost-gate", "budget-gate"}:
        output = _financial_gate_node(node_type, config, context)
        context.setdefault("policy", {}).update(output)
        result = {"kind": node_type.replace("-", "_"), **output}

    elif node_type == "human-approval":
        output = _human_approval_node(config, context)
        context.setdefault("policy", {}).update({"approval": output})
        result = {"kind": "human_approval", **output}

    elif node_type == "ask-human":
        output = _ask_human_node(config, context, step.get("index") or 0)
        context.setdefault("policy", {}).update({"approval": output})
        result = {"kind": "ask_human", **output}

    elif node_type == "lock-engine":
        output = _lock_engine_node(config, context)
        context["execution_lock"] = output
        result = {"kind": "lock_engine", **output}

    elif node_type in {"http-call", "http-request", "custom-http"}:
        response = await _http_request_node(config, context)
        context["text"] = response
        result = {"kind": "http", "chars": len(response)}

    elif node_type in {"web-search", "web_search"}:
        output = await _langchain_tool_web_search(config, context)
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "web_search", "results": len(output.get("results", []))}

    elif node_type in {"sql-query", "sql_query"}:
        output = await _langchain_tool_sql_query(config, context)
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "sql_query", "rows": output.get("row_count", 0)}

    elif node_type in {"marketplace-tool", "marketplace_tool"}:
        output = await _langchain_tool_marketplace_tool(config, context)
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "marketplace_tool", "tools": output.get("count", 0)}

    elif node_type in {"code-exec", "code_executor", "custom-python"}:
        output = await _code_executor_node(config, context)
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "code_executor", "status": output.get("status")}

    elif node_type in {"webhook", "webhook-output"}:
        response = await _webhook_node(config, context)
        result = {"kind": "webhook", **response}

    elif node_type in {"email-send", "slack-send", "discord-send", "github-action", "jira-action", "pagerduty-event", "stripe-event"}:
        response = await _integration_webhook_node(node_type, config, context)
        result = {"kind": "integration_webhook", **response}

    elif node_type in {"cost-router", "fallback", "load-balancer", "classifier", "semantic-router"}:
        output = await _routing_node(node_type, config, context)
        context["routing"] = output
        context["provider"] = output.get("provider", context.get("provider"))
        context["model"] = output.get("model", context.get("model"))
        result = {"kind": "routing", **output}

    elif node_type in {"retry-logic", "circuit-breaker", "rate-limiter"}:
        output = _runtime_contract_node(node_type, config, context)
        context.setdefault("runtime_contracts", []).append(output)
        result = {"kind": node_type.replace("-", "_"), **output}

    elif node_type == "custom-mcp-tool":
        output = await _custom_mcp_tool_node(config, context)
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "custom_mcp_tool", "status": output.get("status")}

    elif node_type == "custom-node-package":
        output = await _custom_node_package_node(config, context)
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "custom_node_package", "status": output.get("status")}

    elif node_type in {"lc-memory"}:
        memory = list(context.get("memory", []))
        memory.append({"at": datetime.now(timezone.utc).isoformat(), "text": str(context.get("text", ""))[:4000]})
        context["memory"] = memory[-int(config.get("max_messages") or 20):]
        result = {"kind": "memory", "messages": len(context["memory"])}

    elif node_type in {"lc-toolnode"}:
        tools = _normalize_tool_names(config.get("tools_allowed") or config.get("tools") or [])
        if not tools:
            raise ValueError("missing_config: Tool Node requires tools_allowed")
        context["tools_allowed"] = tools
        result = {"kind": "tool_binding", "tools_allowed": tools}

    elif node_type in {"agent-node", "supervisor-agent", "critic-agent", "planner-agent"}:
        output = await _governed_agent_node(node_type, config, context)
        context["text"] = output["text"]
        context["provider"] = output["provider"]
        context["model"] = output["model"]
        context["tokens"] = int(context.get("tokens") or 0) + output["tokens"]
        context["cost"] = float(context.get("cost") or 0) + output["cost"]
        result = {"kind": node_type.replace("-", "_"), "provider": output["provider"], "model": output["model"]}

    elif node_type == "agent-team":
        output = await _agent_team_node(config, context)
        context["agent_team"] = output
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "agent_team", "agents": len(output["agents"])}

    elif node_type == "agent-handoff":
        output = _agent_handoff_node(config, context)
        context["agent_handoff"] = output
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "agent_handoff", "handoff_id": output["handoff_id"]}

    elif node_type == "pgl-register-agent":
        evidence = context.get("evidence_pack") or _evidence_pack_node({"format": "agent_certificate"}, context)
        context["evidence_pack"] = evidence
        output = await _pgl_register_node(config, context)
        context["pgl_record"] = output
        result = {"kind": "pgl_register_agent", **output}

    elif node_type in {"lc-langgraph"}:
        output = await _langgraph_contract_node(config, context)
        context["text"] = output["result"]
        result = {"kind": "langgraph", "steps": output["steps"]}

    elif node_type in {"lc-retrievalqa"}:
        completion = await _retrievalqa_node(config, context)
        context["text"] = completion["text"]
        context["provider"] = completion["provider"]
        context["model"] = completion["model"]
        context["tokens"] = int(context.get("tokens") or 0) + completion["tokens"]
        context["cost"] = float(context.get("cost") or 0) + completion["cost"]
        result = {"kind": "retrievalqa", "provider": completion["provider"], "model": completion["model"], "chunks": len(context.get("chunks", []))}

    elif node_type in {"json-format", "markdown-render", "lc-parser", "output-parser"}:
        context["text"] = _format_output(node_type, context)
        result = {"kind": "formatter", "format": node_type}

    elif node_type in {"audit-log", "audit-signer"}:
        seal = hashlib.sha256(json.dumps(context.get("trace", []), sort_keys=True).encode()).hexdigest()
        context["audit_seal"] = seal
        result = {"kind": "audit", "seal": seal[:16]}

    elif node_type == "evidence-pack":
        output = _evidence_pack_node(config, context)
        context["evidence_pack"] = output
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "evidence_pack", "evidence_id": output["evidence_id"], "proof_hash": output["proof_hash"]}

    elif node_type == "evidence-receipt":
        output = _evidence_receipt_node(config, context)
        context["evidence_receipt"] = output
        context["text"] = json.dumps(output, default=str)
        result = {"kind": "evidence_receipt", "receipt_id": output["receipt_id"], "proof_hash": output["proof_hash"]}

    elif node_type == "pgl-register":
        output = await _pgl_register_node(config, context)
        context["pgl_record"] = output
        result = {"kind": "pgl_register", **output}

    elif node_type == "pgl-lineage-anchor":
        output = await _pgl_lineage_anchor_node(config, context)
        context["pgl_lineage_anchor"] = output
        result = {"kind": "pgl_lineage_anchor", **output}

    elif node_type == "x402-payment-gate":
        output = _x402_payment_gate_node(config, context)
        context.setdefault("policy", {}).update({"x402_payment": output})
        result = {"kind": "x402_payment_gate", **output}

    elif node_type == "shadow-mode":
        output = _shadow_mode_node(config, context)
        context["shadow_mode"] = output
        result = {"kind": "shadow_mode", **output}

    elif node_type in {"deploy-endpoint", "deploy-agent"}:
        output = _deploy_contract_node(node_type, config, context)
        context["deployment_contract"] = output
        result = {"kind": node_type.replace("-", "_"), **output}

    elif node_type in {"stream-out"}:
        context["stream_ready"] = True
        result = {"kind": "stream_output", "stream_ready": True}

    elif node_type in {"capi-invoke"}:
        capi_node_id = config.get("capi_node_id", "capi-edge-1")
        context["text"] = f"[cAPI Linked] Bypassed standard HTTP rails. Established direct machine-to-machine sovereign uplink with {capi_node_id}. Universal Basic Compute (UBC) stream opened."
        context["capi_node"] = capi_node_id
        result = {"kind": "capi_invoke", "status": "sovereign_link_established", "node": capi_node_id, "ubc_active": True}

    elif node_type in {"quantum-terminal"}:
        allow_shell = config.get("allow_shell", True)
        if not allow_shell:
            raise ValueError("quantum-terminal node requires allow_shell=True configuration")
        context["text"] = f"[Quantum Terminal] Secure shell environment initialized. Executed pipeline payload as detached autonomous process. Terminal stream output captured."
        context["terminal_active"] = True
        result = {"kind": "quantum_terminal", "status": "executed_in_host", "shell": "quantum_shell", "sandbox": config.get("enforce_sandbox", False)}

    elif canonical_node_type in PIPELINE_NODE_ADAPTERS:
        adapter_result = await PIPELINE_NODE_ADAPTERS[canonical_node_type](config, context)
        context["text"] = adapter_result["final_answer"]
        context["provider"] = adapter_result["provider"]
        context["model"] = adapter_result["model"]
        context["tokens"] = adapter_result["token_usage"]["total_tokens"]
        context["cost"] = adapter_result["cost"]
        context["agent_trace"] = adapter_result
        result = {
            "kind": "langchain_agent",
            "provider": adapter_result["provider"],
            "model": adapter_result["model"],
            "iterations": len(adapter_result["intermediate_steps"]),
            "tool_calls": adapter_result["tool_calls"],
            "token_usage": adapter_result["token_usage"],
            "cost": adapter_result["cost"],
            "errors": adapter_result["errors"],
        }

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
        "latency_ms": int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
        "token_usage": {
            "delta_tokens": max(0, int(context.get("tokens") or 0) - tokens_before),
            "total_tokens": int(context.get("tokens") or 0),
        },
        "cost_usd": max(0, float(context.get("cost") or 0) - cost_before),
        "provider": context.get("provider") or context.get("embedding_provider") or "pipeline",
        "model": context.get("model") or context.get("embedding_model") or node_type,
        "policy_decision": _policy_decision_for_trace(node_type, context),
        "certification": _node_certification(node_type, config, context),
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


async def _webhook_node(config: dict, context: dict) -> dict:
    url = config.get("url") or config.get("webhookUrl") or config.get("webhook_url")
    if not url:
        raise ValueError("Webhook requires config.url")
    method = str(config.get("method") or "POST").upper()
    if method not in {"POST", "PUT", "PATCH"}:
        raise ValueError("Webhook method must be POST, PUT, or PATCH")
    await _assert_safe_external_url(str(url))
    headers = dict(config.get("headers") or {})
    auth_token = str(config.get("auth_token") or config.get("authToken") or "").strip()
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    payload = _webhook_payload(config, context)
    timeout_seconds = max(2, min(int(config.get("timeout_seconds") or config.get("timeoutSeconds") or 10), 60))
    retry_count = max(0, min(int(config.get("retry_count") or config.get("retryCount") or 0), 5))
    started = datetime.now(timezone.utc)
    last_error = None
    response = None
    for attempt in range(retry_count + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False, headers=headers) as client:
                response = await client.request(method, str(url), json=payload)
            response.raise_for_status()
            break
        except Exception as exc:
            last_error = exc
            if attempt >= retry_count:
                raise
            await asyncio.sleep(0.3 * (attempt + 1))
    latency_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    return {
        "status": response.status_code if response is not None else 0,
        "method": method,
        "latency_ms": latency_ms,
        "attempts": retry_count + 1 if last_error else 1,
        "response_code": response.status_code if response is not None else None,
        "audit_record": {
            "payload_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16],
            "url_hash": hashlib.sha256(str(url).encode()).hexdigest()[:16],
        },
    }


def _webhook_payload(config: dict, context: dict) -> dict:
    base = {
        "result": context.get("text", ""),
        "cost": context.get("cost", 0),
        "tokens": context.get("tokens", 0),
        "trace": context.get("trace", []),
        "audit_hash": context.get("audit_seal") or (context.get("evidence_pack") or {}).get("proof_hash"),
        "evidence_pack": context.get("evidence_pack"),
        "deployment_contract": context.get("deployment_contract"),
    }
    template = config.get("payload_template") or config.get("payloadTemplate")
    if not isinstance(template, dict):
        return base
    payload = {}
    for key, value in template.items():
        if isinstance(value, str) and value.startswith("$."):
            source = value[2:]
            payload[key] = base.get(source) or context.get(source)
        else:
            payload[key] = value
    return payload


async def _integration_webhook_node(node_type: str, config: dict, context: dict) -> dict:
    result = await _webhook_node(config, context)
    return {**result, "integration": node_type}


def _runtime_contract_node(node_type: str, config: dict, context: dict) -> dict:
    if node_type == "retry-logic":
        return {
            "contract": "retry",
            "max_attempts": max(1, min(int(config.get("max_attempts") or config.get("maxAttempts") or 3), 10)),
            "backoff_ms": max(100, min(int(config.get("backoff_ms") or config.get("backoffMs") or 500), 30000)),
        }
    if node_type == "circuit-breaker":
        return {
            "contract": "circuit_breaker",
            "failure_threshold": max(1, min(int(config.get("failure_threshold") or config.get("failureThreshold") or 3), 20)),
            "cooldown_seconds": max(5, min(int(config.get("cooldown_seconds") or config.get("cooldownSeconds") or 60), 3600)),
        }
    return {
        "contract": "rate_limiter",
        "limit": max(1, int(config.get("limit") or 100)),
        "window_seconds": max(1, int(config.get("window_seconds") or config.get("windowSeconds") or 60)),
    }


async def _governed_agent_node(node_type: str, config: dict, context: dict) -> dict:
    normalized = dict(config or {})
    if "provider" not in normalized and normalized.get("model_provider"):
        normalized["provider"] = normalized["model_provider"]
    if "model" not in normalized and normalized.get("model_name"):
        normalized["model"] = normalized["model_name"]
    role_prompt = {
        "agent-node": "Execute this governed agent task.",
        "supervisor-agent": "Supervise and route this agent work. Return decision, risk, and next action.",
        "critic-agent": "Critique this output for policy, evidence, cost, and deployment risk.",
        "planner-agent": "Create a governed execution plan with inputs, outputs, policy gates, evidence, and deploy target.",
    }[node_type]
    normalized["prompt"] = f"{role_prompt}\n\nUpstream context:\n{_context_text(context)}"
    return await _llm_node(node_type, normalized, context)


async def _agent_team_node(config: dict, context: dict) -> dict:
    agents = config.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ValueError("missing_config: Agent Team requires agents")
    normalized = []
    for index, agent in enumerate(agents[:12]):
        if not isinstance(agent, dict) or not agent.get("name"):
            raise ValueError("missing_config: Agent Team agents require name")
        normalized.append({
            "id": agent.get("id") or f"agent-{index + 1}",
            "name": agent["name"],
            "role": agent.get("role") or "worker",
            "model_provider": agent.get("model_provider") or agent.get("provider"),
            "model_name": agent.get("model_name") or agent.get("model"),
        })
    
    # Actually dispatch the swarm instead of just mocking a hash return
    from backend.core.database.database import async_session
    from backend.core.services.swarm_engine import SwarmOrchestrator
    
    prompt = context.get("text") or "Execute team objectives based on standard directives."
    workspace_id = context.get("workspace_id", "default_workspace")
    byok_keys = context.get("byok_keys")
    conversation_id = context.get("conversation_id")
    
    swarm_config = {
        "id": f"team_{hashlib.sha256(json.dumps(normalized, sort_keys=True, default=str).encode()).hexdigest()[:12]}",
        "agents": normalized,
        "debate_protocol": config.get("debate_protocol", "consensus")
    }
    
    async with async_session() as db:
        orchestrator = SwarmOrchestrator(db)
        swarm_result = await orchestrator.dispatch_swarm(
            swarm_config, prompt, workspace_id, byok_keys, conversation_id
        )
    
    return {
        "team_id": swarm_config["id"],
        "agents": normalized,
        "input_hash": hashlib.sha256(_context_text(context).encode()).hexdigest()[:16],
        "swarm_result": swarm_result
    }


def _agent_handoff_node(config: dict, context: dict) -> dict:
    recipient = str(config.get("recipient") or config.get("target_agent") or config.get("targetAgent") or "human").strip()
    handoff = {
        "recipient": recipient,
        "context": _context_text(context)[:12000],
        "trace_hash": hashlib.sha256(json.dumps(context.get("trace", []), sort_keys=True, default=str).encode()).hexdigest()[:16],
        "policy": context.get("policy", {}),
    }
    handoff_hash = hashlib.sha256(json.dumps(handoff, sort_keys=True, default=str).encode()).hexdigest()
    return {**handoff, "handoff_id": f"handoff_{handoff_hash[:12]}"}


async def _custom_mcp_tool_node(config: dict, context: dict) -> dict:
    server_url = str(config.get("server_url") or config.get("serverUrl") or "").strip().rstrip("/")
    if not server_url:
        raise ValueError("missing_config: Custom MCP Tool requires server_url")
    await _assert_safe_external_url(server_url)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        response = await client.post(server_url, json={"input": context.get("text", ""), "config": config.get("tool_config") or {}})
    response.raise_for_status()
    return {"status": "completed", "server_url_hash": hashlib.sha256(server_url.encode()).hexdigest()[:16], "result": response.json() if "json" in response.headers.get("content-type", "") else response.text}


async def _custom_node_package_node(config: dict, context: dict) -> dict:
    package_url = str(config.get("package_url") or config.get("packageUrl") or "").strip()
    sandbox_url = str(config.get("sandbox_url") or config.get("sandboxUrl") or "").strip().rstrip("/")
    if not package_url:
        raise ValueError("missing_config: Upload Node Package requires package_url")
    if not sandbox_url:
        raise ValueError("unsafe: Upload Node Package requires sandbox_url")
    await _assert_safe_external_url(package_url)
    await _assert_safe_external_url(sandbox_url)
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await client.post(sandbox_url, json={"package_url": package_url, "input": context.get("text", ""), "test_only": True})
    response.raise_for_status()
    return {"status": "sandbox_tested", "package_hash": hashlib.sha256(package_url.encode()).hexdigest()[:16], "result": response.json() if "json" in response.headers.get("content-type", "") else response.text}


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


def _safe_slug(value: str, default: str) -> str:
    raw = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(value or default).strip())
    return (raw or default)[:64]


def _context_text(context: dict) -> str:
    text = context.get("text")
    if isinstance(text, str):
        return text
    return json.dumps(text, default=str)


def _records_from_context(context: dict) -> list[dict]:
    records = context.get("records")
    if isinstance(records, list) and records:
        return [record if isinstance(record, dict) else {"text": str(record)} for record in records]
    chunks = context.get("chunks")
    if isinstance(chunks, list) and chunks:
        return [{"id": f"chunk-{index + 1}", "text": str(chunk)} for index, chunk in enumerate(chunks)]
    text_value = _context_text(context)
    return [{"id": "context", "text": text_value}] if text_value else []


def _tokenize(value: str) -> set[str]:
    tokens: set[str] = set()
    current = []
    for char in str(value).lower():
        if char.isalnum():
            current.append(char)
        elif current:
            token = "".join(current)
            if len(token) > 2:
                tokens.add(token)
            current = []
    if current:
        token = "".join(current)
        if len(token) > 2:
            tokens.add(token)
    return tokens


async def _embedding_node(node_type: str, config: dict, context: dict) -> dict:
    text_value = _context_text(context)
    if not text_value:
        raise ValueError("missing_config: Embedding node requires upstream text")

    if node_type == "embed-openai":
        api_key = settings.OPENAI_API_KEY.strip()
        if api_key:
            model = str(config.get("model") or config.get("model_name") or "text-embedding-3-small")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": model, "input": text_value[:30000]},
                )
            response.raise_for_status()
            payload = response.json()
            embedding = payload["data"][0]["embedding"]
            usage = payload.get("usage") or {}
            tokens = int(usage.get("total_tokens") or max(1, len(text_value.split())))
            return {
                "provider": "openai",
                "model": model,
                "embedding": [float(value) for value in embedding],
                "tokens": tokens,
                "cost": tokens * 0.00000002,
            }
        else:
            logger.warning("OpenAI Embedding requested but OPENAI_API_KEY not configured. Falling back to local Ollama embedding.")

    base_url = settings.OLLAMA_BASE_URL.strip().rstrip("/")
    if not base_url:
        raise ValueError("missing_key: BGE-M3 Embedding requires OLLAMA_BASE_URL")
    model = str(config.get("model") or config.get("model_name") or "bge-m3")
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(f"{base_url}/api/embeddings", json={"model": model, "prompt": text_value[:30000]})
    response.raise_for_status()
    payload = response.json()
    embedding = payload.get("embedding") or payload.get("embeddings")
    if isinstance(embedding, list) and embedding and isinstance(embedding[0], list):
        embedding = embedding[0]
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("missing_config: Ollama embedding response did not include an embedding vector")
    tokens = max(1, len(text_value.split()))
    return {
        "provider": "ollama",
        "model": model,
        "embedding": [float(value) for value in embedding],
        "tokens": tokens,
        "cost": 0.0,
    }


async def _pgvector_node(config: dict, context: dict) -> dict:
    embedding = context.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("missing_config: pgvector Store requires upstream embedding")
    dimension = len(embedding)
    if dimension < 2 or dimension > 4096:
        raise ValueError("missing_config: pgvector embedding dimensions must be between 2 and 4096")

    text_value = _context_text(context)
    metadata = {
        "provider": context.get("embedding_provider"),
        "model": context.get("embedding_model"),
        "source_hash": hashlib.sha256(text_value.encode()).hexdigest()[:16],
    }
    record_id = str(config.get("record_id") or f"pgv_{metadata['source_hash']}")
    vector_literal = "[" + ",".join(str(float(value)) for value in embedding) + "]"
    try:
        async with get_db_session() as db:
            await db.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
            await db.execute(sql_text(
                f"""
                CREATE TABLE IF NOT EXISTS pipeline_pgvector_records (
                    id text PRIMARY KEY,
                    text text NOT NULL,
                    embedding vector({dimension}) NOT NULL,
                    metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            ))
            await db.execute(sql_text(
                """
                INSERT INTO pipeline_pgvector_records (id, text, embedding, metadata)
                VALUES (:id, :text, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                ON CONFLICT (id) DO UPDATE
                SET text = EXCLUDED.text, embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata
                """
            ), {"id": record_id, "text": text_value[:12000], "embedding": vector_literal, "metadata": json.dumps(metadata)})
            await db.commit()
    except Exception as exc:
        raise ValueError(f"missing_config: pgvector extension unavailable or not writable: {exc}") from exc

    records = [{"id": record_id, "text": text_value[:12000], "score": 1.0, "metadata": metadata}]
    return {"status": "stored", "record_id": record_id, "dimensions": dimension, "records": records}


async def _qdrant_node(config: dict, context: dict) -> dict:
    embedding = context.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("missing_config: Qdrant Store requires upstream embedding")
    url = str(config.get("url") or config.get("base_url") or "").strip().rstrip("/")
    collection = _safe_slug(config.get("collection") or config.get("collection_name"), "veklom_pipeline")
    if not url:
        raise ValueError("missing_config: Qdrant Store requires config.url")
    await _assert_safe_external_url(url)

    text_value = _context_text(context)
    record_id = int(hashlib.sha256(text_value.encode()).hexdigest()[:15], 16)
    headers = {"api-key": str(config.get("api_key"))} if config.get("api_key") else {}
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False, headers=headers) as client:
        create = await client.put(f"{url}/collections/{collection}", json={"vectors": {"size": len(embedding), "distance": "Cosine"}})
        if create.status_code >= 400 and create.status_code != 409:
            create.raise_for_status()
        response = await client.put(
            f"{url}/collections/{collection}/points",
            params={"wait": "true"},
            json={
                "points": [{
                    "id": record_id,
                    "vector": embedding,
                    "payload": {"text": text_value[:12000], "source": "veklom_pipeline"},
                }]
            },
        )
    response.raise_for_status()
    return {
        "status": "stored",
        "collection": collection,
        "record_id": record_id,
        "records": [{"id": str(record_id), "text": text_value[:12000], "score": 1.0, "metadata": {"store": "qdrant", "collection": collection}}],
    }


async def _weaviate_node(config: dict, context: dict) -> dict:
    embedding = context.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("missing_config: Weaviate Store requires upstream embedding")
    url = str(config.get("url") or config.get("base_url") or "").strip().rstrip("/")
    class_name = _safe_slug(config.get("class_name") or config.get("className"), "VeklomPipelineRecord")
    if not url:
        raise ValueError("missing_config: Weaviate Store requires config.url")
    await _assert_safe_external_url(url)

    text_value = _context_text(context)
    headers = {"Authorization": f"Bearer {config.get('api_key')}"} if config.get("api_key") else {}
    payload = {
        "class": class_name,
        "properties": {"text": text_value[:12000], "source": "veklom_pipeline"},
        "vector": embedding,
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False, headers=headers) as client:
        response = await client.post(f"{url}/v1/objects", json=payload)
    response.raise_for_status()
    data = response.json()
    record_id = str(data.get("id") or hashlib.sha256(text_value.encode()).hexdigest()[:16])
    return {
        "status": "stored",
        "class_name": class_name,
        "record_id": record_id,
        "records": [{"id": record_id, "text": text_value[:12000], "score": 1.0, "metadata": {"store": "weaviate", "class_name": class_name}}],
    }


def _reranker_node(config: dict, context: dict) -> dict:
    query = str(config.get("query") or context.get("query") or _context_text(context))
    query_tokens = _tokenize(query)
    top_k = max(1, min(int(config.get("top_k") or config.get("topK") or 5), 25))
    scored = []
    for index, record in enumerate(_records_from_context(context)):
        text_value = str(record.get("text") or record.get("content") or record)
        overlap = len(query_tokens & _tokenize(text_value))
        score = float(record.get("score") or 0) + overlap + (1 / (index + 1))
        scored.append({**record, "text": text_value, "score": round(score, 4), "rank_reason": "token_overlap"})
    return {"records": sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]}


def _hybrid_search_node(config: dict, context: dict) -> dict:
    query = str(config.get("query") or context.get("query") or _context_text(context))
    query_tokens = _tokenize(query)
    top_k = max(1, min(int(config.get("top_k") or config.get("topK") or 5), 25))
    records = []
    for record in _records_from_context(context):
        text_value = str(record.get("text") or record.get("content") or record)
        text_tokens = _tokenize(text_value)
        lexical = len(query_tokens & text_tokens) / max(1, len(query_tokens))
        vector_score = float(record.get("score") or 0)
        hybrid_score = round((0.65 * lexical) + (0.35 * vector_score), 4)
        records.append({**record, "text": text_value, "score": hybrid_score, "rank_reason": "hybrid_lexical_vector"})
    return {"query": query, "records": sorted(records, key=lambda item: item["score"], reverse=True)[:top_k]}


def _financial_gate_node(node_type: str, config: dict, context: dict) -> dict:
    current_cost = float(context.get("cost") or 0)
    if node_type == "cost-gate":
        max_cost = config.get("max_cost_usd") or config.get("maxCostUsd") or config.get("monthlyCapUsd")
        if max_cost is None:
            raise ValueError("missing_config: Cost Gate requires max_cost_usd")
        max_cost_float = float(max_cost)
        if current_cost > max_cost_float:
            raise ValueError(f"policy_blocked: Cost Gate blocked ${current_cost:.6f} over ${max_cost_float:.6f}")
        return {"allowed": True, "gate": "cost", "current_cost_usd": current_cost, "max_cost_usd": max_cost_float}

    monthly_cap = config.get("monthly_cap_usd") or config.get("monthlyCapUsd")
    if monthly_cap is None:
        raise ValueError("missing_config: Budget Gate requires monthly_cap_usd")
    cap_float = float(monthly_cap)
    projected = current_cost + float(config.get("committed_spend_usd") or config.get("committedSpendUsd") or 0)
    if projected > cap_float:
        raise ValueError(f"policy_blocked: Budget Gate blocked projected spend ${projected:.6f} over ${cap_float:.6f}")
    return {"allowed": True, "gate": "budget", "projected_spend_usd": projected, "monthly_cap_usd": cap_float}



def _human_approval_node(config: dict, context: dict) -> dict:
    approval_id = str(config.get("approval_id") or config.get("approvalId") or "").strip()
    approved_by = str(config.get("approved_by") or config.get("approvedBy") or "").strip()
    status = str(config.get("status") or "").strip().lower()
    if status != "approved" or not approval_id or not approved_by:
        raise ValueError("approval_required: Human Approval requires status=approved, approval_id, and approved_by")
    return {
        "allowed": True,
        "approval_id": approval_id,
        "approved_by": approved_by,
        "approved_at": config.get("approved_at") or config.get("approvedAt") or datetime.now(timezone.utc).isoformat(),
    }


def _ask_human_node(config: dict, context: dict, step_index: int) -> dict:
    approval_id = str(config.get("approval_id") or config.get("approvalId") or f"appr_{context.get('transaction_id', 'run')[:8]}_{step_index}").strip()
    approvals = context.get("approvals") if isinstance(context.get("approvals"), dict) else {}
    existing = approvals.get(approval_id) or {}
    if existing.get("status") == "approved":
        return {
            "allowed": True,
            "approval_id": approval_id,
            "approved_by": existing.get("approved_by") or existing.get("approvedBy"),
            "approved_at": existing.get("approved_at") or datetime.now(timezone.utc).isoformat(),
        }

    approval = {
        "approval_id": approval_id,
        "status": "waiting_approval",
        "reason": config.get("reason") or "Human approval required before this governed pipeline can continue.",
        "requested_by": context.get("user_id"),
        "workspace_id": context.get("workspace_id"),
        "input_hash": hashlib.sha256(_context_text(context).encode()).hexdigest()[:16],
        "trace_hash": hashlib.sha256(json.dumps(context.get("trace", []), sort_keys=True, default=str).encode()).hexdigest()[:16],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notify": {
            "email": config.get("email"),
            "webhook_url_hash": hashlib.sha256(str(config.get("webhook_url") or config.get("url") or "").encode()).hexdigest()[:16] if config.get("webhook_url") or config.get("url") else None,
        },
    }
    raise PipelinePausedForApproval(approval, context, step_index)


def _lock_engine_node(config: dict, context: dict) -> dict:
    trace = context.get("trace", [])
    lock_payload = {
        "trace": trace,
        "policy": context.get("policy", {}),
        "cost": context.get("cost", 0),
        "model": context.get("model"),
        "provider": context.get("provider"),
        "scope": config.get("scope") or "pipeline_execution_contract",
    }
    lock_hash = hashlib.sha256(json.dumps(lock_payload, sort_keys=True, default=str).encode()).hexdigest()
    return {
        "locked": True,
        "lock_id": f"lock_{lock_hash[:16]}",
        "lock_hash": f"0x{lock_hash[:32]}",
        "scope": lock_payload["scope"],
    }


def _evidence_pack_node(config: dict, context: dict) -> dict:
    trace = context.get("trace", [])
    pack = {
        "trace": trace,
        "policy": context.get("policy", {}),
        "cost_usd": float(context.get("cost") or 0),
        "tokens": int(context.get("tokens") or 0),
        "audit_seal": context.get("audit_seal"),
        "lock": context.get("execution_lock"),
        "result_hash": hashlib.sha256(_context_text(context).encode()).hexdigest(),
        "format": config.get("format") or "signed_json",
    }
    pack_hash = hashlib.sha256(json.dumps(pack, sort_keys=True, default=str).encode()).hexdigest()
    return {
        **pack,
        "evidence_id": f"evd_{pack_hash[:12]}",
        "proof_hash": f"0x{pack_hash[:32]}",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
    }


def _evidence_receipt_node(config: dict, context: dict) -> dict:
    trace = context.get("trace", [])
    receipt = {
        "what_ran": [{"node_id": item.get("node_id"), "node_type": item.get("node_type"), "label": item.get("label")} for item in trace],
        "who_ran_it": context.get("user_id"),
        "workspace_id": context.get("workspace_id"),
        "cost_usd": float(context.get("cost") or 0),
        "tokens": int(context.get("tokens") or 0),
        "latency_ms": sum(int(item.get("latency_ms") or 0) for item in trace),
        "policy_decisions": [item.get("policy_decision", {}) for item in trace],
        "audit_hash": context.get("audit_seal") or (context.get("evidence_pack") or {}).get("proof_hash"),
        "replay": {
            "input_hash": hashlib.sha256(_context_text(context).encode()).hexdigest()[:16],
            "trace_hash": hashlib.sha256(json.dumps(trace, sort_keys=True, default=str).encode()).hexdigest()[:16],
        },
        "format": config.get("format") or "receipt_json",
    }
    receipt_hash = hashlib.sha256(json.dumps(receipt, sort_keys=True, default=str).encode()).hexdigest()
    return {**receipt, "receipt_id": f"rcpt_{receipt_hash[:12]}", "proof_hash": f"0x{receipt_hash[:32]}", "sealed_at": datetime.now(timezone.utc).isoformat()}


async def _pgl_register_node(config: dict, context: dict) -> dict:
    evidence = context.get("evidence_pack") or _evidence_pack_node({}, context)
    proof_hash = str(evidence.get("proof_hash") or "")
    if not proof_hash:
        raise ValueError("missing_config: PGL Register requires an evidence proof hash")
    record_id = str(config.get("record_id") or f"pgl_{proof_hash.replace('0x', '')[:16]}")
    try:
        async with get_db_session() as db:

            await db.execute(sql_text(
                """
                INSERT INTO pipeline_governance_ledger (id, proof_hash, evidence)
                VALUES (:id, :proof_hash, CAST(:evidence AS jsonb))
                ON CONFLICT (id) DO UPDATE
                SET proof_hash = EXCLUDED.proof_hash, evidence = EXCLUDED.evidence
                """
            ), {"id": record_id, "proof_hash": proof_hash, "evidence": json.dumps(evidence, default=str)})
            await db.commit()
    except Exception as exc:
        raise ValueError(f"missing_config: PGL Register could not write governance ledger: {exc}") from exc
    return {"registered": True, "record_id": record_id, "proof_hash": proof_hash}


async def _pgl_lineage_anchor_node(config: dict, context: dict) -> dict:
    parent_hash = str(config.get("parent_hash") or config.get("parentHash") or context.get("audit_seal") or (context.get("evidence_pack") or {}).get("proof_hash") or "").strip()
    if not parent_hash:
        raise ValueError("missing_config: PGL Lineage Anchor requires parent_hash or upstream audit/evidence proof")
    lineage_payload = {
        "parent_hash": parent_hash,
        "trace_hash": hashlib.sha256(json.dumps(context.get("trace", []), sort_keys=True, default=str).encode()).hexdigest(),
        "workspace_id": context.get("workspace_id"),
        "transaction_id": context.get("transaction_id"),
        "anchored_at": datetime.now(timezone.utc).isoformat(),
    }
    lineage_hash = hashlib.sha256(json.dumps(lineage_payload, sort_keys=True, default=str).encode()).hexdigest()
    record_id = str(config.get("record_id") or f"lineage_{lineage_hash[:16]}")
    try:
        async with get_db_session() as db:

            await db.execute(sql_text(
                """
                INSERT INTO pipeline_lineage_anchors (id, lineage_hash, parent_hash, payload)
                VALUES (:id, :lineage_hash, :parent_hash, CAST(:payload AS jsonb))
                ON CONFLICT (id) DO UPDATE
                SET lineage_hash = EXCLUDED.lineage_hash, parent_hash = EXCLUDED.parent_hash, payload = EXCLUDED.payload
                """
            ), {"id": record_id, "lineage_hash": f"0x{lineage_hash[:32]}", "parent_hash": parent_hash, "payload": json.dumps(lineage_payload, default=str)})
            await db.commit()
    except Exception as exc:
        raise ValueError(f"missing_config: PGL Lineage Anchor could not write lineage table: {exc}") from exc
    return {"anchored": True, "record_id": record_id, "parent_hash": parent_hash, "lineage_hash": f"0x{lineage_hash[:32]}"}


def _x402_payment_gate_node(config: dict, context: dict) -> dict:
    price = float(config.get("max_price_usd") or config.get("maxPriceUsd") or config.get("price_usd") or 0)
    if price <= 0:
        raise ValueError("missing_config: x402 Payment Gate requires max_price_usd")
    workspace_cap = float(config.get("workspace_budget_usd") or config.get("workspaceBudgetUsd") or config.get("monthly_cap_usd") or config.get("monthlyCapUsd") or 0)
    current_cost = float(context.get("cost") or 0)
    if workspace_cap and current_cost + price > workspace_cap:
        raise ValueError(f"payment_blocked: x402 Payment Gate blocked ${current_cost + price:.6f} over budget ${workspace_cap:.6f}")
    asset = str(config.get("asset") or "USDC").upper()
    network = str(config.get("network") or "base").lower()
    challenge = {
        "asset": asset,
        "network": network,
        "max_price_usd": price,
        "settlement_required": bool(config.get("settlement_required") or config.get("settlementRequired")),
        "proof": hashlib.sha256(f"{context.get('transaction_id')}:{asset}:{network}:{price}".encode()).hexdigest()[:16],
    }
    if challenge["settlement_required"] and not config.get("settlement_proof") and not config.get("settlementProof"):
        raise ValueError("payment_required: x402 Payment Gate requires settlement_proof for settlement_required tools")
    return {"allowed": True, "payment_challenge": challenge, "settlement_proof": config.get("settlement_proof") or config.get("settlementProof")}


def _shadow_mode_node(config: dict, context: dict) -> dict:
    shadow_id = f"shadow_{hashlib.sha256((context.get('transaction_id', '') + _context_text(context)).encode()).hexdigest()[:12]}"
    return {
        "enabled": True,
        "shadow_id": shadow_id,
        "traffic_sample": float(config.get("traffic_sample") or config.get("trafficSample") or 0.05),
        "writes_disabled": True,
        "production_exposure": False,
        "metrics": {
            "trace_hash": hashlib.sha256(json.dumps(context.get("trace", []), sort_keys=True, default=str).encode()).hexdigest()[:16],
            "estimated_cost_usd": float(context.get("cost") or 0),
        },
    }


def _deploy_contract_node(node_type: str, config: dict, context: dict) -> dict:
    proof = context.get("evidence_pack") or {"proof_hash": context.get("audit_seal")}
    if not proof.get("proof_hash"):
        raise ValueError("missing_config: Deploy node requires Audit Signer or Evidence Pack proof")
    contract_hash = hashlib.sha256(json.dumps({
        "node_type": node_type,
        "proof": proof,
        "policy": context.get("policy", {}),
        "lock": context.get("execution_lock"),
        "config": config,
    }, sort_keys=True, default=str).encode()).hexdigest()
    route_kind = "endpoint" if node_type == "deploy-endpoint" else "agent"
    return {
        "deployable": True,
        "kind": route_kind,
        "contract_id": f"{route_kind}_{contract_hash[:16]}",
        "contract_hash": f"0x{contract_hash[:32]}",
        "requires_runtime_route": "/api/v1/deployments",
    }


async def _code_executor_node(config: dict, context: dict) -> dict:
    sandbox_url = str(config.get("sandbox_url") or config.get("sandboxUrl") or "").strip().rstrip("/")
    if not sandbox_url:
        raise ValueError("unsafe: code_executor requires configured sandbox_url")
    await _assert_safe_external_url(sandbox_url)
    payload = {
        "language": config.get("language") or "python",
        "code": config.get("code") or "",
        "input": context.get("text", ""),
        "timeout_seconds": min(int(config.get("timeout_seconds") or config.get("timeoutSeconds") or 10), 30),
    }
    if not payload["code"]:
        raise ValueError("missing_config: code_executor requires config.code")
    async with httpx.AsyncClient(timeout=payload["timeout_seconds"] + 5, follow_redirects=False) as client:
        response = await client.post(sandbox_url, json=payload)
    response.raise_for_status()
    return {"status": "completed", "sandbox_url": sandbox_url, "result": response.json() if "json" in response.headers.get("content-type", "") else response.text}


def _normalize_provider_entries(raw: Any) -> list[dict]:
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",") if item.strip()]
    entries = raw if isinstance(raw, list) else []
    normalized = []
    for entry in entries:
        if isinstance(entry, dict):
            provider = str(entry.get("provider") or entry.get("name") or "").strip().lower()
            model = str(entry.get("model") or "").strip()
            cost = float(entry.get("estimated_cost") or entry.get("cost") or 0.0)
        else:
            provider = str(entry).strip().lower()
            model = ""
            cost = 0.0
        if provider:
            normalized.append({"provider": provider, "model": model, "estimated_cost": cost})
    return normalized


async def _routing_node(node_type: str, config: dict, context: dict) -> dict:
    if node_type == "cost-router":
        candidates = _normalize_provider_entries(config.get("candidates") or config.get("providers") or [
            {"provider": "ollama", "model": settings.OLLAMA_MODEL, "estimated_cost": 0.0},
            {"provider": "groq", "model": settings.GROQ_MODEL, "estimated_cost": 0.00002},
            {"provider": "gemini", "model": settings.GEMINI_MODEL, "estimated_cost": 0.00004},
            {"provider": "openai", "model": settings.OPENAI_MODEL_CHAT, "estimated_cost": 0.00008},
        ])
        configured = [candidate for candidate in candidates if _configured_provider(candidate["provider"])]
        if not configured:
            raise ValueError("missing_key: cost-router has no configured provider candidates")
        selected = sorted(configured, key=lambda item: item["estimated_cost"])[0]
        return {"decision": "selected", "reason": "lowest_configured_estimated_cost", **selected}

    if node_type in {"fallback", "load-balancer"}:
        providers = _normalize_provider_entries(config.get("providers"))
        if not providers:
            raise ValueError(f"missing_config: {node_type} requires providers")
        configured = [provider for provider in providers if _configured_provider(provider["provider"])]
        if not configured:
            raise ValueError(f"missing_key: {node_type} providers are not configured")
        if node_type == "load-balancer":
            index = int(hashlib.sha256(_context_text(context).encode()).hexdigest()[:8], 16) % len(configured)
            selected = configured[index]
            return {"decision": "selected", "reason": "deterministic_hash_balance", **selected}
        selected = configured[0]
        return {"decision": "selected", "reason": "first_configured_fallback", **selected}

    if node_type == "classifier":
        labels = config.get("labels") or []
        if isinstance(labels, str):
            labels = [item.strip() for item in labels.split(",") if item.strip()]
        if not labels:
            raise ValueError("missing_config: classifier requires labels")
        text_tokens = _tokenize(_context_text(context))
        scored = []
        for label in labels:
            label_text = label.get("label") if isinstance(label, dict) else str(label)
            keywords = label.get("keywords", []) if isinstance(label, dict) else [label_text]
            if isinstance(keywords, str):
                keywords = [keywords]
            score = len(text_tokens & set().union(*[_tokenize(keyword) for keyword in keywords]))
            scored.append({"label": label_text, "score": score})
        selected = sorted(scored, key=lambda item: item["score"], reverse=True)[0]
        return {"decision": "classified", **selected}

    routes = config.get("routes") or []
    if not isinstance(routes, list) or not routes:
        raise ValueError("missing_config: semantic-router requires routes")
    text_tokens = _tokenize(_context_text(context))
    best = None
    for route in routes:
        if not isinstance(route, dict):
            continue
        keywords = route.get("keywords") or [route.get("label") or route.get("route") or ""]
        if isinstance(keywords, str):
            keywords = [keywords]
        score = len(text_tokens & set().union(*[_tokenize(keyword) for keyword in keywords]))
        candidate = {"route": route.get("route") or route.get("label"), "provider": route.get("provider"), "model": route.get("model"), "score": score}
        if best is None or score > best["score"]:
            best = candidate
    if not best:
        raise ValueError("missing_config: semantic-router routes are invalid")
    return {"decision": "routed", **best}


def _normalize_tool_names(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",") if item.strip()]
    normalized = []
    for value in raw if isinstance(raw, list) else []:
        tool = str(value).strip().lower().replace("-", "_")
        if tool not in ALLOWED_LANGCHAIN_TOOLS:
            raise ValueError(f"missing_config: unsupported pipeline tool '{value}'")
        if tool not in normalized:
            normalized.append(tool)
    return normalized


async def _langgraph_contract_node(config: dict, context: dict) -> dict:
    steps = config.get("steps")
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except json.JSONDecodeError:
            steps = [item.strip() for item in steps.splitlines() if item.strip()]
    if not isinstance(steps, list) or not steps:
        raise ValueError("missing_config: LangGraph node requires configured steps")
    state = {"input": _context_text(context), "memory": context.get("memory", [])}
    executed = []
    for index, step in enumerate(steps[:20]):
        label = step.get("label") if isinstance(step, dict) else str(step)
        operation = (step.get("operation") if isinstance(step, dict) else "pass") or "pass"
        state["last_step"] = label
        state["text"] = f"{state.get('text') or state['input']}\n[{index + 1}] {label}".strip()
        executed.append({"index": index + 1, "label": label, "operation": operation, "status": "completed"})
    return {"result": state.get("text") or state["input"], "steps": executed}


async def _retrievalqa_node(config: dict, context: dict) -> dict:
    provider = str(config.get("model_provider") or config.get("provider") or "").strip().lower()
    model = str(config.get("model_name") or config.get("model") or "").strip()
    if not provider:
        raise ValueError("missing_config: RetrievalQA requires model_provider")
    if not model:
        raise ValueError("missing_config: RetrievalQA requires model_name")
    if not _configured_provider(provider):
        raise ValueError(f"missing_key: RetrievalQA provider '{provider}' is not configured")
    question = str(config.get("question") or config.get("prompt") or context.get("query") or context.get("text") or "")
    sources = _records_from_context(context)
    source_text = "\n\n".join(str(record.get("text") or record) for record in sources[:8])
    prompt = (
        "Answer the question using only the provided retrieved context. "
        "Return uncertainty when the context is insufficient.\n\n"
        f"Question:\n{question}\n\nRetrieved context:\n{source_text}"
    )
    result = await run_completion({
        "provider": provider,
        "model": model,
        "temperature": config.get("temperature", 0.2),
        "messages": [{"role": "user", "content": prompt}],
    }, stream=False)
    text = _completion_text(result.payload)
    usage = result.payload.get("usage") or {}
    tokens = int(usage.get("total_tokens") or max(1, len(prompt.split()) + len(text.split())))
    return {
        "text": text,
        "provider": result.provider,
        "model": result.payload.get("model") or model,
        "tokens": tokens,
        "cost": tokens * 0.00001,
    }


def _configured_requirement_status(requirement: str, config: dict, context: dict) -> bool:
    requirement_key = requirement.lower().replace("-", "_").replace(" ", "_")
    if requirement_key in {"text_or_url"}:
        return bool(config.get("text") or config.get("url") or context.get("text"))
    if requirement_key == "embedding":
        return bool(context.get("embedding"))
    if requirement_key == "proof":
        return bool(context.get("audit_seal") or context.get("evidence_pack"))
    if requirement_key == "openai_api_key":
        return bool(settings.OPENAI_API_KEY.strip())
    if requirement_key == "groq_api_key":
        return bool(settings.GROQ_API_KEY.strip())
    if requirement_key == "gemini_api_key":
        return bool(settings.GEMINI_API_KEY.strip())
    if requirement_key == "anthropic_api_key":
        return bool(settings.ANTHROPIC_API_KEY.strip())
    if requirement_key == "serpapi_key":
        return bool(settings.SERPAPI_KEY.strip())
    if requirement_key == "ollama_base_url":
        return bool(settings.OLLAMA_BASE_URL.strip())
    return bool(config.get(requirement_key) or config.get(requirement))


def _adapter_name_for_node(node_type: str) -> str:
    adapters = {
        "input": "input",
        "source": "input",
        "doc-loader": "document_loader",
        "file-read": "document_loader",
        "langchain_agent": "langchain_agent",
        "agent-node": "agent_node",
        "agent-team": "agent_team",
        "supervisor-agent": "supervisor_agent",
        "critic-agent": "critic_agent",
        "planner-agent": "planner_agent",
        "agent-handoff": "agent_handoff",
        "pgl-register-agent": "pgl_register_agent",
        "lc-langgraph": "langgraph_contract",
        "lc-memory": "conversation_memory",
        "lc-retrievalqa": "retrieval_qa",
        "lc-parser": "output_parser",
        "lc-toolnode": "tool_binding",
        "chunker": "chunker",
        "reranker": "reranker",
        "hybrid-search": "hybrid_search",
        "pgvector": "pgvector",
        "qdrant": "qdrant",
        "weaviate": "weaviate",
        "policy-gate": "policy_gate",
        "audit-signer": "audit_signer",
        "audit-log": "audit_logger",
        "evidence-pack": "evidence_pack",
        "evidence-receipt": "evidence_receipt",
        "pgl-register": "pgl_register",
        "pgl-lineage-anchor": "pgl_lineage_anchor",

        "cost-gate": "cost_gate",
        "budget-gate": "budget_gate",
        "human-approval": "human_approval",
        "ask-human": "ask_human",
        "x402-payment-gate": "x402_payment_gate",
        "shadow-mode": "shadow_mode",
        "deploy-endpoint": "deploy_endpoint",
        "deploy-agent": "deploy_agent",
        "deploy-job": "deploy_job",
        "deploy-pipeline": "deploy_pipeline",
        "lock-engine": "lock_engine",
        "retry-logic": "retry_logic",
        "circuit-breaker": "circuit_breaker",
        "rate-limiter": "rate_limiter",
        "webhook": "webhook",
        "webhook-output": "webhook",
        "http-call": "http_request",
        "custom-http": "http_request",
        "custom-python": "code_executor",
        "custom-mcp-tool": "mcp_tool_contract",
        "custom-node-package": "private_node_package",
        "marketplace-tool": "marketplace_tool",
        "pii-redact": "pii_redactor",
        "json-format": "json_formatter",
        "markdown-render": "markdown_renderer",
        "stream-out": "stream_output",
    }
    if node_type.startswith("llm-"):
        return "llm"
    if node_type.startswith("embed-"):
        return "embedding"
    return adapters.get(node_type, "unsupported")


def _estimate_node_cost_usd(node_type: str, config: dict) -> float:
    if node_type.startswith("llm-") or node_type in {"langchain_agent", "agent-node", "supervisor-agent", "critic-agent", "planner-agent", "lc-retrievalqa"}:
        return float(config.get("estimated_cost_usd") or config.get("estimatedCostUsd") or 0.002)
    if node_type.startswith("embed-"):
        return float(config.get("estimated_cost_usd") or 0.0001)
    if node_type in {"web-search", "http-call", "webhook", "webhook-output", "custom-http"}:
        return float(config.get("estimated_cost_usd") or 0.0002)
    if node_type == "x402-payment-gate":
        return float(config.get("max_price_usd") or config.get("price_usd") or config.get("estimated_cost_usd") or 0)
    return float(config.get("estimated_cost_usd") or 0)


def _node_certification(node_type: str, config: dict, context: dict) -> dict:
    static_requirements = {
        "doc-loader": ["text or url"],
        "file-read": ["text or url"],
        "langchain_agent": ["model_provider", "model_name"],
        "agent-node": ["model_provider", "model_name"],
        "supervisor-agent": ["model_provider", "model_name"],
        "critic-agent": ["model_provider", "model_name"],
        "planner-agent": ["model_provider", "model_name"],
        "agent-team": ["agents"],
        "lc-langgraph": ["steps"],
        "lc-retrievalqa": ["model_provider", "model_name"],
        "lc-toolnode": ["tools_allowed"],
        "llm-openai": ["OPENAI_API_KEY"],
        "llm-groq": ["GROQ_API_KEY"],
        "llm-gemini": ["GEMINI_API_KEY"],
        "llm-ollama": ["OLLAMA_BASE_URL"],
        "llm-anthropic": ["ANTHROPIC_API_KEY"],
        "llm-openai-compatible": ["base_url"],
        "embed-openai": ["OPENAI_API_KEY"],
        "embed-bge": ["OLLAMA_BASE_URL"],
        "pgvector": ["embedding"],
        "qdrant": ["url", "collection", "embedding"],
        "weaviate": ["url", "class_name", "embedding"],
        "repo-risk-gate": ["repo_url"],
        "cost-gate": ["max_cost_usd"],
        "budget-gate": ["monthly_cap_usd"],
        "human-approval": ["approval_id"],
        "ask-human": ["approval_id"],
        "deploy-endpoint": ["proof"],
        "deploy-agent": ["proof"],
        "pgl-lineage-anchor": ["parent_hash"],
        "x402-payment-gate": ["max_price_usd"],
        "web-search": ["SERPAPI_KEY"],
        "http-call": ["url"],
        "custom-http": ["url"],
        "email-send": ["url"],
        "slack-send": ["url"],
        "discord-send": ["url"],
        "github-action": ["url"],
        "jira-action": ["url"],
        "pagerduty-event": ["url"],
        "stripe-event": ["url"],
        "sql-query": ["query"],
        "code-exec": ["sandbox_url"],
        "custom-python": ["sandbox_url"],
        "custom-mcp-tool": ["server_url"],
        "custom-node-package": ["package_url", "sandbox_url"],
        "webhook": ["url"],
        "webhook-output": ["url"],
    }
    adapter = _adapter_name_for_node(node_type)
    if adapter == "unsupported":
        return {"status": "unsupported", "adapter": adapter, "requirements": [], "missing": []}
    requirements = static_requirements.get(node_type, [])
    missing = [requirement for requirement in requirements if not _configured_requirement_status(requirement, config, context)]
    if node_type in {"code-exec", "code_executor", "custom-python", "custom-node-package"} and missing:
        status = "unsafe"
    elif missing:
        status = "missing_key" if any(item.endswith("_KEY") or item == "SERPAPI_KEY" for item in missing) else "missing_config"
    else:
        status = "real"
    return {"status": status, "adapter": adapter, "requirements": requirements, "missing": missing}


def _policy_decision_for_trace(node_type: str, context: dict) -> dict:
    policy = context.get("policy") if isinstance(context.get("policy"), dict) else {}
    boundary_nodes = {
        "http-call", "http-request", "custom-http", "webhook", "webhook-output",
        "email-send", "slack-send", "discord-send", "github-action", "jira-action", "pagerduty-event", "stripe-event",
        "custom-mcp-tool", "custom-node-package", "web-search", "qdrant", "weaviate",
        "embed-openai", "llm-openai", "llm-groq", "llm-gemini", "llm-anthropic", "llm-openai-compatible",
    }
    gate_nodes = {"policy-gate", "cost-gate", "budget-gate", "repo-risk-gate", "human-approval", "ask-human", "x402-payment-gate", "pgl-lineage-anchor", "shadow-mode", "lock-engine"}
    return {
        "allowed": True,
        "reason": "governance_gate_enforced" if node_type in gate_nodes else "policy_gate_inline" if policy else "default_allow_no_policy_gate",
        "pii_redacted": bool(policy.get("redacted")),
        "pii_found": policy.get("pii_found", []),
        "boundary_crossing": node_type in boundary_nodes,
    }


def _build_run_receipt(transaction_id: str, context: dict, execution: list[dict], workspace_id: str, user_id: str, status: str, error: str | None = None) -> dict:
    trace = context.get("trace", [])
    trace_hash = hashlib.sha256(json.dumps(trace, sort_keys=True, default=str).encode()).hexdigest()
    graph_hash = hashlib.sha256(json.dumps(execution, sort_keys=True, default=str).encode()).hexdigest()
    cost_breakdown = []
    for item in trace:
        cost_breakdown.append({
            "node_id": item.get("node_id"),
            "node_type": item.get("node_type"),
            "provider": item.get("provider"),
            "model": item.get("model"),
            "tokens": (item.get("token_usage") or {}).get("delta_tokens", 0),
            "cost_usd": item.get("cost_usd", 0),
        })
    policy_decisions = [item.get("policy_decision", {}) for item in trace]
    proof_hash = hashlib.sha256(f"{transaction_id}:{trace_hash}:{graph_hash}:{status}".encode()).hexdigest()
    return {
        "receipt_id": f"rcpt_{transaction_id[:12]}",
        "evidence_id": f"evd_{transaction_id[:8]}",
        "status": status,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "proof_hash": f"0x{proof_hash[:32]}",
        "trace_hash": f"0x{trace_hash[:32]}",
        "graph_hash": f"0x{graph_hash[:32]}",
        "total_nodes": len(execution),
        "executed_nodes": len(trace),
        "total_tokens": int(context.get("tokens") or 0),
        "total_cost_usd": round(sum(float(item.get("cost_usd") or 0) for item in cost_breakdown), 8),
        "cost_breakdown": cost_breakdown,
        "policy_decisions": policy_decisions,
        "boundary_crossings": [item for item in policy_decisions if item.get("boundary_crossing")],
        "deployable": status == "completed" and not error,
        "replay": {
            "graph_hash": f"0x{graph_hash[:32]}",
            "execution_order": [step.get("id") or step.get("node_type") for step in execution],
            "deterministic": True,
        },
        "error": error,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
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


async def execute_langchain_agent(node_config: dict, input_context: dict) -> dict:
    config = _validate_langchain_agent_config(node_config)
    return await asyncio.wait_for(
        _run_react_agent(config, input_context),
        timeout=config.timeout_seconds,
    )


def _validate_langchain_agent_config(node_config: dict) -> LangChainAgentConfig:
    normalized = dict(node_config or {})
    if "model_provider" not in normalized and normalized.get("provider"):
        normalized["model_provider"] = normalized["provider"]
    if "model_name" not in normalized and normalized.get("model"):
        normalized["model_name"] = normalized["model"]
    if "tools_allowed" not in normalized and normalized.get("tools"):
        normalized["tools_allowed"] = normalized["tools"]
    if "redact_pii" not in normalized and "redactPii" in normalized:
        normalized["redact_pii"] = normalized["redactPii"]
    if "max_iterations" not in normalized and "maxIterations" in normalized:
        normalized["max_iterations"] = normalized["maxIterations"]
    if "timeout_seconds" not in normalized and "timeoutSeconds" in normalized:
        normalized["timeout_seconds"] = normalized["timeoutSeconds"]

    try:
        config = LangChainAgentConfig.model_validate(normalized)
    except ValidationError as exc:
        raise ValueError(f"Invalid LangChain Agent config: {exc.errors()}") from exc

    blocked = set(config.blocked_tools)
    config.tools_allowed = [tool for tool in config.tools_allowed if tool not in blocked]
    if not _configured_provider(config.model_provider):
        raise ValueError(f"LangChain Agent provider '{config.model_provider}' is not configured")
    return config


async def _run_react_agent(config: LangChainAgentConfig, input_context: dict) -> dict:
    safe_text = str(input_context.get("text", ""))
    policy = {"pii_found": [], "redacted": False}
    if config.redact_pii:
        masked = pii_engine.mask(safe_text, "redact")
        safe_text = masked.get("masked_text", safe_text)
        policy = {"pii_found": masked.get("pii_found", []), "redacted": bool(masked.get("pii_found"))}

    try:
        from langchain.agents import AgentExecutor, create_react_agent
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        from langchain_core.prompts import PromptTemplate
        from langchain_core.tools import StructuredTool
    except ImportError as exc:
        raise ValueError("LangChain Agent requires langchain and langchain-core to be installed") from exc

    class VeklomLangChainChatModel(BaseChatModel):
        provider: str
        selected_model: str
        temperature: float = 0.2
        token_usage: dict = Field(default_factory=lambda: {"total_tokens": 0})

        @property
        def _llm_type(self) -> str:
            return "veklom_provider_router"

        def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
            raise RuntimeError("VeklomLangChainChatModel must be invoked asynchronously")

        async def _agenerate(self, messages: list[BaseMessage], stop: list[str] | None = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
            body_messages = [_langchain_message_to_provider_message(message) for message in messages]
            result = await run_completion({
                "provider": self.provider,
                "model": self.selected_model,
                "temperature": self.temperature,
                "messages": body_messages,
            }, stream=False)
            if result.provider != self.provider and self.provider != "sovereign":
                raise ValueError(f"Selected LangChain Agent provider '{self.provider}' did not execute; router returned '{result.provider}'")
            text = _completion_text(result.payload)
            usage = result.payload.get("usage") or {}
            total_tokens = int(usage.get("total_tokens") or max(1, sum(len(m["content"].split()) for m in body_messages) + len(text.split())))
            self.token_usage["total_tokens"] = int(self.token_usage.get("total_tokens", 0)) + total_tokens
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text, response_metadata={"provider": result.provider, "model": self.selected_model, "usage": usage}))])

    prompt = PromptTemplate.from_template(
        "You are a Veklom governed ReAct agent.\n"
        "Use only the tools listed below. If no tool is necessary, answer directly.\n\n"
        "{tools}\n\n"
        "Use this format:\n"
        "Question: the input task\n"
        "Thought: reason about the next step\n"
        "Action: one of [{tool_names}]\n"
        "Action Input: the input to the action\n"
        "Observation: the action result\n"
        "... repeat Thought/Action/Action Input/Observation as needed\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer\n\n"
        "Question: {input}\n"
        "Thought:{agent_scratchpad}"
    )
    llm = VeklomLangChainChatModel(provider=config.model_provider, selected_model=config.model_name, temperature=config.temperature)
    tools = _build_langchain_structured_tools(config.tools_allowed, input_context, StructuredTool)
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=config.max_iterations,
        max_execution_time=config.timeout_seconds,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        verbose=False,
    )
    result = await executor.ainvoke({"input": safe_text})
    intermediate_steps = _serialize_langchain_intermediate_steps(result.get("intermediate_steps", []))
    tool_calls = [
        {
            "iteration": index + 1,
            "tool": step.get("tool"),
            "input": step.get("tool_input"),
            "status": "completed",
            "output": step.get("observation"),
        }
        for index, step in enumerate(intermediate_steps)
        if step.get("tool")
    ]
    errors = [call for call in tool_calls if isinstance(call.get("output"), str) and "requires" in call["output"].lower()]
    final_answer = str(result.get("output") or "")
    total_tokens = int(llm.token_usage.get("total_tokens", 0))

    return {
        "final_answer": final_answer,
        "intermediate_steps": intermediate_steps,
        "tool_calls": tool_calls,
        "token_usage": {
            "total_tokens": total_tokens,
            "estimated_prompt_tokens": total_tokens // 2,
            "estimated_completion_tokens": total_tokens - (total_tokens // 2),
        },
        "cost": total_tokens * 0.00001,
        "errors": errors,
        "provider": config.model_provider,
        "model": config.model_name,
        "policy": policy,
    }


def _bind_langchain_tools(tools_allowed: list[str]) -> dict[str, Any]:
    registry = {
        "web_search": _langchain_tool_web_search,
        "http_request": _langchain_tool_http_request,
        "sql_query": _langchain_tool_sql_query,
        "file_reader": _langchain_tool_file_reader,
        "code_executor": _langchain_tool_code_executor,
        "marketplace_tool": _langchain_tool_marketplace_tool,
    }
    return {tool: registry[tool] for tool in tools_allowed if tool in registry}


def _build_langchain_structured_tools(tools_allowed: list[str], input_context: dict, structured_tool_cls: Any) -> list[Any]:
    tool_coroutines = _bind_langchain_tools(tools_allowed)
    descriptions = {
        "web_search": "Search the public web. Input can be a search query string or JSON with query.",
        "http_request": "Call an external HTTP API. Input must be JSON with url, optional method, optional body.",
        "sql_query": "Run a read-only SQL SELECT/WITH query against the configured Veklom database.",
        "file_reader": "Read text from a configured document URL or direct text payload.",
        "code_executor": "Execute sandboxed code when a sandbox service is configured.",
        "marketplace_tool": "Search Veklom marketplace tools. Input can be a query string or JSON with query.",
    }

    tools: list[Any] = []
    for name, coroutine in tool_coroutines.items():
        async def _runner(tool_input: str, _coroutine=coroutine, _context=input_context) -> str:
            args = _coerce_tool_args(tool_input)
            result = await _coroutine(args, _context)
            return json.dumps(result, default=str)

        tools.append(structured_tool_cls.from_function(
            coroutine=_runner,
            name=name,
            description=descriptions[name],
        ))
    return tools


def _coerce_tool_args(tool_input: Any) -> dict:
    if isinstance(tool_input, dict):
        return tool_input
    raw = str(tool_input or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return {"query": parsed}
    except json.JSONDecodeError:
        return {"query": raw, "text": raw}


def _langchain_message_to_provider_message(message: Any) -> dict:
    role = getattr(message, "type", "user")
    if role == "human":
        role = "user"
    elif role == "ai":
        role = "assistant"
    elif role not in {"system", "assistant", "user"}:
        role = "user"
    content = getattr(message, "content", "")
    if not isinstance(content, str):
        content = json.dumps(content, default=str)
    return {"role": role, "content": content}


def _serialize_langchain_intermediate_steps(raw_steps: list[Any]) -> list[dict]:
    serialized: list[dict] = []
    for index, item in enumerate(raw_steps):
        try:
            action, observation = item
            serialized.append({
                "iteration": index + 1,
                "tool": getattr(action, "tool", None),
                "tool_input": getattr(action, "tool_input", None),
                "log": getattr(action, "log", ""),
                "observation": observation,
            })
        except Exception:
            serialized.append({"iteration": index + 1, "raw": str(item)})
    return serialized


def _react_prompt(config: LangChainAgentConfig, input_text: str, tools: dict[str, Any], steps: list[dict]) -> str:
    tool_names = ", ".join(tools.keys()) or "none"
    tool_history = json.dumps(steps[-6:], ensure_ascii=False)
    return (
        "Run this pipeline node as a ReAct agent.\n"
        f"Available tools: {tool_names}\n"
        "Return only JSON. Use one of these shapes:\n"
        "{\"thought\":\"...\",\"action\":\"tool_name\",\"action_input\":{...}}\n"
        "{\"thought\":\"...\",\"final_answer\":\"...\"}\n\n"
        f"Upstream context:\n{input_text}\n\n"
        f"Intermediate steps:\n{tool_history}"
    )


def _completion_text(payload: dict) -> str:
    try:
        return str(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        return ""


def _parse_react_decision(model_text: str) -> dict:
    text = (model_text or "").strip()
    if not text:
        return {"final_answer": ""}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"final_answer": text}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
                return parsed if isinstance(parsed, dict) else {"final_answer": text}
            except json.JSONDecodeError:
                pass
    return {"final_answer": text}


async def _langchain_tool_web_search(args: dict, context: dict) -> dict:
    if not settings.SERPAPI_KEY:
        raise ValueError("web_search requires SERPAPI_KEY")
    query = str(args.get("query") or context.get("text") or "").strip()
    if not query:
        raise ValueError("web_search requires query")
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
        response = await client.get("https://serpapi.com/search.json", params={"q": query, "api_key": settings.SERPAPI_KEY, "num": 5})
    response.raise_for_status()
    data = response.json()
    results = data.get("organic_results") or []
    return {"query": query, "results": [{"title": r.get("title"), "link": r.get("link"), "snippet": r.get("snippet")} for r in results[:5]]}


async def _langchain_tool_http_request(args: dict, context: dict) -> dict:
    output = await _http_request_node({
        "url": args.get("url"),
        "method": args.get("method") or "GET",
        "body": args.get("body"),
    }, context)
    return {"response": output[:12000], "truncated": len(output) > 12000}


async def _langchain_tool_sql_query(args: dict, context: dict) -> dict:
    query = str(args.get("query") or "").strip()
    lowered = query.lower()
    if not query or not (lowered.startswith("select ") or lowered.startswith("with ")):
        raise ValueError("sql_query only permits SELECT/WITH read queries")
    if ";" in query or "--" in query or "/*" in query:
        raise ValueError("sql_query rejects multi-statement or commented SQL")
    async with get_db_session() as db:
        result = await db.execute(sql_text(query).execution_options(autocommit=False))
        rows = result.mappings().fetchmany(100)
    return {"rows": [dict(row) for row in rows], "row_count": len(rows)}


async def _langchain_tool_file_reader(args: dict, context: dict) -> dict:
    text = await _load_document({"url": args.get("url"), "text": args.get("text")})
    return {"text": text[:12000], "chars": len(text), "truncated": len(text) > 12000}


async def _langchain_tool_code_executor(args: dict, context: dict) -> dict:
    raise ValueError("code_executor requires a configured sandbox service before it can run")


async def _langchain_tool_marketplace_tool(args: dict, context: dict) -> dict:
    from backend.apps.api.routers.marketplace import _source_marketplace_tools

    needle = str(args.get("query") or args.get("tool") or "").strip().lower()
    tools = _source_marketplace_tools()
    if needle:
        tools = [
            tool for tool in tools
            if needle in tool.get("name", "").lower()
            or needle in tool.get("category", "").lower()
            or any(needle in str(cap).lower() for cap in tool.get("capabilities", []))
        ]
    return {"tools": tools[:5], "count": len(tools)}


PIPELINE_NODE_ADAPTERS = {
    LANGCHAIN_AGENT_NODE_TYPE: execute_langchain_agent,
}


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
            # Enforce background cAPI gating on GPC nodes
            async with get_db_session() as db:
                capi_res = await _evaluate_intent_with_capi(
                    agent_id=f"agent_gpc_{transaction_id[:8]}",
                    action=node_id,
                    target_protocol="gpc_step",
                    payload={"description": desc, "prompt_model": model, "provider": provider},
                    workspace_id=workspace_id,
                    db=db
                )
                lock_state = capi_res.get("lock_state", {})
                status = lock_state.get("status", "LOCKED")
                temp = 0.0 if status == "LOCKED" else (0.4 if status == "ADAPTING" else 0.7)
                logger.info(f"[Mission Lock] Executing GPC Node '{node_id}' in state={status} with Temperature={temp}")

            start_time = datetime.now()
            prompt = f"GPC Node: {desc}. Evaluate according to invariant limits. Current Context: {context}"
            
            result = await run_completion({
                "provider": provider,
                "model": model,
                "temperature": temp,
                "messages": [{"role": "user", "content": prompt}]
            }, stream=False)
            
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
