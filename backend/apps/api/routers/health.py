"""Health check routes."""

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from backend.core.config.settings import settings
from backend.core.database.redis_client import redis_client
from backend.core.llm.circuit_breaker import CircuitBreaker

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)
_PROCESS_START_MONOTONIC = time.monotonic()
_DEPENDENCY_TIMEOUT_SECONDS = 2.0


async def _check_database() -> tuple[bool, float | None]:
    started = time.perf_counter()
    try:
        from backend.core.database.database import engine

        async def query() -> None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(query(), timeout=_DEPENDENCY_TIMEOUT_SECONDS)
        return True, round((time.perf_counter() - started) * 1000, 1)
    except Exception as exc:
        logger.warning("Database health check failed: %s", type(exc).__name__)
        return False, None


async def _check_redis() -> tuple[bool, float | None]:
    started = time.perf_counter()
    client = None
    try:
        import redis.asyncio as redis

        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=_DEPENDENCY_TIMEOUT_SECONDS,
            socket_timeout=_DEPENDENCY_TIMEOUT_SECONDS,
        )
        await asyncio.wait_for(client.ping(), timeout=_DEPENDENCY_TIMEOUT_SECONDS)
        return True, round((time.perf_counter() - started) * 1000, 1)
    except Exception as exc:
        logger.warning("Redis health check failed: %s", type(exc).__name__)
        return False, None
    finally:
        if client is not None:
            await client.aclose()


async def _check_llm() -> tuple[bool, float | None, list[str] | None]:
    base_url = (getattr(settings, "OLLAMA_BASE_URL", None) or "").strip()
    if not base_url:
        return False, None, None

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=_DEPENDENCY_TIMEOUT_SECONDS) as client:
            response = await asyncio.wait_for(
                client.get(f"{base_url.rstrip('/')}/api/tags"),
                timeout=_DEPENDENCY_TIMEOUT_SECONDS,
            )
        response.raise_for_status()
        models = response.json().get("models", [])
        names = [model.get("name") for model in models if model.get("name")]
        return True, round((time.perf_counter() - started) * 1000, 1), names
    except Exception as exc:
        logger.warning("LLM health check failed: %s", type(exc).__name__)
        return False, None, None


def _uptime_seconds() -> int:
    return max(0, int(time.monotonic() - _PROCESS_START_MONOTONIC))


@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Shallow liveness check; does not assert dependency or runtime verification."""
    return {
        "status": "alive",
        "verification_scope": "PROCESS_ONLY",
        "dependencies": "NOT_VERIFIED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
    }


@router.api_route("/_ping", methods=["GET", "HEAD"])
async def ping_check():
    """Alias for shallow health check."""
    return await health_check()


@router.api_route("/ready", methods=["GET", "HEAD"])
async def ready_check():
    """Traffic readiness check hitting core dependencies like DB and Redis."""
    db_ok, _ = await _check_database()
    redis_ok, _ = await _check_redis()
    if db_ok and redis_ok:
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.VERSION,
            "service": settings.APP_NAME,
        }
    from fastapi import HTTPException

    raise HTTPException(status_code=503, detail="Service Unavailable: core dependencies unreachable")


@router.api_route("/api/v1/health", methods=["GET", "HEAD"])
async def health_check_v1():
    """Alias for /health — keeps API consistency for clients that call /api/v1/health."""
    return await health_check()


@router.api_route("/api/health", methods=["GET", "HEAD"])
async def health_check_api():
    """Alias for /health — explicitly requested by observability script."""
    return await health_check()


@router.api_route("/api/v1/sys/health", methods=["GET", "HEAD"])
async def health_check_sys():
    """Alias for /health — explicitly requested by frontend observability components."""
    return await health_check()


@router.get("/health/dependencies")
async def dependencies_health():
    db_ok, db_latency = await _check_database()
    redis_ok, redis_latency = await _check_redis()
    llm_ok, llm_latency, llm_models = await _check_llm()
    return {
        "status": "healthy" if db_ok and redis_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
        "components": {
            "database": {
                "status": "healthy" if db_ok else "unhealthy",
                "latency_ms": db_latency,
            },
            "redis": {
                "status": "healthy" if redis_ok else "unhealthy",
                "latency_ms": redis_latency,
            },
            "ai_services": {
                "status": "healthy" if llm_ok else "unknown",
                "latency_ms": llm_latency,
                "models_loaded": len(llm_models) if llm_models is not None else None,
            },
        },
        "uptime_seconds": _uptime_seconds(),
    }


@router.get("/api-status")
async def platform_status():
    db_ok, _ = await _check_database()
    redis_ok, _ = await _check_redis()
    llm_ok, _, llm_models = await _check_llm()

    cb = CircuitBreaker("ollama")
    cb_state = await cb.get_state()
    cb_failures = 0
    try:
        cb_failures = int(await redis_client.get(cb.failures_key) or "0")
    except Exception:
        pass

    threshold = int(getattr(settings, "CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3))
    cooldown = int(getattr(settings, "CIRCUIT_BREAKER_COOLDOWN_SECONDS", 60))

    return {
        "status": "healthy" if (db_ok and redis_ok and llm_ok) else "degraded",
        "db_ok": db_ok,
        "redis_ok": redis_ok,
        "llm_ok": llm_ok,
        "llm_model": getattr(settings, "LLM_MODEL_DEFAULT", "qwen2.5:3b"),
        "llm_models_available": llm_models or [],
        "groq_fallback_enabled": bool(
            getattr(settings, "LLM_FALLBACK", "groq") == "groq" and settings.GROQ_API_KEY
        ),
        "circuit_breaker": {
            "state": cb_state,
            "failures": cb_failures,
            "threshold": threshold,
            "cooldown_seconds": cooldown,
        },
        "uptime_seconds": _uptime_seconds(),
    }


@router.post("/test-post")
async def test_post():
    return {"status": "success", "message": "POST endpoint works"}
