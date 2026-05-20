"""SSE streaming exec endpoint (OpenAI-compatible)."""

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.core.config.settings import settings
from backend.core.security.auth import get_current_user

router = APIRouter(tags=["AI Exec SSE"])

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


def _provider_headers() -> dict[str, str]:
    api_key = settings.OPENAI_API_KEY.strip()
    if not api_key or api_key.startswith("NEED_FROM_"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _normalize_messages(body: dict) -> list[dict[str, str]]:
    messages = body.get("messages")
    if isinstance(messages, list) and messages:
        return messages

    prompt = body.get("prompt") or body.get("input") or ""
    if not prompt:
        prompt = "Run a governed Veklom inference."
    return [{"role": "user", "content": str(prompt)}]


def _openai_payload(body: dict, stream: bool) -> dict:
    payload = {
        "model": body.get("model") or "gpt-4o-mini",
        "messages": _normalize_messages(body),
        "stream": stream,
    }
    for key in ("temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"):
        if key in body:
            payload[key] = body[key]
    return payload


def _provider_error(status_code: int, text: str) -> HTTPException:
    safe_status = status_code if 400 <= status_code < 600 else 502
    try:
        detail = json.loads(text)
    except json.JSONDecodeError:
        detail = {"error": text[:500] or "AI provider request failed"}
    return HTTPException(status_code=safe_status, detail=detail)


@router.post("/v1/exec")
async def exec_stream(request: Request, user=Depends(get_current_user)):
    body = await request.json()
    stream = body.get("stream", True)
    payload = _openai_payload(body, stream=stream)
    headers = _provider_headers()

    if not stream:
        async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(OPENAI_CHAT_COMPLETIONS_URL, headers=headers, json=payload)
        if response.status_code >= 400:
            raise _provider_error(response.status_code, response.text)
        return response.json()

    async def event_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", OPENAI_CHAT_COMPLETIONS_URL, headers=headers, json=payload) as response:
                if response.status_code >= 400:
                    text = await response.aread()
                    error = {"error": text.decode("utf-8", errors="replace")[:500]}
                    yield f"data: {json.dumps(error)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
