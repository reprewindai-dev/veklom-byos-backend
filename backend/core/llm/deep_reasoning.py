"""Extended thinking (deep reasoning) flag wrapper for Claude 3.7+."""
from __future__ import annotations

from typing import Any

import anthropic

from backend.core.config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

DEEP_REASONING_MODEL = "claude-sonnet-4-5"


async def complete_with_thinking(
    messages: list[dict],
    budget_tokens: int = 10_000,
    max_tokens: int = 16_000,
    system: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run a completion with extended thinking enabled.

    Returns the full message object so callers can inspect thinking blocks.
    """
    params: dict[str, Any] = dict(
        model=DEEP_REASONING_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "enabled", "budget_tokens": budget_tokens},
        messages=messages,
        **kwargs,
    )
    if system:
        params["system"] = system

    response = await _client.messages.create(**params)
    thinking_text = ""
    answer_text = ""
    for block in response.content:
        if block.type == "thinking":
            thinking_text = block.thinking
        elif block.type == "text":
            answer_text = block.text
    return {
        "thinking": thinking_text,
        "answer": answer_text,
        "usage": response.usage.model_dump(),
        "model": response.model,
    }
