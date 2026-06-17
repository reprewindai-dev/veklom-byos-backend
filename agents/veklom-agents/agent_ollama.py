"""
Veklom Sovereign Agent — Ollama Core Engine (PRIMARY)
======================================================
This is the MAIN agent for veklom-byos-backend.

Ollama runs 100% on your Hetzner server.
Zero data leaves your sovereign infrastructure.
Zero inference cost. Zero cloud dependency.

Architecture:
    THINK  →  Ollama LLM reasons over goal + memory
    ACT    →  Calls real Veklom BYOS backend endpoints
    OBSERVE→  Result injected back into context
    ITERATE→  Loop until goal achieved or max_iterations
    DONE   →  Final structured output + audit log entry

Supported models (sovereign, run locally):
    llama3          ← best general reasoning (default)
    mistral         ← fast, strong instruction following
    phi3            ← ultra-lightweight for edge nodes
    gemma2          ← Google open weights, strong tool use
    codellama       ← code generation tasks
    llama3.1:70b    ← maximum reasoning (needs 40GB RAM)
    deepseek-r1     ← chain-of-thought reasoning

Env vars:
    OLLAMA_BASE_URL     default: http://localhost:11434
    OLLAMA_MODEL        default: llama3
    OLLAMA_TIMEOUT      default: 120 seconds
    VEKLOM_API_URL      e.g.    https://veklom.com/api/v1
    VEKLOM_API_KEY      JWT from /auth/login
    AGENT_MAX_ITER      default: 10
    AGENT_DEBUG         set to 1 for verbose output

Install Ollama on Hetzner:
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull llama3
    ollama serve  # already running after install
"""

import os
import json
import asyncio
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Any
import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3")
OLLAMA_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT", "120"))
VEKLOM_API_URL  = os.getenv("VEKLOM_API_URL",  "https://veklom.com/api/v1")
VEKLOM_API_KEY  = os.getenv("VEKLOM_API_KEY",  "")
MAX_ITER        = int(os.getenv("AGENT_MAX_ITER", "10"))
DEBUG           = os.getenv("AGENT_DEBUG", "0") == "1"


def log(tag: str, msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}][{tag}] {msg}")


# ---------------------------------------------------------------------------
# BYOS Backend Tool Suite
# All tools call real veklom-byos-backend endpoints
# ---------------------------------------------------------------------------

async def _get(path: str) -> dict:
    """Authenticated GET against BYOS backend."""
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.get(
            f"{VEKLOM_API_URL}{path}",
            headers={"Authorization": f"Bearer {VEKLOM_API_KEY}"},
        )
        try:
            return {"status": r.status_code, "data": r.json()}
        except Exception:
            return {"status": r.status_code, "data": r.text}


async def _post(path: str, body: dict) -> dict:
    """Authenticated POST against BYOS backend."""
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{VEKLOM_API_URL}{path}",
            headers={"Authorization": f"Bearer {VEKLOM_API_KEY}"},
            json=body,
        )
        try:
            return {"status": r.status_code, "data": r.json()}
        except Exception:
            return {"status": r.status_code, "data": r.text}


# --- Health & System ---
async def tool_health() -> dict:
    """Check BYOS backend health. No args."""
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(f"{VEKLOM_API_URL}/health")
        try:
            return {"status": r.status_code, "data": r.json()}
        except Exception:
            return {"status": r.status_code, "data": r.text}


# --- Marketplace ---
async def tool_list_vendors() -> dict:
    """List all registered vendors in the Veklom marketplace."""
    return await _get("/marketplace/vendors")


async def tool_list_models() -> dict:
    """List all AI models available in the Veklom marketplace."""
    return await _get("/marketplace/models")


async def tool_get_vendor(vendor_id: str) -> dict:
    """Get details for a specific vendor by ID."""
    return await _get(f"/marketplace/vendors/{vendor_id}")


# --- Workflows / UACP ---
async def tool_run_workflow(
    tenant_id: str,
    payload_intent: str,
    model: str = "llama3",
    origin_x: int = 0,
    origin_y: int = 0,
) -> dict:
    """
    Execute a governed AI workflow via UACP.
    Bills the tenant's Operating Reserve automatically.
    """
    txn_id = f"ollama-{secrets.token_hex(8)}"
    return await _post("/workflows/execute", {
        "transaction_id": txn_id,
        "tenant_id": tenant_id,
        "payload_intent": payload_intent,
        "model": model,
        "origin_x": origin_x,
        "origin_y": origin_y,
    })


async def tool_get_workflow_status(transaction_id: str) -> dict:
    """Check status of a previously submitted workflow by transaction ID."""
    return await _get(f"/workflows/{transaction_id}/status")


# --- Tenants ---
async def tool_list_tenants() -> dict:
    """List all tenants on the platform."""
    return await _get("/tenants")


async def tool_get_tenant(tenant_id: str) -> dict:
    """Get details and operating reserve balance for a specific tenant."""
    return await _get(f"/tenants/{tenant_id}")


async def tool_get_tenant_balance(tenant_id: str) -> dict:
    """Get the current Operating Reserve balance for a tenant."""
    return await _get(f"/tenants/{tenant_id}/balance")


# --- Billing & Revenue ---
async def tool_get_revenue_summary() -> dict:
    """Get platform-wide revenue summary: daily, weekly, monthly totals."""
    return await _get("/billing/revenue/summary")


async def tool_get_audit_log(limit: int = 20) -> dict:
    """Get the most recent immutable audit log entries."""
    return await _get(f"/audit/log?limit={limit}")


# --- IronGrid Routing ---
async def tool_get_node_status() -> dict:
    """Get IronGrid sovereign node health and routing status."""
    return await _get("/irongrid/nodes")


async def tool_route_to_node(origin_x: int, origin_y: int, payload: str) -> dict:
    """Route a payload to the optimal IronGrid node using coordinate physics."""
    return await _post("/irongrid/route", {
        "origin_x": origin_x,
        "origin_y": origin_y,
        "payload": payload,
    })


# --- Ollama local model management ---
async def tool_ollama_list_models() -> dict:
    """List all models currently pulled and available in local Ollama."""
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(f"{OLLAMA_BASE_URL}/api/tags")
        return {"status": r.status_code, "models": r.json()}


async def tool_ollama_pull_model(model_name: str) -> dict:
    """Pull a new model into local Ollama (e.g. 'mistral', 'phi3')."""
    async with httpx.AsyncClient(timeout=300) as http:
        r = await http.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model_name, "stream": False},
        )
        return {"status": r.status_code, "result": r.text[:500]}


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
TOOL_MAP: dict[str, Any] = {
    "health":                tool_health,
    "list_vendors":          tool_list_vendors,
    "list_models":           tool_list_models,
    "get_vendor":            tool_get_vendor,
    "run_workflow":          tool_run_workflow,
    "get_workflow_status":   tool_get_workflow_status,
    "list_tenants":          tool_list_tenants,
    "get_tenant":            tool_get_tenant,
    "get_tenant_balance":    tool_get_tenant_balance,
    "get_revenue_summary":   tool_get_revenue_summary,
    "get_audit_log":         tool_get_audit_log,
    "get_node_status":       tool_get_node_status,
    "route_to_node":         tool_route_to_node,
    "ollama_list_models":    tool_ollama_list_models,
    "ollama_pull_model":     tool_ollama_pull_model,
}

TOOL_SCHEMA_TEXT = """
You have access to these tools. To call a tool output ONLY a JSON object.
Never add explanation before or after the JSON while calling a tool.

TOOLS:
  health                   {}                                   Check BYOS backend health
  list_vendors             {}                                   List marketplace vendors
  list_models              {}                                   List marketplace AI models
  get_vendor               {"vendor_id": "<id>"}               Get vendor detail
  run_workflow             {"tenant_id": "<id>",               Execute governed AI workflow
                            "payload_intent": "<task>",
                            "model": "<ollama_model>"}          (model optional, default llama3)
  get_workflow_status      {"transaction_id": "<id>"}          Check workflow status
  list_tenants             {}                                   List all tenants
  get_tenant               {"tenant_id": "<id>"}               Get tenant detail
  get_tenant_balance       {"tenant_id": "<id>"}               Get Operating Reserve balance
  get_revenue_summary      {}                                   Platform revenue totals
  get_audit_log            {"limit": 20}                       Last N audit entries
  get_node_status          {}                                   IronGrid node health
  route_to_node            {"origin_x": 0,                     Route payload to optimal node
                            "origin_y": 0,
                            "payload": "<text>"}
  ollama_list_models       {}                                   Models in local Ollama
  ollama_pull_model        {"model_name": "<name>"}            Pull new model into Ollama

CALL FORMAT:
  {"tool": "<name>", "args": {<args>}}

When the goal is fully achieved, output ONLY:
  {"done": true, "answer": "<final answer>"}

IMPORTANT: Output ONLY valid JSON when calling tools or finishing. No extra text.
"""


# ---------------------------------------------------------------------------
# SHA-256 audit fingerprint for every agent session
# ---------------------------------------------------------------------------
def audit_hash(goal: str, result: str, iterations: int) -> str:
    raw = f"{goal}|{result}|{iterations}|{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Ollama inference
# ---------------------------------------------------------------------------
async def ollama_chat(messages: list[dict]) -> str:
    """Call Ollama /api/chat and return assistant content string."""
    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as http:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.05,  # near-deterministic for tool calls
                "num_predict": 1024,
            },
        }
        r = await http.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()["message"]["content"]


# ---------------------------------------------------------------------------
# Core agent loop
# ---------------------------------------------------------------------------
async def run_agent(goal: str, session_id: str | None = None) -> dict:
    """
    Run the Ollama sovereign agent loop.

    Args:
        goal:       Natural-language objective.
        session_id: Optional session ID for logging.

    Returns:
        dict with keys: answer, iterations, audit_hash, session_id
    """
    sid = session_id or f"sess-{secrets.token_hex(6)}"
    log("AGENT", f"Session: {sid}")
    log("AGENT", f"Model:   {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
    log("AGENT", f"Goal:    {goal}")

    system_prompt = (
        f"You are the Veklom Sovereign Agent running entirely on a private Hetzner server.\n"
        f"Your inference engine is Ollama ({OLLAMA_MODEL}). No data leaves this server.\n"
        f"You help operate the Veklom BYOS backend: marketplace, tenants, billing, IronGrid routing.\n"
        f"Reason step by step. Use tools to gather information and take action.\n\n"
        + TOOL_SCHEMA_TEXT
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": goal},
    ]

    final_answer = ""
    iterations_used = 0

    for iteration in range(1, MAX_ITER + 1):
        iterations_used = iteration
        log("THINK", f"Iteration {iteration}/{MAX_ITER}")

        raw = await ollama_chat(messages)
        if DEBUG:
            log("LLM", raw[:500])

        messages.append({"role": "assistant", "content": raw})

        # Strip markdown fences if model wraps output
        clean = raw.strip()
        for fence in ["```json", "```JSON", "```"]:
            clean = clean.strip(fence).strip()

        # Try to parse JSON
        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            # Model gave prose — treat as final answer
            log("DONE", "Prose response — treating as final answer")
            final_answer = raw
            break

        # Done signal
        if parsed.get("done"):
            final_answer = parsed.get("answer", raw)
            log("DONE", f"Goal achieved in {iteration} iteration(s)")
            break

        # Tool call
        tool_name = parsed.get("tool")
        tool_args = parsed.get("args", {})

        if not tool_name:
            log("WARN", f"No tool name in JSON: {parsed}")
            final_answer = str(parsed)
            break

        log("ACT", f"{tool_name}({json.dumps(tool_args)[:120]})")

        if tool_name not in TOOL_MAP:
            observation = {"error": f"Unknown tool '{tool_name}'. Valid tools: {list(TOOL_MAP.keys())}"}
        else:
            try:
                observation = await TOOL_MAP[tool_name](**tool_args)
            except TypeError as exc:
                observation = {"error": f"Bad args for {tool_name}: {exc}"}
            except Exception as exc:
                observation = {"error": str(exc)}

        obs_str = json.dumps(observation)
        log("OBSERVE", obs_str[:300])
        messages.append({"role": "user", "content": f"Tool '{tool_name}' result: {obs_str}"})

    else:
        final_answer = f"[Agent hit max iterations ({MAX_ITER}) without completing goal]"
        log("WARN", final_answer)

    h = audit_hash(goal, final_answer, iterations_used)
    log("AUDIT", f"SHA-256: {h}")

    return {
        "session_id":  sid,
        "goal":        goal,
        "answer":      final_answer,
        "iterations":  iterations_used,
        "model":       OLLAMA_MODEL,
        "audit_hash":  h,
        "sovereign":   True,
        "provider":    "ollama",
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Check backend health, list all marketplace vendors and models, "
        "get the platform revenue summary, and report the IronGrid node status."
    )

    result = asyncio.run(run_agent(goal))

    print("\n" + "=" * 60)
    print("VEKLOM SOVEREIGN AGENT — SESSION COMPLETE")
    print("=" * 60)
    print(f"Session  : {result['session_id']}")
    print(f"Model    : {result['model']}")
    print(f"Iter     : {result['iterations']}")
    print(f"Sovereign: {result['sovereign']}")
    print(f"Audit    : {result['audit_hash']}")
    print(f"\nAnswer:\n{result['answer']}")
