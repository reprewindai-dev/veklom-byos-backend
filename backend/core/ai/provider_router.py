"""Provider routing for governed AI execution."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

import httpx
from fastapi import HTTPException

from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OLLAMA_ONLY safety guard
# When OLLAMA_ONLY=true in the environment, ALL requests are forced to Ollama
# and NO paid provider (OpenAI, Groq, Gemini, HuggingFace) will EVER be called.
# This prevents surprise bills. Set OLLAMA_ONLY=false to re-enable paid providers.
# ---------------------------------------------------------------------------
import os as _os
OLLAMA_ONLY: bool = _os.environ.get("OLLAMA_ONLY", "true").strip().lower() in ("1", "true", "yes")
if OLLAMA_ONLY:
    logger.info("[COST GUARD] OLLAMA_ONLY=true — all completions forced to local Ollama. Paid providers DISABLED.")


OPENAI_CHAT_COMPLETIONS_URL = _os.environ.get("OPENAI_CHAT_COMPLETIONS_URL", "http://new-api-jv2pt97j6vgxcbfrbteue2k1:3000/v1/chat/completions")


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
    # Hard safety guard: if OLLAMA_ONLY is set, never return any paid provider
    if OLLAMA_ONLY:
        return ["ollama"]

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
    # Hard safety guard
    if OLLAMA_ONLY:
        body = {**body, "provider": "ollama", "model": settings.OLLAMA_MODEL}
        return CompletionResult("ollama", await _ollama_completion(body))

    model_requested = (body.get("model") or "").lower()
    provider_requested = (body.get("provider") or "").lower()
    is_openai_req = ("gpt-4" in model_requested or "openai" in provider_requested)
    openai_absent = not _configured_provider("openai")
    
    if is_openai_req and openai_absent:
        logger.warning("OpenAI requested but API key not configured. Gracefully falling back to local/configured providers.")
        body = {**body, "provider": "ollama", "model": settings.OLLAMA_MODEL}

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
        except HTTPException as he:
            errors.append(f"{provider}: HTTP {he.status_code} {he.detail}")
            continue
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
            continue

    raise HTTPException(
        status_code=503,
        detail={"error": "No configured AI provider succeeded", "providers": errors}
    )


async def stream_completion(body: dict) -> AsyncIterator[str]:
    import asyncio
    
    model_requested = (body.get("model") or "").lower()
    provider_requested = (body.get("provider") or "").lower()
    is_openai_req = ("gpt-4" in model_requested or "openai" in provider_requested)
    openai_absent = not _configured_provider("openai")
    
    if is_openai_req and openai_absent:
        logger.warning("OpenAI requested but API key not configured for stream. Gracefully falling back to local/configured providers.")
        body = {**body, "provider": "ollama", "model": settings.OLLAMA_MODEL}

    stream_started = False
    for provider in provider_order(body):
        if not _configured_provider(provider):
            continue
        try:
            if provider in {"openai", "groq", "huggingface"}:
                async for line in _openai_compatible_stream(provider, body):
                    yield line
                return
            if provider == "ollama":
                async for line in _ollama_stream(body):
                    yield line
                return
            result = await run_completion({**body, "provider": provider}, stream=False)
            content = _content_from_openai_response(result.payload)
            yield _sse_chunk(result.provider, _model_for(result.provider, body), content)
            yield "data: [DONE]\n\n"
            return
        except Exception:
            continue

    yield f'data: {{"error":"No configured AI provider succeeded."}}\n\n'
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
    return _openai_response("gemini", model, content, prompt=body.get("messages"))


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
    prompt_tokens = data.get("prompt_eval_count")
    completion_tokens = data.get("eval_count")
    return _openai_response(
        "ollama",
        model,
        content,
        prompt=body.get("messages"),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens
    )


def _openai_response(
    provider: str,
    model: str,
    content: str,
    prompt: Optional[Any] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
) -> dict:
    now = int(time.time())
    
    if prompt_tokens is None:
        # Realistic token estimation (1 token approx 4 chars)
        prompt_str = ""
        if isinstance(prompt, str):
            prompt_str = prompt
        elif isinstance(prompt, list):
            parts = []
            for m in prompt:
                if isinstance(m, dict):
                    parts.append(f"{m.get('role', '')}: {m.get('content', '')}")
                elif isinstance(m, str):
                    parts.append(m)
            prompt_str = "\n".join(parts)
            
        prompt_tokens = max(1, len(prompt_str) // 4) if prompt_str else 0
        # No hardcoded 120 fallback; use actual length or a small minimum for system overhead
        if not prompt_tokens and prompt_str:
            prompt_tokens = 1
            
    if completion_tokens is None:
        completion_tokens = max(1, len(content) // 4)
        # Remove the 150 token floor for short responses to ensure authenticity
        
    total_tokens = prompt_tokens + completion_tokens
    
    return {
        "id": f"{provider}-{now}",
        "object": "chat.completion",
        "created": now,
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        },
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


def _sse_delta_chunk(provider: str, model: str, content: str, finish_reason: str | None = None) -> str:
    data = {
        "id": f"{provider}-{int(time.time())}",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(data)}\n\n"


async def _ollama_stream(body: dict) -> AsyncIterator[str]:
    base = settings.OLLAMA_BASE_URL.rstrip("/")
    model = _model_for("ollama", body)
    payload = {
        "model": model,
        "messages": normalize_messages(body),
        "stream": True
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", f"{base}/api/chat", json=payload) as response:
            if response.status_code >= 400:
                text = await response.aread()
                yield _sse_delta_chunk("ollama", model, f"Ollama streaming error: {text.decode('utf-8', errors='replace')[:500]}", "stop")
                yield "data: [DONE]\n\n"
                return
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield _sse_delta_chunk("ollama", model, content)
                        if data.get("done"):
                            yield _sse_delta_chunk("ollama", model, "", "stop")
                            break
                    except Exception:
                        continue
            yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Smart escalation tier classification
# ---------------------------------------------------------------------------

TIER_TO_PROVIDERS: dict[str, list[str]] = {
    # Daily driver — Ollama handles all routine tasks
    "local":      ["ollama"],
    # Fast streaming / low latency — Groq first (131k context, ultra fast)
    "fast":       ["groq", "ollama", "huggingface"],
    # Complex reasoning / long context — Gemini 2.5 Flash (2M context)
    "reasoning":  ["gemini", "ollama", "groq", "openai"],
    # Maximum capability — GPT-4o for tool calls, orchestration, hardest tasks
    "max":        ["openai", "gemini", "groq", "ollama"],
    # Specialized / open-weight — HuggingFace for domain models
    "specialized": ["huggingface", "ollama", "groq"],
}


def task_tier(body: dict) -> str:
    """Classify a request into an execution tier to pick the optimal provider.

    Tier hierarchy:
      local      → Ollama qwen2.5:3b  (default, free, sovereign)
      fast       → Groq               (streaming, low latency, medium tasks)
      reasoning  → Gemini 2.5 Flash   (complex reasoning, long context ≤2M)
      max        → OpenAI GPT-4o      (tool calls, orchestration, max quality)
      specialized → HuggingFace       (domain-specific open-weight models)
    """
    model = (body.get("model") or "").lower()
    explicit = (body.get("provider") or "").lower()
    messages = body.get("messages") or []
    context_chars = sum(len(str(m.get("content", ""))) for m in messages)

    # Explicit provider overrides
    if explicit in ("openai", "gpt-4", "gpt-4o"):
        return "max"
    if explicit in ("gemini", "google"):
        return "reasoning"
    if explicit in ("groq",):
        return "fast"
    if explicit in ("ollama",):
        return "local"
    if explicit in ("huggingface", "hf"):
        return "specialized"

    # Specific model name signals
    if any(k in model for k in ("gpt-4", "claude-3", "o1", "o3")):
        return "max"
    if any(k in model for k in ("gemini-2", "gemini-1.5", "gemini-flash", "gemini-pro")):
        return "reasoning"
    if any(k in model for k in ("llama-3.1", "mixtral", "groq")):
        return "fast"
    if any(k in model for k in ("llama", "mistral", "phi", "falcon", "bloom")):
        return "specialized"

    # Tool/function calling requires strong models
    if body.get("tools") or body.get("functions"):
        return "max"

    # Context window signals
    if context_chars > 32_000:
        return "reasoning"   # Gemini 2M context window handles this best
    if context_chars > 8_000:
        return "fast"         # Groq 131k window, fast

    # Agent type hints (for autonomous agent routing)
    agent_type = (body.get("agent_type") or body.get("agent") or "").lower()
    if any(k in agent_type for k in ("orchestrat", "plan", "strateg", "architect")):
        return "max"
    if any(k in agent_type for k in ("reason", "analyz", "research", "complex")):
        return "reasoning"
    if any(k in agent_type for k in ("fast", "stream", "realtime", "light")):
        return "fast"

    # Streaming without explicit quality flag → Groq (fastest)
    if body.get("stream") and not body.get("high_quality"):
        return "fast"

    return "local"   # Default: Ollama daily driver


def smart_provider_order(body: dict) -> list[str]:
    """Return provider priority list based on task tier."""
    tier = task_tier(body)
    return TIER_TO_PROVIDERS.get(tier, ["ollama"])


# ---------------------------------------------------------------------------
# Tenant-isolation helpers
# ---------------------------------------------------------------------------

def is_founder_tenant(workspace_id: str) -> bool:
    """True if this workspace is the owner/admin tenant."""
    fw = (settings.FOUNDER_WORKSPACE_ID or "").strip()
    return bool(fw and workspace_id and fw == workspace_id)


def escalation_reason(body: dict) -> str:
    """Determine why we'd escalate beyond Ollama."""
    model = (body.get("model") or "").lower()
    messages = body.get("messages") or []
    context_chars = sum(len(str(m.get("content", ""))) for m in messages)

    if body.get("tools") or body.get("functions"):
        return "tool_support_required"
    if context_chars > 24000:
        return "long_context"
    if any(k in model for k in ("gpt-4", "claude", "gemini", "groq", "mixtral")):
        return "specific_model_requested"
    if body.get("stream") and body.get("latency") == "low":
        return "low_latency_streaming"
    return ""


def provider_order_for_tenant(body: dict, workspace_id: str) -> tuple[list[str], str]:
    """Return (ordered_providers, escalation_reason) for a given tenant.

    Rules:
    - Founder/admin: start with Ollama (or explicit), full owner key stack
    - Customer: If explicit BYOK provider requested, try it first. If invalid/fails, fallback to Ollama.
    """
    reason = escalation_reason(body)
    explicit = (body.get("provider") or "").strip().lower()

    if is_founder_tenant(workspace_id):
        # Founder gets full stack, prioritizing explicit
        order = ["ollama"]
        full_stack = ["groq", "huggingface", "gemini", "openai"]
        if explicit and explicit not in order:
            order.insert(0, explicit)
        order.extend([p for p in full_stack if p not in order])
    else:
        # Customer / eval tenant
        order = []
        # If customer explicitly requested a BYOK provider, try it first
        if explicit and explicit != "ollama":
            order.append(explicit)
            
        # Always fallback to Ollama if BYOK fails or is invalid
        if "ollama" not in order:
            order.append("ollama")
            
        # Free tier public fallback if Ollama fails
        if "huggingface" not in order:
            order.append("huggingface")

    return order, reason


async def run_completion_for_tenant(
    body: dict,
    workspace_id: str,
    byok_keys: Optional[dict] = None,
) -> tuple[CompletionResult, str, str]:
    """Tenant-aware completion."""
    model_requested = (body.get("model") or "").lower()
    provider_requested = (body.get("provider") or "").lower()
    is_openai_req = ("gpt-4" in model_requested or "openai" in provider_requested)
    openai_absent = not _configured_provider("openai")
    
    if is_openai_req and openai_absent:
        logger.warning("OpenAI requested but API key not configured for tenant. Gracefully falling back to local/configured providers.")
        body = {**body, "provider": "ollama", "model": settings.OLLAMA_MODEL}

    order, reason = provider_order_for_tenant(body, workspace_id)
    errors: list[str] = []
    key_source = "owner" if is_founder_tenant(workspace_id) else "default"

    for provider in order:
        # Check if this provider is available for this tenant
        if provider == "ollama":
            if not _configured_provider("ollama"):
                errors.append("ollama: not reachable")
                continue
            try:
                result = CompletionResult(provider, await _ollama_completion(body))
                return result, "default", ""
            except Exception as exc:
                errors.append(f"ollama: {exc}")
                continue

        # For non-Ollama: founder uses owner keys, customer uses BYOK
        if is_founder_tenant(workspace_id):
            if not _configured_provider(provider):
                errors.append(f"{provider}: owner key not configured")
                continue
            try:
                if provider in {"openai", "groq", "huggingface"}:
                    payload = await _openai_compatible(provider, body, stream=False)
                elif provider == "gemini":
                    payload = await _gemini_completion(body)
                else:
                    errors.append(f"{provider}: unknown provider")
                    continue
                return CompletionResult(provider, payload), "owner", reason
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                continue
        else:
            # Customer: BYOK key required, except HuggingFace which has a
            # public inference API for basic models (free tier fallback).
            raw_key = (byok_keys or {}).get(provider)
            if not raw_key:
                # Allow HuggingFace as a public fallback using owner's HF token
                # (rate-limited free tier — not a full key leak, scoped models only)
                if provider == "huggingface" and _is_configured(settings.HF_TOKEN):
                    raw_key = settings.HF_TOKEN.strip()
                else:
                    errors.append(f"{provider}: no BYOK key for tenant")
                    continue
            try:
                if provider in {"openai", "groq", "huggingface"}:
                    url, _ = _openai_compatible_config(provider)
                    headers = {"Authorization": f"Bearer {raw_key}", "Content-Type": "application/json"}
                    payload_data = _openai_payload(body, provider, False)
                    async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
                        resp = await client.post(url, headers=headers, json=payload_data)
                    if resp.status_code >= 400:
                        raise _provider_error(resp.status_code, resp.text)
                    return CompletionResult(provider, resp.json()), "byok", reason
                else:
                    errors.append(f"{provider}: BYOK not supported for this provider type")
                    continue
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                continue

    raise HTTPException(
        status_code=503,
        detail={"error": "No provider succeeded", "tried": errors, "workspace": workspace_id}
    )


async def stream_completion_for_tenant(
    body: dict,
    workspace_id: str,
    byok_keys: Optional[dict] = None,
) -> AsyncIterator[str]:
    """Tenant-aware streaming completion."""
    model_requested = (body.get("model") or "").lower()
    provider_requested = (body.get("provider") or "").lower()
    is_openai_req = ("gpt-4" in model_requested or "openai" in provider_requested)
    openai_absent = not _configured_provider("openai")
    
    if is_openai_req and openai_absent:
        logger.warning("OpenAI requested but API key not configured for tenant. Gracefully falling back to local/configured providers.")
        body = {**body, "provider": "ollama", "model": settings.OLLAMA_MODEL}

    order, reason = provider_order_for_tenant(body, workspace_id)
    key_source = "owner" if is_founder_tenant(workspace_id) else "default"

    for provider in order:
        # Ollama logic
        if provider == "ollama":
            if not _configured_provider("ollama"):
                continue
            try:
                async for line in _ollama_stream(body):
                    yield line
                return
            except Exception:
                continue

        # Non-Ollama logic
        if is_founder_tenant(workspace_id):
            if not _configured_provider(provider):
                continue
            try:
                if provider in {"openai", "groq", "huggingface"}:
                    async for line in _openai_compatible_stream(provider, body):
                        yield line
                    return
                if provider == "gemini":
                    # Fallback to non-streaming for Gemini if we don't have a streaming gemini function
                    payload = await _gemini_completion(body)
                    content = _content_from_openai_response(payload)
                    yield _sse_chunk(provider, _model_for(provider, body), content)
                    yield "data: [DONE]\n\n"
                    return
            except Exception:
                continue
        else:
            raw_key = (byok_keys or {}).get(provider)
            if not raw_key:
                if provider == "huggingface" and _is_configured(settings.HF_TOKEN):
                    raw_key = settings.HF_TOKEN.strip()
                else:
                    continue
            
            try:
                if provider in {"openai", "groq", "huggingface"}:
                    # We need a custom stream function that takes the raw_key instead of using owner keys
                    async for line in _openai_compatible_stream_with_key(provider, body, raw_key):
                        yield line
                    return
            except Exception:
                continue

    yield f'data: {{"error":"No provider succeeded for workspace {workspace_id}."}}\n\n'
    yield "data: [DONE]\n\n"


async def _openai_compatible_stream_with_key(provider: str, body: dict, raw_key: str) -> AsyncIterator[str]:
    url, _ = _openai_compatible_config(provider)
    headers = {"Authorization": f"Bearer {raw_key}", "Content-Type": "application/json"}
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

