"""Bounded dependency health probes for BYOS."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from urllib.parse import urlparse

import httpx
import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy import text

from backend.core.config.settings import settings
from backend.core.database.database import engine

router = APIRouter(tags=["Health"])
_PROBE_TIMEOUT_SECONDS = 2.0
_STATE_RANK = {"healthy": 0, "degraded": 1, "unconfigured": 1, "unavailable": 2}


def _host(url: str) -> str:
    return urlparse(url).hostname or "unknown"


def _result(name: str, host: str, state: str, started: float) -> dict[str, Any]:
    return {
        "name": name,
        "host": host,
        "state": state,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }


async def _probe_http(name: str, base_url: str) -> dict[str, Any]:
    started = time.perf_counter()
    base = base_url.rstrip("/")
    try:
        timeout = httpx.Timeout(_PROBE_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await asyncio.wait_for(
                client.get(f"{base}/health"),
                timeout=_PROBE_TIMEOUT_SECONDS,
            )
            if response.status_code == 404:
                response = await asyncio.wait_for(
                    client.get(f"{base}/protocol.json"),
                    timeout=_PROBE_TIMEOUT_SECONDS,
                )
        state = "healthy" if 200 <= response.status_code < 300 else "degraded"
    except Exception:  # noqa: BLE001 - dependency probes must never raise
        state = "unavailable"
    return _result(name, _host(base_url), state, started)


async def _probe_database() -> dict[str, Any]:
    started = time.perf_counter()

    async def check() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(check(), timeout=_PROBE_TIMEOUT_SECONDS)
        state = "healthy"
    except Exception:  # noqa: BLE001 - dependency probes must never raise
        state = "unavailable"
    return _result("database", "configured", state, started)


async def _probe_redis() -> dict[str, Any]:
    started = time.perf_counter()
    client = None
    try:
        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=_PROBE_TIMEOUT_SECONDS,
            socket_timeout=_PROBE_TIMEOUT_SECONDS,
        )
        await asyncio.wait_for(client.ping(), timeout=_PROBE_TIMEOUT_SECONDS)
        state = "healthy"
    except Exception:  # noqa: BLE001 - dependency probes must never raise
        state = "unavailable"
    finally:
        if client is not None:
            await client.aclose()
    return _result("redis", _host(settings.REDIS_URL), state, started)


def _unconfigured(name: str) -> dict[str, Any]:
    return {"name": name, "host": "unconfigured", "state": "unconfigured", "latency_ms": 0.0}


@router.get("/health/dependencies")
async def dependency_health() -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        await _probe_database(),
        await _probe_redis(),
    ]

    ollama_url = getattr(settings, "OLLAMA_BASE_URL", None)
    if ollama_url:
        checks.append(await _probe_http("ollama", ollama_url))
    else:
        checks.append(_unconfigured("ollama"))

    configured_http_dependencies = [
        ("capi", getattr(settings, "CAPI_BACKEND_URL", "") or os.getenv("CAPI_BACKEND_URL")),
        ("cappo", getattr(settings, "CAPPO_BACKEND_URL", "") or os.getenv("CAPPO_BACKEND_URL")),
        (
            "pgl",
            getattr(settings, "PGL_LEDGER_URL", "")
            or os.getenv("PGL_LEDGER_URL")
            or getattr(settings, "GNOMLEDGER_URL", "")
        ),
        ("lockerphycer", getattr(settings, "LOCKERPHYCER_URL", "") or os.getenv("LOCKERPHYCER_URL")),
    ]
    for name, url in configured_http_dependencies:
        checks.append(await _probe_http(name, url) if url else _unconfigured(name))

    overall = max(checks, key=lambda check: _STATE_RANK[check["state"]])["state"]
    return {"status": overall, "dependencies": checks}
