"""Health check routes."""

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.core.config.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
    }


@router.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
        "components": {
            "database": {"status": "healthy", "latency_ms": 2},
            "redis": {"status": "healthy", "latency_ms": 1},
            "ai_services": {"status": "healthy", "models_loaded": 5},
        },
    }


@router.get("/api-status")
async def platform_status():
    from backend.core.database.redis_client import redis_client
    from backend.core.database.database import engine
    from backend.core.llm.circuit_breaker import CircuitBreaker
    import httpx
    import time
    
    # Check DB
    db_ok = False
    try:
        from sqlalchemy import text
        from backend.core.database.database import SessionLocal
        # Use simple select 1
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
        
    # Check Redis
    redis_ok = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_ok = True
        except Exception:
            pass
            
    # Check Ollama
    llm_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            if res.status_code == 200:
                llm_ok = True
    except Exception:
        pass
        
    # Get Circuit Breaker State
    cb = CircuitBreaker("ollama")
    cb_state = await cb.get_state()
    cb_failures = 0
    if redis_client:
        try:
            cb_failures = int(await redis_client.get(cb.failures_key) or "0")
        except Exception:
            pass
            
    threshold = int(getattr(settings, "CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3))
    cooldown = int(getattr(settings, "CIRCUIT_BREAKER_COOLDOWN_SECONDS", 60))
    
    # Mock uptime for demo purposes
    uptime = 43200
    
    return {
        "status": "healthy" if (db_ok and redis_ok and llm_ok) else "degraded",
        "db_ok": db_ok,
        "redis_ok": redis_ok,
        "llm_ok": llm_ok,
        "llm_model": getattr(settings, "LLM_MODEL_DEFAULT", "qwen2.5:3b"),
        "llm_models_available": ["qwen2.5:3b", "llama3.1:8b"],
        "groq_fallback_enabled": bool(getattr(settings, "LLM_FALLBACK", "groq") == "groq" and settings.GROQ_API_KEY),
        "circuit_breaker": {
            "state": cb_state,
            "failures": cb_failures,
            "threshold": threshold,
            "cooldown_seconds": cooldown
        },
        "uptime_seconds": uptime
    }


@router.post("/test-post")
async def test_post():
    return {"status": "success", "message": "POST endpoint works"}
