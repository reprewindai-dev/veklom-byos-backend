"""
Veklom Agent — Hugging Face Inference Provider
===============================================
Runs the Level-3 agent loop using Hugging Face's
Serverless Inference API or Inference Endpoints.

Two modes:
    1. HF Serverless  — free tier, hosted by HF, 1000s of models
    2. HF Endpoint    — your own dedicated endpoint (set HF_ENDPOINT_URL)

Recommended models:
    mistralai/Mistral-7B-Instruct-v0.3   ← best open-source for tool use
    meta-llama/Meta-Llama-3-8B-Instruct  ← strong reasoning
    HuggingFaceH4/zephyr-7b-beta         ← fast + instruction-tuned
    microsoft/Phi-3-mini-4k-instruct     ← ultra-lightweight

Env vars:
    HF_API_TOKEN      from huggingface.co/settings/tokens
    HF_MODEL          default: mistralai/Mistral-7B-Instruct-v0.3
    HF_ENDPOINT_URL   (optional) your private endpoint URL
    VEKLOM_API_URL    e.g. https://veklom.com/api/v1
    VEKLOM_API_KEY    JWT from /auth/login
"""

import os
import json
import asyncio
import httpx

HF_API_TOKEN   = os.getenv("HF_API_TOKEN",  "")
HF_MODEL       = os.getenv("HF_MODEL",      "mistralai/Mistral-7B-Instruct-v0.3")
HF_ENDPOINT    = os.getenv("HF_ENDPOINT_URL", "")
VEKLOM_API_URL = os.getenv("VEKLOM_API_URL",  "https://veklom.com/api/v1")
VEKLOM_API_KEY = os.getenv("VEKLOM_API_KEY",  "")
MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))

# Resolve inference URL: private endpoint takes priority
if HF_ENDPOINT:
    HF_INFER_URL = HF_ENDPOINT
else:
    HF_INFER_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}/v1/chat/completions"

# ---------------------------------------------------------------------------
# Tools
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

TOOL_DESCRIPTIONS = """
You have these tools. To call one, output ONLY a JSON object:

{"tool": "check_backend_health", "args": {}}
{"tool": "run_governed_workflow", "args": {"transaction_id": "<id>", "tenant_id": "<id>", "payload_intent": "<text>"}}
{"tool": "list_vendors", "args": {}}

When the goal is complete, output:
{"done": true, "answer": "<final answer>"}

Never output anything else while using tools — ONLY valid JSON.
"""


async def hf_chat(messages: list[dict]) -> str:
    """Call HuggingFace Inference API (OpenAI-compatible endpoint)."""
    async with httpx.AsyncClient(timeout=120) as http:
        r = await http.post(
            HF_INFER_URL,
            headers={
                "Authorization": f"Bearer {HF_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "model": HF_MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.1,  # low temp for deterministic tool calls
            },
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


async def run_agent(goal: str) -> str:
    print(f"\n[HF AGENT] Goal: {goal}")
    print(f"[HF AGENT] Model: {HF_MODEL}")
    print(f"[HF AGENT] Endpoint: {HF_INFER_URL}")

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Veklom Autonomous Agent. "
                "Achieve the user's goal using the available tools. "
                "Reason step by step.\n\n" + TOOL_DESCRIPTIONS
            ),
        },
        {"role": "user", "content": goal},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n[HF AGENT] — Iteration {iteration} — THINKING...")
        raw = await hf_chat(messages)
        print(f"[HF AGENT] LLM: {raw[:300]}")
        messages.append({"role": "assistant", "content": raw})

        try:
            clean = raw.strip().strip("```json").strip("```").strip()
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            print("[HF AGENT] Non-JSON — final answer.")
            return raw

        if parsed.get("done"):
            answer = parsed.get("answer", raw)
            print(f"\n[HF AGENT] DONE.\n{answer}")
            return answer

        tool_name = parsed.get("tool")
        tool_args = parsed.get("args", {})

        if tool_name not in TOOL_MAP:
            observation = {"error": f"Unknown tool: {tool_name}"}
        else:
            print(f"[HF AGENT] ACT → {tool_name}({tool_args})")
            try:
                observation = await TOOL_MAP[tool_name](**tool_args)
            except Exception as exc:
                observation = {"error": str(exc)}

        print(f"[HF AGENT] OBSERVE ← {json.dumps(observation)[:200]}")
        messages.append({"role": "user", "content": f"Tool result: {json.dumps(observation)}"})

    return "[HF AGENT] Max iterations reached."


if __name__ == "__main__":
    asyncio.run(run_agent("Check backend health and list all Veklom marketplace vendors."))
