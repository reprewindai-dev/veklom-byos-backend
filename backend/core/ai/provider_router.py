"""Provider routing for governed AI execution."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import AsyncIterator

import httpx
from fastapi import HTTPException

from backend.core.config.settings import settings


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


@dataclass
class CompletionResult:
    provider: str
    payload: dict


def _is_configured(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip()
    if not normalized:
        return False
    lowered = normalized.lower()
    blocked = ("need_from_", "your-", "your_", "example", "placeholder", "changeme")
    return not any(marker in lowered for marker in blocked)


def _provider_error(status_code: int, text: str) -> HTTPException:
    safe_status = status_code if 400 <= status_code < 600 else 502
    try:
        detail = json.loads(text)
    except json.JSONDecodeError:
        detail = {"error": text[:500] or "AI provider request failed"}
    return HTTPException(status_code=safe_status, detail=detail)


def normalize_messages(body: dict) -> list[dict[str, str]]:
    messages = body.get("messages")
    if isinstance(messages, list) and messages:
        return messages
    prompt = body.get("prompt") or body.get("input") or "Run a governed Veklom inference."
    return [{"role": "user", "content": str(prompt)}]


def _model_for(provider: str, body: dict) -> str:
    explicit = body.get("model")
    if explicit:
        return str(explicit).strip().strip('"')
    defaults = {
        "openai": "gpt-4o-mini",
        "groq": settings.GROQ_MODEL,
        "huggingface": settings.HF_MODEL,
        "gemini": settings.GEMINI_MODEL,
        "ollama": settings.OLLAMA_MODEL,
    }
    return defaults.get(provider, "gpt-4o-mini").strip().strip('"')


def _openai_payload(body: dict, provider: str, stream: bool) -> dict:
    payload = {
        "model": _model_for(provider, body),
        "messages": normalize_messages(body),
        "stream": stream,
    }
    for key in ("temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"):
        if key in body:
            payload[key] = body[key]
    return payload


def _configured_provider(provider: str) -> bool:
    provider = provider.lower()
    if provider == "openai":
        return _is_configured(settings.OPENAI_API_KEY)
    if provider == "groq":
        return _is_configured(settings.GROQ_API_KEY)
    if provider == "huggingface":
        return _is_configured(settings.HF_TOKEN) or _is_configured(settings.HUGGINGFACE_API_KEY)
    if provider == "gemini":
        return _is_configured(settings.GEMINI_API_KEY)
    if provider == "ollama":
        return _is_configured(settings.OLLAMA_BASE_URL)
    return False


def provider_order(body: dict) -> list[str]:
    raw = body.get("provider") or settings.LLM_PROVIDER or settings.DEFAULT_AI_PROVIDER or settings.AI_PROVIDER
    parts: list[str] = []
    for chunk in str(raw).replace(",", "/").split("/"):
        provider = chunk.strip().lower()
        if provider:
            parts.append(provider)

    fallback = (settings.AI_FALLBACK_PROVIDER or "").strip().lower()
    if fallback:
        parts.append(fallback)

    parts.extend(["ollama", "groq", "huggingface", "gemini", "openai"])

    ordered: list[str] = []
    for provider in parts:
        aliases = {"hf": "huggingface", "google": "gemini"}
        provider = aliases.get(provider, provider)
        if provider not in ordered:
            ordered.append(provider)
    return ordered


async def run_completion(body: dict, stream: bool = False) -> CompletionResult:
    errors: list[str] = []
    for provider in provider_order(body):
        if not _configured_provider(provider):
            errors.append(f"{provider}: not configured")
            continue
        try:
            if provider in {"openai", "groq", "huggingface"}:
                return CompletionResult(provider, await _openai_compatible(provider, body, stream=False))
            if provider == "gemini":
                return CompletionResult(provider, await _gemini_completion(body))
            if provider == "ollama":
                return CompletionResult(provider, await _ollama_completion(body))
        except HTTPException:
            raise
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
            continue
    raise HTTPException(status_code=503, detail={"error": "No configured AI provider succeeded", "providers": errors})


async def stream_completion(body: dict) -> AsyncIterator[str]:
    for provider in provider_order(body):
        if not _configured_provider(provider):
            continue
        if provider in {"openai", "groq", "huggingface"}:
            async for line in _openai_compatible_stream(provider, body):
                yield line
            return
        result = await run_completion({**body, "provider": provider}, stream=False)
        content = _content_from_openai_response(result.payload)
        yield _sse_chunk(result.provider, _model_for(result.provider, body), content)
        yield "data: [DONE]\n\n"
        return
    yield 'data: {"error":"No configured AI provider succeeded"}\n\n'
    yield "data: [DONE]\n\n"


async def _openai_compatible(provider: str, body: dict, stream: bool) -> dict:
    url, token = _openai_compatible_config(provider)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = _openai_payload(body, provider, stream)
    async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        raise _provider_error(response.status_code, response.text)
    return response.json()


async def _openai_compatible_stream(provider: str, body: dict) -> AsyncIterator[str]:
    url, token = _openai_compatible_config(provider)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = _openai_payload(body, provider, True)
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code >= 400:
                text = await response.aread()
                yield f"data: {json.dumps({'error': text.decode('utf-8', errors='replace')[:500]})}\n\n"
                yield "data: [DONE]\n\n"
                return
            async for line in response.aiter_lines():
                if line:
                    yield f"{line}\n\n"


def _openai_compatible_config(provider: str) -> tuple[str, str]:
    if provider == "openai":
        return OPENAI_CHAT_COMPLETIONS_URL, settings.OPENAI_API_KEY.strip()
    if provider == "groq":
        base = settings.GROQ_BASE_URL.rstrip("/") or "https://api.groq.com/openai/v1"
        return f"{base}/chat/completions", settings.GROQ_API_KEY.strip()
    base = settings.HF_API_URL.rstrip("/") or "https://router.huggingface.co/v1"
    token = settings.HF_TOKEN.strip() or settings.HUGGINGFACE_API_KEY.strip()
    return f"{base}/chat/completions", token


async def _gemini_completion(body: dict) -> dict:
    model = _model_for("gemini", body).replace(" ", "-").lower()
    if not model.startswith("gemini-"):
        model = settings.GEMINI_MODEL.strip().strip('"').replace(" ", "-").lower()
    messages = normalize_messages(body)
    prompt = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(url, params={"key": settings.GEMINI_API_KEY.strip()}, json=payload)
    if response.status_code >= 400:
        raise _provider_error(response.status_code, response.text)
    data = response.json()
    content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    return _openai_response("gemini", model, content)


async def _ollama_completion(body: dict) -> dict:
    base = settings.OLLAMA_BASE_URL.rstrip("/")
    model = _model_for("ollama", body)
    payload = {"model": model, "messages": normalize_messages(body), "stream": False}
    async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(f"{base}/api/chat", json=payload)
    if response.status_code >= 400:
        raise _provider_error(response.status_code, response.text)
    data = response.json()
    content = data.get("message", {}).get("content", "")
    return _openai_response("ollama", model, content)


def _openai_response(provider: str, model: str, content: str) -> dict:
    now = int(time.time())
    return {
        "id": f"{provider}-{now}",
        "object": "chat.completion",
        "created": now,
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _content_from_openai_response(payload: dict) -> str:
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def _sse_chunk(provider: str, model: str, content: str) -> str:
    data = {
        "id": f"{provider}-{int(time.time())}",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": "stop"}],
    }
    return f"data: {json.dumps(data)}\n\n"
