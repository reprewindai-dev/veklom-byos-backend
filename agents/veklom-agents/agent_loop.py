"""
Veklom AI Agent Loop — Level-3 Autonomous Agent
================================================
Implements the full THINK → ACT → OBSERVE → ITERATE cycle.

The agent receives a goal, reasons over it using an LLM,
calls real tools (Veklom backend, IronGrid, external APIs),
observes results, and decides whether to iterate or stop.

Usage:
    python agents/agent_loop.py

Required env vars (add to .env or Coolify secrets):
    VEKLOM_API_URL   — e.g. https://veklom.com/api/v1
    VEKLOM_API_KEY   — JWT or API key from /auth/login
    OPENAI_API_KEY   — for the reasoning LLM (swap for Gemini/Groq freely)
    MCP_SERVER_URL   — URL of your running irongrid/server.py (SSE mode)
"""

import os
import json
import asyncio
import httpx
from typing import Any

try:
    from openai import AsyncOpenAI
except ImportError:
    raise SystemExit("pip install openai  (or swap for your preferred LLM client)")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VEKLOM_API_URL = os.getenv("VEKLOM_API_URL", "https://veklom.com/api/v1")
VEKLOM_API_KEY = os.getenv("VEKLOM_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# Tool registry  — add new tools here; each is a plain async function
# ---------------------------------------------------------------------------
async def tool_check_backend_health() -> dict:
    """Ping the Veklom backend and return health status."""
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(f"{VEKLOM_API_URL}/health")
        return {"status": r.status_code, "body": r.json()}


async def tool_run_governed_workflow(
    transaction_id: str,
    tenant_id: str,
    payload_intent: str,
    origin_x: int = 0,
    origin_y: int = 0,
) -> dict:
    """Submit a governed workflow task to the Veklom backend."""
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{VEKLOM_API_URL}/workflows/execute",
            headers={"Authorization": f"Bearer {VEKLOM_API_KEY}"},
            json={
                "transaction_id": transaction_id,
                "tenant_id": tenant_id,
                "payload_intent": payload_intent,
                "origin_x": origin_x,
                "origin_y": origin_y,
            },
        )
        return {"status": r.status_code, "body": r.text}


async def tool_list_vendors() -> dict:
    """List registered vendors from the Veklom marketplace."""
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(
            f"{VEKLOM_API_URL}/marketplace/vendors",
            headers={"Authorization": f"Bearer {VEKLOM_API_KEY}"},
        )
        return {"status": r.status_code, "vendors": r.json()}


TOOL_MAP: dict[str, Any] = {
    "check_backend_health": tool_check_backend_health,
    "run_governed_workflow": tool_run_governed_workflow,
    "list_vendors": tool_list_vendors,
}

# OpenAI function-calling schema (auto-generated from docstrings)
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
                    "origin_x": {"type": "integer", "default": 0},
                    "origin_y": {"type": "integer", "default": 0},
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


# ---------------------------------------------------------------------------
# Core agent loop
# ---------------------------------------------------------------------------
async def run_agent(goal: str) -> str:
    """
    Level-3 Agent loop: THINK → ACT → OBSERVE → ITERATE → DONE.

    Args:
        goal: Natural-language objective for the agent.

    Returns:
        Final answer string once the agent judges the goal achieved.
    """
    print(f"\n[AGENT] Goal: {goal}")
    messages = [
        {
            "role": "system",
            "content": (
                "You are the Veklom Autonomous Agent.  "
                "You have tools to interact with the Veklom sovereign AI backend. "
                "Reason step-by-step. Call tools when needed. "
                "When you have enough information to fully satisfy the user's goal, "
                "respond with a final plain-text answer — do NOT call any more tools."
            ),
        },
        {"role": "user", "content": goal},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n[AGENT] — Iteration {iteration} — THINKING...")

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_unset=True))

        # --- No tool call → agent is done ---------------------------------
        if not msg.tool_calls:
            final = msg.content or "[Agent produced no output]"
            print(f"\n[AGENT] DONE after {iteration} iteration(s).")
            print(f"[AGENT] Final output:\n{final}")
            return final

        # --- Execute every tool call the LLM requested --------------------
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments or "{}")
            print(f"[AGENT] ACT  → {fn_name}({fn_args})")

            if fn_name not in TOOL_MAP:
                observation = {"error": f"Unknown tool: {fn_name}"}
            else:
                try:
                    observation = await TOOL_MAP[fn_name](**fn_args)
                except Exception as exc:
                    observation = {"error": str(exc)}

            print(f"[AGENT] OBSERVE ← {json.dumps(observation)[:200]}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(observation),
                }
            )

    return "[AGENT] Max iterations reached without a final answer."


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    goal = (
        "Check that the Veklom backend is healthy, "
        "then list the current marketplace vendors, "
        "and finally run a governed workflow for tenant 'demo-tenant' "
        "with the intent 'Summarise Q2 sales report'."
    )
    asyncio.run(run_agent(goal))
