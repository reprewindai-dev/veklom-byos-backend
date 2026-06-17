"""
Veklom Agent Router
===================
Dispatches to the correct LLM provider.
Default is OLLAMA (sovereign, zero cost).

Usage:
    python agents/agent_router.py ["your goal here"]

    VEKLOM_AGENT_PROVIDER=groq python agents/agent_router.py
    VEKLOM_AGENT_PROVIDER=ollama OLLAMA_MODEL=mistral python agents/agent_router.py

Providers:
    ollama      (DEFAULT) — local Hetzner, zero cost, fully sovereign
    groq        — cloud, sub-150ms, near-free
    openai      — cloud, best tool-call accuracy
    huggingface — open models, free tier or private endpoint
"""

import os
import sys
import asyncio
import json

# Ollama is the primary provider — default if nothing set
PROVIDER = os.getenv("VEKLOM_AGENT_PROVIDER", "ollama").lower()

DEFAULT_GOAL = (
    "Check the Veklom backend health, list all marketplace vendors and models, "
    "get revenue summary, and report IronGrid node status."
)
GOAL = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else os.getenv("AGENT_GOAL", DEFAULT_GOAL)


async def main():
    print(f"[ROUTER] Provider : {PROVIDER.upper()}")
    print(f"[ROUTER] Goal     : {GOAL}\n")

    if PROVIDER == "ollama":
        from agents.agent_ollama import run_agent
    elif PROVIDER == "groq":
        from agents.agent_groq import run_agent
    elif PROVIDER == "openai":
        from agents.agent_loop import run_agent
    elif PROVIDER == "gemini":
        from agents.agent_gemini import run_agent
    elif PROVIDER in ("huggingface", "hf"):
        from agents.agent_huggingface import run_agent
    else:
        raise ValueError(
            f"Unknown provider '{PROVIDER}'. "
            "Choose: ollama (default) | groq | openai | gemini | huggingface"
        )

    result = await run_agent(GOAL)
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    if isinstance(result, dict):
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
