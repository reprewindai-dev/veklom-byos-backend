"""Redis-backed prompt cache for LLM response deduplication."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from backend.core.config import settings

_pool: Optional[aioredis.Redis] = None


def _client() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _pool


def _cache_key(model: str, messages: list[dict], **kwargs: Any) -> str:
    payload = json.dumps({"model": model, "messages": messages, "kwargs": kwargs}, sort_keys=True)
    return "prompt_cache:" + hashlib.sha256(payload.encode()).hexdigest()


async def get_cached(model: str, messages: list[dict], **kwargs: Any) -> Optional[str]:
    """Return cached completion text or None."""
    key = _cache_key(model, messages, **kwargs)
    return await _client().get(key)


async def set_cached(
    model: str,
    messages: list[dict],
    response: str,
    ttl: int = 3600,
    **kwargs: Any,
) -> None:
    """Store completion text with TTL (default 1 h)."""
    key = _cache_key(model, messages, **kwargs)
    await _client().setex(key, ttl, response)


async def invalidate(model: str, messages: list[dict], **kwargs: Any) -> None:
    key = _cache_key(model, messages, **kwargs)
    await _client().delete(key)
