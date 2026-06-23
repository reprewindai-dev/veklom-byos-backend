"""VNP Scoring Engine and Cache Pipeline."""

import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.vnp import VNPMonitoredAPI, VNPProbeMetric
from backend.core.services.redis_cache import redis_cache


async def update_api_composite_score(session: AsyncSession, api_id: str) -> float:
    """Calculate the moving average composite score and update the API."""
    # Look back over the last 5 minutes (or adjust as needed)
    lookback = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    # Calculate avg latency and success rate
    stmt = (
        select(
            func.avg(VNPProbeMetric.latency_ms).label("avg_latency"),
            func.avg(func.cast(VNPProbeMetric.success, func.integer())).label("success_rate")
        )
        .where(
            and_(
                VNPProbeMetric.api_id == api_id,
                VNPProbeMetric.created_at >= lookback
            )
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    
    if not row or row.avg_latency is None or row.success_rate is None:
        return 100.0  # Default perfect score if no metrics
    
    avg_latency = float(row.avg_latency)
    success_rate = float(row.success_rate)
    
    # Calculate composite score (100.0 is perfect)
    # E.g., success_rate * 100 - (latency penalties)
    # For now, simple formula: success_rate * 100 - (latency / 100)
    score = (success_rate * 100) - (avg_latency / 100.0)
    score = max(0.0, min(100.0, score))  # Clamp between 0 and 100
    
    # Update DB
    api = await session.get(VNPMonitoredAPI, api_id)
    if api:
        api.current_composite_score = score
        api.stability_rating = "Stable" if score > 90 else "Degraded" if score > 50 else "Unstable"
        await session.commit()
        
        # Push to Redis Cache for <15ms beacon reads
        cache_key = f"vnp:api:score:{api_id}"
        cache_data = {
            "score": score,
            "rating": api.stability_rating,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await redis_cache.set(cache_key, json.dumps(cache_data), ttl=300)
        
    return score


async def get_cached_api_score(api_id: str) -> dict:
    """Get the latest cached score for an API, falling back to default."""
    cache_key = f"vnp:api:score:{api_id}"
    cached = await redis_cache.get(cache_key)
    if cached:
        return json.loads(cached)
    return {"score": 100.0, "rating": "Unknown", "updated_at": None}
