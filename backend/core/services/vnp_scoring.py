"""VNP Scoring Engine and Cache Pipeline."""

import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.vnp import Api, ProbeEvent
from backend.core.services.redis_cache import redis_cache

async def update_api_composite_score(session: AsyncSession, api_id: str) -> float:
    """Calculate the moving average composite score and update the API."""
    # Look back over the last 5 minutes (or adjust as needed)
    lookback = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    # Calculate avg latency and success rate
    stmt = (
        select(
            func.avg(ProbeEvent.latency_ms).label("avg_latency"),
            func.avg(cast(ProbeEvent.success, Integer)).label("success_rate")
        )
        .where(
            and_(
                ProbeEvent.api_id == api_id,
                ProbeEvent.measured_at >= lookback
            )
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    
    if not row or row.avg_latency is None or row.success_rate is None:
        return None  # No telemetry data available
    
    avg_latency = float(row.avg_latency)
    success_rate = float(row.success_rate)
    
    # Calculate composite score (100.0 is perfect)
    # E.g., success_rate * 100 - (latency penalties)
    # For now, simple formula: success_rate * 100 - (latency / 100)
    score = (success_rate * 100) - (avg_latency / 100.0)
    score = max(0.0, min(100.0, score))  # Clamp between 0 and 100
    
    # Update DB
    api = await session.get(Api, api_id)
    if api:
        # Note: We assume these columns exist or we add them if needed.
        # In the current Api model, stability_rating and current_composite_score are not defined.
        # We will use metadata or just update Redis for now if they are missing.
        if hasattr(api, 'current_composite_score'):
            api.current_composite_score = score
        if hasattr(api, 'stability_rating'):
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
    """Get the latest cached score for an API, falling back to None if no data."""
    cache_key = f"vnp:api:score:{api_id}"
    cached = await redis_cache.get(cache_key)
    if cached:
        return json.loads(cached)
    return {"score": None, "rating": "Unknown", "updated_at": None}


async def update_agent_governance_score(session: AsyncSession, agent_id: str) -> float:
    """Calculate real-time trust score based on path conformance, safety violations and dominance."""
    from backend.db.models.mission_lock import MissionLockAgentState
    
    stmt = select(MissionLockAgentState).where(MissionLockAgentState.agent_id == agent_id)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()
    
    if not state:
        return 100.0  # Perfect baseline for new/unmonitored agents
        
    conformance = float(state.path_conformance or 0.0)
    # If path_conformance is scaled 0.0 to 1.0, normalize it to 100%
    if conformance <= 1.0:
        conformance_percentage = conformance * 100.0
    else:
        conformance_percentage = conformance
        
    violations = int(state.safety_violations or 0)
    
    # Base trust starts at path conformance (100 points max)
    trust_score = conformance_percentage
    
    # Direct safety penalties: -15 points per violation
    trust_score -= (violations * 15.0)
    
    # Epsilon exploration penalty: minor penalty for too much random exploration if dominance is degraded
    dominance = float(state.current_dominance or 0.85)
    if dominance < 0.60:
        trust_score -= (1.0 - dominance) * 10.0
        
    # Clamp score between 0.0 and 100.0
    trust_score = max(0.0, min(100.0, trust_score))
    
    # Update cache
    cache_key = f"vnp:agent:governance:{agent_id}"
    cache_data = {
        "agent_id": agent_id,
        "trust_score": trust_score,
        "conformance": conformance_percentage,
        "violations": violations,
        "dominance": dominance,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await redis_cache.set(cache_key, json.dumps(cache_data), ttl=300)
    
    return trust_score

