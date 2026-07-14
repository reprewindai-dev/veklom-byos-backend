"""
Veklom Agent — Gemini Provider (Advanced Multi-modal & Flash Reasoning)
=======================================================================
Runs the Level-3 agent loop using Google Gemini API.

Models available on Gemini:
    gemini-1.5-flash        ← recommended (fast / cost-efficient)
    gemini-1.5-pro          ← deep reasoning
    gemini-2.5-flash        ← next-gen fast
    gemini-2.5-pro          ← next-gen maximum capability

Env vars:
    GEMINI_API_KEY      from Google AI Studio
    GEMINI_MODEL        default: gemini-1.5-flash
    VEKLOM_API_URL      e.g. https://veklom.com/api/v1
    VEKLOM_API_KEY      JWT from /auth/login
"""

import os
import json
import asyncio
import httpx
from openai import AsyncOpenAI

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL",   "gemini-1.5-flash")
VEKLOM_API_URL = os.getenv("VEKLOM_API_URL", "https://veklom.com/api/v1")
VEKLOM_API_KEY = os.getenv("VEKLOM_API_KEY", "")
MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))

# Base URL for Gemini OpenAI Compatibility Endpoint
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

client = AsyncOpenAI(
    api_key=GEMINI_API_KEY,
    base_url=GEMINI_BASE_URL
)

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

async def run_agent(goal: str) -> str:
    print(f"\n[GEMINI AGENT] Goal: {goal}")
    print(f"[GEMINI AGENT] Model: {GEMINI_MODEL}")

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Veklom Autonomous Agent powered by Google Gemini. "
                "Use the provided tools to achieve the user's goal step by step. "
                "Call tools as needed. When the goal is fully achieved, respond with a plain final answer."
            ),
        },
        {"role": "user", "content": goal},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n[GEMINI AGENT] — Iteration {iteration} — THINKING...")
        
        response = await client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto"
        )
        
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_unset=True))

        tool_calls = msg.tool_calls or []

        if not tool_calls:
            answer = msg.content or "[No output]"
            print(f"\n[GEMINI AGENT] DONE.\n{answer}")
            return answer

        for tc in tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments or "{}")
            print(f"[GEMINI AGENT] ACT → {fn_name}({fn_args})")

            observation = await TOOL_MAP.get(fn_name, lambda **_: {"error": f"Unknown tool: {fn_name}"})(**fn_args) \
                if fn_name in TOOL_MAP else {"error": f"Unknown tool: {fn_name}"}

            print(f"[GEMINI AGENT] OBSERVE ← {json.dumps(observation)[:200]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(observation),
            })

    return "[GEMINI AGENT] Max iterations reached."

if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("[GEMINI AGENT] GEMINI_API_KEY is not set.")
    else:
        asyncio.run(run_agent("Check backend health and list all vendors."))
