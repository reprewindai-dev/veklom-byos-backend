"""
Veklom Agent Router — Multi-Provider Dispatcher
================================================
Select which LLM provider powers your agent at runtime
by setting the VEKLOM_AGENT_PROVIDER env var.

Providers:
    openai      — GPT-4o-mini (cloud, best tool-calling accuracy)
    groq        — Llama 3.3 70B via Groq (fastest, near-free)
    ollama      — Any local model on Hetzner (zero cost, sovereign)
    huggingface — HF Serverless or private Endpoint

Usage:
    VEKLOM_AGENT_PROVIDER=groq python agents/agent_router.py
    VEKLOM_AGENT_PROVIDER=ollama OLLAMA_MODEL=mistral python agents/agent_router.py
"""

import os
import asyncio

PROVIDER = os.getenv("VEKLOM_AGENT_PROVIDER", "groq").lower()

DEFAULT_GOAL = (
    "Check the Veklom backend health, list all vendors, "
    "then run a governed workflow for tenant 'veklom-demo' "
    "with intent 'Automated revenue pipeline audit'."
)
GOAL = os.getenv("AGENT_GOAL", DEFAULT_GOAL)


async def main():
    print(f"[ROUTER] Provider selected: {PROVIDER.upper()}")
    print(f"[ROUTER] Goal: {GOAL}\n")

    if PROVIDER == "openai":
        from agents.agent_loop import run_agent
    elif PROVIDER == "groq":
        from agents.agent_groq import run_agent
    elif PROVIDER == "ollama":
        from agents.agent_ollama import run_agent
    elif PROVIDER == "huggingface" or PROVIDER == "hf":
        from agents.agent_huggingface import run_agent
    else:
        raise ValueError(
            f"Unknown provider '{PROVIDER}'. "
            "Choose: openai | groq | ollama | huggingface"
        )

    result = await run_agent(GOAL)
    print(f"\n[ROUTER] Final Result:\n{result}")


if __name__ == "__main__":
    asyncio.run(main())
