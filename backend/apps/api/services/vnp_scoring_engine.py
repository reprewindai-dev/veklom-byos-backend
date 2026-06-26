"""
VNP Scoring Engine - Background task to compute route snapshots.
Aligned with VNP Production Architecture Phase 3.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import async_session
from backend.core.services.redis_cache import redis_cache
from backend.db.models.vnp import (
    Api, ApiRegion, RegionalTelemetry, RouteSnapshot, ApiStatus
)

logger = logging.getLogger(__name__)

class VNPScoringEngine:
    SCORING_INTERVAL = 60  # seconds
    REDIS_BEACON_PREFIX = "vnp:beacon"

    @classmethod
    async def start(cls):
        """Starts the scoring engine background loop."""
        logger.info("Starting VNP Scoring Engine...")
        asyncio.create_task(cls.run_loop())

    @classmethod
    async def run_loop(cls):
        while True:
            try:
                await cls.compute_and_cache_snapshots()
            except Exception as e:
                logger.error(f"Error in VNP Scoring Engine loop: {e}", exc_info=True)
            await asyncio.sleep(cls.SCORING_INTERVAL)

    @classmethod
    async def compute_and_cache_snapshots(cls):
        """
        Reads from regional_telemetry, computes weighted scores,
        and updates both Redis and DB.
        """
        async with async_session() as db:
            # 1. Fetch active APIs and their latest telemetry
            # We look at telemetry from the last 1 hour
            lookback = datetime.now(timezone.utc) - timedelta(hours=1)

            # Subquery to get latest telemetry per api_id and region_code
            latest_tel_stmt = (
                select(
                    RegionalTelemetry.api_id,
                    RegionalTelemetry.region_code,
                    func.max(RegionalTelemetry.measured_at).label("max_measured_at")
                )
                .where(RegionalTelemetry.measured_at >= lookback)
                .group_by(RegionalTelemetry.api_id, RegionalTelemetry.region_code)
                .subquery()
            )

            stmt = (
                select(Api, ApiRegion, RegionalTelemetry)
                .join(ApiRegion, Api.id == ApiRegion.api_id)
                .join(
                    RegionalTelemetry,
                    (Api.id == RegionalTelemetry.api_id) &
                    (ApiRegion.region_code == RegionalTelemetry.region_code)
                )
                .join(
                    latest_tel_stmt,
                    (RegionalTelemetry.api_id == latest_tel_stmt.c.api_id) &
                    (RegionalTelemetry.region_code == latest_tel_stmt.c.region_code) &
                    (RegionalTelemetry.measured_at == latest_tel_stmt.c.max_measured_at)
                )
                .where(Api.status == ApiStatus.active)
                .where(ApiRegion.active == True)
            )

            result = await db.execute(stmt)
            rows = result.all()

            if not rows:
                logger.debug("No active API telemetry found for snapshot computation.")
                return

            # 2. Group by region for multi-region beaconing
            regional_candidates = {}
            for api, region, telemetry in rows:
                reg_code = region.region_code
                if reg_code not in regional_candidates:
                    regional_candidates[reg_code] = []

                # Weighted scoring: p99 latency x uptime x x402 compliance x region diversity
                # Higher score is better.
                # Basic formula: Score = (1000 / p99) * (uptime/100) * (1.2 if x402 else 1.0)
                p99 = max(float(telemetry.p99_latency_ms), 1.0)
                uptime = float(telemetry.uptime_percent) / 100.0
                x402_multiplier = 1.2 if api.x402_ready else 1.0

                composite_score = (1000.0 / p99) * uptime * x402_multiplier

                regional_candidates[reg_code].append({
                    "api_id": str(api.id),
                    "provider_id": str(api.provider_id),
                    "region": reg_code,
                    "endpoint_url": region.endpoint_url,
                    "composite_score": round(composite_score, 4),
                    "p99_latency_ms": telemetry.p99_latency_ms,
                    "uptime_percent": telemetry.uptime_percent,
                    "trust_score": float(telemetry.trust_score),
                    "x402_ready": api.x402_ready
                })

            # 3. Create snapshots and update Redis
            for reg_code, candidates in regional_candidates.items():
                # Sort by score
                candidates.sort(key=lambda x: x["composite_score"], reverse=True)

                snapshot_id = str(uuid.uuid4())
                generated_at = datetime.now(timezone.utc)

                # Create snapshot record
                # We store a "global" policy snapshot if requested, or per-region
                snapshot_data = {
                    "snapshot_id": snapshot_id,
                    "region": reg_code,
                    "generated_at": generated_at.isoformat(),
                    "candidates": candidates[:5] # Top 5
                }

                # Update Redis Hot-Cache
                cache_key = f"{cls.REDIS_BEACON_PREFIX}:region:{reg_code}"
                await redis_cache.set(cache_key, json.dumps(snapshot_data), ttl=300)

                # Also a "default" catch-all if needed
                if reg_code == "us-east-1": # Primary region
                    await redis_cache.set(f"{cls.REDIS_BEACON_PREFIX}:default", json.dumps(snapshot_data), ttl=300)

                # Persist to DB
                new_snapshot = RouteSnapshot(
                    id=snapshot_id,
                    requested_region=reg_code,
                    generated_at=generated_at,
                    ttl_seconds=300,
                    snapshot=snapshot_data
                )
                db.add(new_snapshot)

            await db.commit()
            logger.info(f"VNP Scoring Engine: Updated snapshots for {len(regional_candidates)} regions.")

    @classmethod
    async def get_latest_beacon(cls, region: str = "default") -> Optional[Dict[str, Any]]:
        """Fast lookup for beacon service."""
        cache_key = f"{cls.REDIS_BEACON_PREFIX}:{region}"
        if region != "default":
             cache_key = f"{cls.REDIS_BEACON_PREFIX}:region:{region}"

        cached = await redis_cache.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
