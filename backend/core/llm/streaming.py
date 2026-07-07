"""SSE streaming endpoint helper for Anthropic / Ollama completions."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import anthropic
from fastapi import Request
from fastapi.responses import StreamingResponse

from backend.core.config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def _stream_anthropic(
    model: str,
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 4096,
    **kwargs: Any,
) -> AsyncIterator[str]:
    params: dict[str, Any] = dict(model=model, messages=messages, max_tokens=max_tokens, **kwargs)
    if system:
        params["system"] = system

    async with _client.messages.stream(**params) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'delta': text})}\n\n"
    yield "data: [DONE]\n\n"


def streaming_response(
    model: str,
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 4096,
    **kwargs: Any,
) -> StreamingResponse:
    """Return a FastAPI StreamingResponse for Server-Sent Events."""
    return StreamingResponse(
        _stream_anthropic(model, messages, system, max_tokens, **kwargs),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
