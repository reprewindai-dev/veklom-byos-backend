"""
Veklom AI Response Cache — hot/warm Redis cache + 24h persistent conversation memory.

Architecture:
  Hot cache  → exact SHA-256 match of (model, messages, temp)  TTL = 5 min
  Warm cache → provider-level keyed response                    TTL = 1 hour
  Memory     → per-workspace per-session conversation history   TTL = 24 hours
                max 20 messages (enforced on every write)

All operations degrade gracefully if Redis is unavailable.
"""

from __future__ import annotations

import json
import hashlib
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

MEMORY_MAX_MESSAGES: int = 20
MEMORY_TTL_SECONDS: int = 86_400      # 24 hours
HOT_CACHE_TTL: int = 300              # 5 minutes — exact response hit
WARM_CACHE_TTL: int = 3_600           # 1 hour — provider-level


# ---------------------------------------------------------------------------
# Cache key helpers
# ---------------------------------------------------------------------------

def _request_hash(model: str, messages: list, temperature: float = 0.7) -> str:
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": round(temperature, 2)},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def hot_key(model: str, messages: list, temperature: float = 0.7) -> str:
    return f"veklom:ai:hot:{_request_hash(model, messages, temperature)}"


def warm_key(model: str, messages: list) -> str:
    h = _request_hash(model, messages, 0.0)   # temperature-agnostic
    return f"veklom:ai:warm:{h}"


def memory_key(workspace_id: str, session_id: str) -> str:
    return f"veklom:memory:{workspace_id}:{session_id}"


# ---------------------------------------------------------------------------
# Redis helpers (always safe to call — returns None on failure)
# ---------------------------------------------------------------------------

async def _redis():
    try:
        from backend.core.database.redis_client import redis_client
        return redis_client
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Hot cache — exact response match
# ---------------------------------------------------------------------------

async def get_hot(model: str, messages: list, temperature: float = 0.7) -> Optional[dict]:
    """Return cached response dict if exact match found (≤5 min old)."""
    r = await _redis()
    if not r:
        return None
    try:
        key = hot_key(model, messages, temperature)
        raw = await r.get(key)
        if raw:
            logger.debug(f"[cache:hot] HIT {key[-12:]}")
            return json.loads(raw)
    except Exception as exc:
        logger.debug(f"[cache:hot] get error: {exc}")
    return None


async def set_hot(model: str, messages: list, response: dict, temperature: float = 0.7) -> None:
    """Store response in hot cache. Silently skips on Redis failure."""
    r = await _redis()
    if not r:
        return
    try:
        key = hot_key(model, messages, temperature)
        await r.setex(key, HOT_CACHE_TTL, json.dumps(response, ensure_ascii=False))
        logger.debug(f"[cache:hot] SET {key[-12:]} ttl={HOT_CACHE_TTL}s")
    except Exception as exc:
        logger.debug(f"[cache:hot] set error: {exc}")


# ---------------------------------------------------------------------------
# Warm cache — provider-level, temperature-agnostic
# ---------------------------------------------------------------------------

async def get_warm(model: str, messages: list) -> Optional[dict]:
    """Return warm-cached response (1h TTL, temperature-agnostic match)."""
    r = await _redis()
    if not r:
        return None
    try:
        key = warm_key(model, messages)
        raw = await r.get(key)
        if raw:
            logger.debug(f"[cache:warm] HIT {key[-12:]}")
            return json.loads(raw)
    except Exception as exc:
        logger.debug(f"[cache:warm] get error: {exc}")
    return None


async def set_warm(model: str, messages: list, response: dict) -> None:
    r = await _redis()
    if not r:
        return
    try:
        key = warm_key(model, messages)
        await r.setex(key, WARM_CACHE_TTL, json.dumps(response, ensure_ascii=False))
        logger.debug(f"[cache:warm] SET {key[-12:]} ttl={WARM_CACHE_TTL}s")
    except Exception as exc:
        logger.debug(f"[cache:warm] set error: {exc}")


# ---------------------------------------------------------------------------
# Conversation memory — persistent 20-message 24h window per session
# ---------------------------------------------------------------------------

async def get_memory(workspace_id: str, session_id: str) -> List[dict]:
    """Load last ≤20 messages for this session. Returns [] on miss."""
    r = await _redis()
    if not r:
        return []
    try:
        key = memory_key(workspace_id, session_id)
        raw = await r.get(key)
        if raw:
            msgs = json.loads(raw)
            return msgs[-MEMORY_MAX_MESSAGES:]
    except Exception as exc:
        logger.debug(f"[cache:memory] get error: {exc}")
    return []


async def push_memory(workspace_id: str, session_id: str, new_messages: List[dict]) -> List[dict]:
    """
    Append new_messages to existing history, enforce 20-message limit,
    refresh TTL to 24h, and return the full updated window.
    """
    existing = await get_memory(workspace_id, session_id)
    combined = existing + new_messages
    truncated = combined[-MEMORY_MAX_MESSAGES:]

    r = await _redis()
    if r:
        try:
            key = memory_key(workspace_id, session_id)
            await r.setex(key, MEMORY_TTL_SECONDS, json.dumps(truncated, ensure_ascii=False))
        except Exception as exc:
            logger.debug(f"[cache:memory] push error: {exc}")

    return truncated


async def clear_memory(workspace_id: str, session_id: str) -> None:
    r = await _redis()
    if not r:
        return
    try:
        await r.delete(memory_key(workspace_id, session_id))
    except Exception:
        pass


async def get_memory_stats(workspace_id: str, session_id: str) -> dict:
    """Return metadata about the current conversation window."""
    msgs = await get_memory(workspace_id, session_id)
    return {
        "session_id": session_id,
        "message_count": len(msgs),
        "max_messages": MEMORY_MAX_MESSAGES,
        "ttl_hours": MEMORY_TTL_SECONDS // 3600,
        "cache_backend": "redis",
    }
