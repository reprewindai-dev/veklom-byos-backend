"""
Veklom Agent — Groq Provider (Ultra-Fast Inference)
====================================================
Runs the Level-3 agent loop using Groq's API.
Groq delivers sub-100ms first-token latency — ideal for
high-throughput automated pipelines.

Models available on Groq:
    llama-3.3-70b-versatile   ← recommended (best balance)
    llama-3.1-8b-instant      ← fastest / cheapest
    mixtral-8x7b-32768        ← good for long context
    gemma2-9b-it              ← Google Gemma

Env vars:
    GROQ_API_KEY    from console.groq.com
    GROQ_MODEL      default: llama-3.3-70b-versatile
    VEKLOM_API_URL  e.g. https://veklom.com/api/v1
    VEKLOM_API_KEY  JWT from /auth/login
"""

import os
import json
import asyncio
import httpx

GROQ_API_KEY   = os.getenv("GROQ_API_KEY",  "")
GROQ_MODEL     = os.getenv("GROQ_MODEL",    "llama-3.3-70b-versatile")
VEKLOM_API_URL = os.getenv("VEKLOM_API_URL", "https://veklom.com/api/v1")
VEKLOM_API_KEY = os.getenv("VEKLOM_API_KEY", "")
MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))

GROQ_BASE_URL  = "https://api.groq.com/openai/v1"  # OpenAI-compatible

# ---------------------------------------------------------------------------
# Tools — identical interface across all provider agents
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
    "check_backend_health":  tool_check_backend_health,
    "run_governed_workflow": tool_run_governed_workflow,
    "list_vendors":          tool_list_vendors,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_backend_health",
            "description": "Ping the Veklom backend and return health status.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_governed_workflow",
            "description": "Submit a governed workflow task to the Veklom backend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "payload_intent": {"type": "string"},
                    "origin_x": {"type": "integer"},
                    "origin_y": {"type": "integer"},
                },
                "required": ["transaction_id", "tenant_id", "payload_intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_vendors",
            "description": "List registered vendors from the Veklom marketplace.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


async def groq_chat(messages: list[dict], tools: list) -> dict:
    """Call Groq's OpenAI-compatible chat endpoint."""
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "tools": tools, "tool_choice": "auto"},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]


async def run_agent(goal: str) -> str:
    print(f"\n[GROQ AGENT] Goal: {goal}")
    print(f"[GROQ AGENT] Model: {GROQ_MODEL}")

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Veklom Autonomous Agent. "
                "Use the provided tools to achieve the user's goal step by step. "
                "Call tools as needed. When the goal is fully achieved, respond with a plain final answer."
            ),
        },
        {"role": "user", "content": goal},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n[GROQ AGENT] — Iteration {iteration} — THINKING...")
        msg = await groq_chat(messages, TOOL_SCHEMAS)
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            answer = msg.get("content", "[No output]")
            print(f"\n[GROQ AGENT] DONE.\n{answer}")
            return answer

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"].get("arguments", "{}"))
            print(f"[GROQ AGENT] ACT → {fn_name}({fn_args})")

            observation = await TOOL_MAP.get(fn_name, lambda **_: {"error": f"Unknown tool: {fn_name}"})(**fn_args) \
                if fn_name in TOOL_MAP else {"error": f"Unknown tool: {fn_name}"}

            print(f"[GROQ AGENT] OBSERVE ← {json.dumps(observation)[:200]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(observation),
            })

    return "[GROQ AGENT] Max iterations reached."


if __name__ == "__main__":
    asyncio.run(run_agent("Check the Veklom backend health, list all vendors, then execute a governed workflow for tenant 'enterprise-1' with intent 'Quarterly compliance audit automation'."))
