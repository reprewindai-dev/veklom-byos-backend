"""
Veklom Agent — Ollama Provider (100% Local / Sovereign)
========================================================
Runs the Level-3 agent loop using a locally-hosted Ollama model.
Zero tokens leave your Hetzner server. Total cost: $0/call.

Prerequisites on Hetzner:
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull llama3          # or mistral, phi3, gemma2, etc.

Env vars:
    OLLAMA_BASE_URL   default: http://localhost:11434
    OLLAMA_MODEL      default: llama3
    VEKLOM_API_URL    e.g.    https://veklom.com/api/v1
    VEKLOM_API_KEY    JWT from /auth/login
"""

import os
import json
import asyncio
import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3")
VEKLOM_API_URL  = os.getenv("VEKLOM_API_URL",  "https://veklom.com/api/v1")
VEKLOM_API_KEY  = os.getenv("VEKLOM_API_KEY",  "")
MAX_ITERATIONS  = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))

# ---------------------------------------------------------------------------
# Tool implementations (same as agent_loop.py — reusable across providers)
# ---------------------------------------------------------------------------
async def tool_check_backend_health() -> dict:
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(f"{VEKLOM_API_URL}/health")
        return {"status": r.status_code, "body": r.text}

async def tool_run_governed_workflow(transaction_id: str, tenant_id: str, payload_intent: str, origin_x: int = 0, origin_y: int = 0) -> dict:
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{VEKLOM_API_URL}/workflows/execute",
            headers={"Authorization": f"Bearer {VEKLOM_API_KEY}"},
            json={"transaction_id": transaction_id, "tenant_id": tenant_id, "payload_intent": payload_intent, "origin_x": origin_x, "origin_y": origin_y},
        )
        return {"status": r.status_code, "body": r.text}

async def tool_list_vendors() -> dict:
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(f"{VEKLOM_API_URL}/marketplace/vendors", headers={"Authorization": f"Bearer {VEKLOM_API_KEY}"})
        return {"status": r.status_code, "vendors": r.text}

TOOL_MAP = {
    "check_backend_health":   tool_check_backend_health,
    "run_governed_workflow":  tool_run_governed_workflow,
    "list_vendors":           tool_list_vendors,
}

TOOL_DESCRIPTIONS = """
Available tools (call by outputting valid JSON exactly like the examples):

1. check_backend_health
   - No args required.
   - Call: {"tool": "check_backend_health", "args": {}}

2. run_governed_workflow
   - Args: transaction_id (str), tenant_id (str), payload_intent (str), origin_x (int, optional), origin_y (int, optional)
   - Call: {"tool": "run_governed_workflow", "args": {"transaction_id": "txn-001", "tenant_id": "demo", "payload_intent": "Analyse Q2 sales"}}

3. list_vendors
   - No args required.
   - Call: {"tool": "list_vendors", "args": {}}

When you are DONE and have a final answer, output:
{"done": true, "answer": "<your final answer here>"}
"""


async def ollama_chat(messages: list[dict]) -> str:
    """Call Ollama /api/chat and return the assistant message content."""
    async with httpx.AsyncClient(timeout=120) as http:
        r = await http.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


async def run_agent(goal: str) -> str:
    print(f"\n[OLLAMA AGENT] Goal: {goal}")
    print(f"[OLLAMA AGENT] Model: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")

    system_prompt = (
        "You are the Veklom Autonomous Agent running on a sovereign Hetzner server. "
        "You have tools you can call to interact with the Veklom backend. "
        "Reason step by step. When you need to call a tool, output ONLY valid JSON "
        "matching the tool call format. When the goal is fully achieved, output the done JSON.\n\n"
        + TOOL_DESCRIPTIONS
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": goal},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n[OLLAMA AGENT] — Iteration {iteration} — THINKING...")
        raw = await ollama_chat(messages)
        print(f"[OLLAMA AGENT] LLM output: {raw[:300]}")
        messages.append({"role": "assistant", "content": raw})

        # Try to parse JSON from response
        try:
            # Strip markdown code fences if present
            clean = raw.strip().strip("```json").strip("```").strip()
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            # LLM gave prose — treat as final answer
            print(f"[OLLAMA AGENT] Non-JSON response — treating as final answer.")
            return raw

        if parsed.get("done"):
            answer = parsed.get("answer", raw)
            print(f"\n[OLLAMA AGENT] DONE.\n{answer}")
            return answer

        tool_name = parsed.get("tool")
        tool_args = parsed.get("args", {})

        if tool_name not in TOOL_MAP:
            observation = {"error": f"Unknown tool: {tool_name}"}
        else:
            print(f"[OLLAMA AGENT] ACT → {tool_name}({tool_args})")
            try:
                observation = await TOOL_MAP[tool_name](**tool_args)
            except Exception as exc:
                observation = {"error": str(exc)}

        print(f"[OLLAMA AGENT] OBSERVE ← {json.dumps(observation)[:200]}")
        messages.append({"role": "user", "content": f"Tool result: {json.dumps(observation)}"})

    return "[OLLAMA AGENT] Max iterations reached."


if __name__ == "__main__":
    asyncio.run(run_agent("Check backend health, list vendors, then run a governed workflow for tenant 'veklom-demo' with intent 'Generate monthly revenue summary'."))
