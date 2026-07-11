"""
Route Beacon Service - High-performance Redis-based route resolution hot-cache.
Ensures <15ms route resolution for VNP workloads.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.services.redis_cache import redis_cache
from backend.db.models.vnp import (
    Api, ApiRegion, RoutePolicy, RegionalTelemetry, ApiStatus
)
from backend.core.services.vnp_scoring import get_cached_api_score

logger = logging.getLogger(__name__)

class RouteBeaconService:
    BEACON_TTL = 300  # 5 minutes
    BEACON_PREFIX = "vnp:beacon"

    @classmethod
    async def get_best_route(
        cls,
        db: AsyncSession,
        customer_id: str,
        project_id: str,
        policy_id: str,
        requested_region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Resolves the best route by first checking the Redis hot-cache.
        Falls back to DB if cache is cold.
        """
        cache_key = f"{cls.BEACON_PREFIX}:policy:{policy_id}:region:{requested_region}"

        # 1. Try Cache
        cached_snapshot = await redis_cache.get(cache_key)
        if cached_snapshot:
            logger.debug(f"Route beacon cache hit for policy {policy_id}")
            return json.loads(cached_snapshot)

        # 2. Cache Miss - Compute and Cache
        logger.info(f"Route beacon cache miss for policy {policy_id}. Resolving from DB...")

        # Fetch Policy
        policy_stmt = select(RoutePolicy).where(RoutePolicy.id == policy_id)
        policy_res = await db.execute(policy_stmt)
        policy = policy_res.scalar_one_or_none()
        if not policy:
            return {"error": "Policy not found"}

        # Fetch active APIs (In a real high-scale system, this list would also be cached)
        api_stmt = select(Api).where(Api.status == ApiStatus.active)
        apis_res = await db.execute(api_stmt)
        apis = apis_res.scalars().all()

        candidates = []
        for api in apis:
            # Policy filters
            if policy.allowed_provider_ids and str(api.provider_id) not in policy.allowed_provider_ids:
                continue

            # Get latest telemetry
            tel_stmt = (
                select(RegionalTelemetry)
                .where(RegionalTelemetry.api_id == api.id)
                .order_by(RegionalTelemetry.measured_at.desc())
                .limit(1)
            )
            tel_res = await db.execute(tel_stmt)
            telemetry = tel_res.scalar_one_or_none()
            if not telemetry:
                continue

            # Policy constraints
            if policy.max_p99_latency_ms and telemetry.p99_latency_ms > policy.max_p99_latency_ms:
                continue
            if policy.minimum_trust_score and telemetry.trust_score < policy.minimum_trust_score:
                continue

            # Get composite score from vnp_scoring cache if available
            score_data = await get_cached_api_score(str(api.id))

            candidates.append({
                "api_id": str(api.id),
                "provider_id": str(api.provider_id),
                "provider_region": telemetry.region_code,
                "endpoint_url": api.base_url,
                "composite_score": score_data.get("score", 0.0),
                "trust_grade": "AAA" if telemetry.trust_score > 90 else "A",
                "estimated_p99_latency_ms": telemetry.p99_latency_ms,
                "uptime_percent_rolling": float(telemetry.uptime_percent),
                "decision_reasons": ["policy_match", "healthy"]
            })

        # Sort and Rank
        candidates.sort(key=lambda x: x["composite_score"], reverse=True)
        top_candidates = candidates[:5]
        for i, c in enumerate(top_candidates):
            c["rank"] = i + 1

        snapshot = {
            "route_snapshot_id": str(uuid.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": cls.BEACON_TTL,
            "candidates": top_candidates
        }

        # 3. Save to Cache
        await redis_cache.set(cache_key, json.dumps(snapshot), ttl=cls.BEACON_TTL)

        return snapshot

    @classmethod
    async def update_beacon_cache(cls, policy_id: str, requested_region: str, snapshot: Dict[str, Any]):
        """Manually update or invalidate a beacon."""
        cache_key = f"{cls.BEACON_PREFIX}:policy:{policy_id}:region:{requested_region}"
        await redis_cache.set(cache_key, json.dumps(snapshot), ttl=cls.BEACON_TTL)
