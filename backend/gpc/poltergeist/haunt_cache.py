"""
Haunt Cache Plane
Multi-tier caching for capability artifacts

Tiers:
- L0: Hot (process memory, agent RAM, fingerprint→ID)
- L1: Warm (Redis/Valkey, registry, locks, heartbeats)
- L2: Build cache (local NVMe, compiled wheels, source)
- L3: Inference (vLLM prefix cache, model weights)
- L4: Cold (Hetzner Object Storage, immutable archives)

Purpose:
- Fast path: L0 hit (sub-millisecond)
- Warm path: L1 hit (milliseconds)
- Build path: L2 hit or rebuild (seconds)
- Inference: L3 hit or download (milliseconds)
- Archive: L4 for immutable proof and recovery

Location: veklom-byos-backend/backend/gpc/poltergeist/haunt_cache.py
"""

import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

import redis.asyncio as redis  # Redis/Valkey async client


class CacheTier(str, Enum):
    """Cache tier identifiers"""
    L0_HOT = "l0_hot"           # Process memory
    L1_WARM = "l1_warm"         # Redis
    L2_BUILD = "l2_build"       # NVMe
    L3_INFERENCE = "l3_inference"  # vLLM
    L4_COLD = "l4_cold"         # Hetzner Object Storage


@dataclass
class CachedCapability:
    """A cached capability artifact"""
    capability_id: str
    artifact_hash: str
    artifact_bytes: bytes
    source_hash: str
    policy_hash: str
    pgl_agent_id: str
    pgl_certificate: str
    verified_at: datetime
    expires_at: Optional[datetime] = None
    tier: CacheTier = CacheTier.L2_BUILD
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        return {
            **asdict(self),
            "tier": self.tier.value,
            "verified_at": self.verified_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class HauntCachePlane:
    """
    Multi-tier cache for capability artifacts.
    
    Workflow:
    1. Try L0 (hot memory) — instant hit
    2. Try L1 (Redis) — fast hit
    3. Try L2 (NVMe) — local hit
    4. Try L3 (vLLM) — inference cache
    5. Fall back to L4 (S3) or rebuild
    
    Promotion:
    - L4 → L2 (download from S3 to NVMe)
    - L2 → L1 (register in Redis)
    - L1 → L0 (hot path, keep in memory)
    
    Eviction:
    - LFU (least-frequently-used) policy
    - Immediate: expired artifacts
    - Background: low-frequency artifacts
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_l0_items: int = 100,
        max_l2_mb: int = 10_000,
        l1_ttl_seconds: int = 3600,
    ):
        """
        Initialize cache plane.
        
        Args:
            redis_url: Redis/Valkey connection URL
            max_l0_items: Max items in L0 hot cache
            max_l2_mb: Max MB for L2 NVMe cache
            l1_ttl_seconds: TTL for L1 Redis entries
        """
        self.redis_url = redis_url
        self.max_l0_items = max_l0_items
        self.max_l2_mb = max_l2_mb
        self.l1_ttl_seconds = l1_ttl_seconds
        
        # L0: Hot memory cache
        self._l0_hot: Dict[str, CachedCapability] = {}
        self._l0_access_counts: Dict[str, int] = {}  # For LFU
        
        # L1: Redis connection (lazy)
        self._l1_redis: Optional[redis.Redis] = None
        
        # L2: Local NVMe (path-based)
        self._l2_path = "/var/cache/veklom/capabilities/"
        self._l2_size_bytes = 0
        
        # L3: vLLM prefix cache (external service)
        self._l3_vllm_url = "http://localhost:8000"
        
        # L4: Hetzner S3 (external service)
        self._l4_s3_bucket = "veklom-haunt-artifacts"
    
    async def get(self, capability_id: str) -> Optional[CachedCapability]:
        """
        Retrieve a capability from cache.
        
        Tries tiers in order: L0 → L1 → L2 → L3 → L4
        
        Args:
            capability_id: ID of capability to retrieve
            
        Returns:
            CachedCapability if found, None otherwise
        """
        # L0: Hot memory
        if capability_id in self._l0_hot:
            self._l0_access_counts[capability_id] += 1
            return self._l0_hot[capability_id]
        
        # L1: Redis
        l1_result = await self._get_l1(capability_id)
        if l1_result:
            # Promote to L0
            await self._promote_to_l0(l1_result)
            return l1_result
        
        # L2: NVMe
        l2_result = await self._get_l2(capability_id)
        if l2_result:
            # Promote to L1 and L0
            await self._promote_to_l1(l2_result)
            await self._promote_to_l0(l2_result)
            return l2_result
        
        # L3: vLLM (inference cache)
        l3_result = await self._get_l3(capability_id)
        if l3_result:
            await self._promote_to_l2(l3_result)
            await self._promote_to_l1(l3_result)
            await self._promote_to_l0(l3_result)
            return l3_result
        
        # L4: S3 (archive)
        l4_result = await self._get_l4(capability_id)
        if l4_result:
            await self._promote_to_l2(l4_result)
            await self._promote_to_l1(l4_result)
            await self._promote_to_l0(l4_result)
            return l4_result
        
        # Not found
        return None
    
    async def put(
        self,
        capability: CachedCapability,
        target_tier: CacheTier = CacheTier.L2_BUILD,
    ) -> None:
        """
        Store a capability in cache.
        
        Args:
            capability: Capability to cache
            target_tier: Where to store (will cascade upward)
        """
        # Store at target tier
        if target_tier == CacheTier.L2_BUILD:
            await self._put_l2(capability)
        elif target_tier == CacheTier.L1_WARM:
            await self._put_l1(capability)
        elif target_tier == CacheTier.L0_HOT:
            await self._put_l0(capability)
        elif target_tier == CacheTier.L4_COLD:
            await self._put_l4(capability)
        
        # Always cascade to archive (L4)
        await self._put_l4(capability)
    
    async def invalidate(self, capability_id: str) -> None:
        """
        Invalidate a capability across all tiers.
        
        Used when a capability is updated or policy changes.
        
        Args:
            capability_id: ID to invalidate
        """
        # Remove from L0
        if capability_id in self._l0_hot:
            del self._l0_hot[capability_id]
            if capability_id in self._l0_access_counts:
                del self._l0_access_counts[capability_id]
        
        # Remove from L1
        await self._invalidate_l1(capability_id)
        
        # L2 and above: mark as stale (don't delete for recovery)
        # Can be recovered from L4 if needed
    
    # ========================================================================
    # TIER-SPECIFIC OPERATIONS
    # ========================================================================
    
    async def _get_l1(self, capability_id: str) -> Optional[CachedCapability]:
        """Get from Redis"""
        if not self._l1_redis:
            return None
        
        try:
            data = await self._l1_redis.get(f"cap:{capability_id}")
            if data:
                return CachedCapability(**json.loads(data))
        except Exception as e:
            print(f"[Cache L1] Get error: {e}")
        
        return None
    
    async def _get_l2(self, capability_id: str) -> Optional[CachedCapability]:
        """Get from NVMe"""
        import aiofiles
        import os
        
        path = f"{self._l2_path}{capability_id}.bin"
        
        try:
            if os.path.exists(path):
                async with aiofiles.open(path, 'rb') as f:
                    data = await f.read()
                return CachedCapability(
                    capability_id=capability_id,
                    artifact_bytes=data,
                    artifact_hash=hashlib.sha256(data).hexdigest(),
                    source_hash="",  # Would be stored separately
                    policy_hash="",
                    pgl_agent_id="",
                    pgl_certificate="",
                    verified_at=datetime.utcnow(),
                )
        except Exception as e:
            print(f"[Cache L2] Get error: {e}")
        
        return None
    
    async def _get_l3(self, capability_id: str) -> Optional[CachedCapability]:
        """Get from vLLM prefix cache"""
        # vLLM stores model weights and prefix cached embeddings
        # Lookup by capability_id key
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._l3_vllm_url}/cache/get?key={capability_id}",
                    timeout=1.0
                )
                if response.status_code == 200:
                    return CachedCapability(**response.json())
        except Exception as e:
            print(f"[Cache L3] Get error: {e}")
        
        return None
    
    async def _get_l4(self, capability_id: str) -> Optional[CachedCapability]:
        """Get from Hetzner S3"""
        try:
            # Would use boto3 or similar to fetch from S3
            # For now, mock
            return None
        except Exception as e:
            print(f"[Cache L4] Get error: {e}")
        
        return None
    
    async def _put_l0(self, capability: CachedCapability) -> None:
        """Store in hot memory cache"""
        # Check capacity
        if len(self._l0_hot) >= self.max_l0_items:
            # Evict LFU item
            lfu_id = min(
                self._l0_access_counts.keys(),
                key=lambda k: self._l0_access_counts[k]
            )
            del self._l0_hot[lfu_id]
            del self._l0_access_counts[lfu_id]
        
        self._l0_hot[capability.capability_id] = capability
        self._l0_access_counts[capability.capability_id] = 1
    
    async def _put_l1(self, capability: CachedCapability) -> None:
        """Store in Redis"""
        if not self._l1_redis:
            await self._init_redis()
        
        try:
            data = json.dumps(capability.to_dict(), default=str)
            await self._l1_redis.setex(
                f"cap:{capability.capability_id}",
                self.l1_ttl_seconds,
                data
            )
        except Exception as e:
            print(f"[Cache L1] Put error: {e}")
    
    async def _put_l2(self, capability: CachedCapability) -> None:
        """Store on NVMe"""
        import aiofiles
        import os
        
        os.makedirs(self._l2_path, exist_ok=True)
        path = f"{self._l2_path}{capability.capability_id}.bin"
        
        try:
            async with aiofiles.open(path, 'wb') as f:
                await f.write(capability.artifact_bytes)
            self._l2_size_bytes += len(capability.artifact_bytes)
        except Exception as e:
            print(f"[Cache L2] Put error: {e}")
    
    async def _put_l4(self, capability: CachedCapability) -> None:
        """Store in S3"""
        try:
            # Would use boto3 to upload to S3
            # For now, mock
            pass
        except Exception as e:
            print(f"[Cache L4] Put error: {e}")
    
    async def _promote_to_l0(self, capability: CachedCapability) -> None:
        """Promote from lower tier to L0"""
        await self._put_l0(capability)
    
    async def _promote_to_l1(self, capability: CachedCapability) -> None:
        """Promote from lower tier to L1"""
        await self._put_l1(capability)
    
    async def _promote_to_l2(self, capability: CachedCapability) -> None:
        """Promote from lower tier to L2"""
        await self._put_l2(capability)
    
    async def _invalidate_l1(self, capability_id: str) -> None:
        """Remove from L1"""
        if not self._l1_redis:
            return
        
        try:
            await self._l1_redis.delete(f"cap:{capability_id}")
        except Exception as e:
            print(f"[Cache L1] Invalidate error: {e}")
    
    async def _init_redis(self) -> None:
        """Initialize Redis connection"""
        self._l1_redis = await redis.from_url(self.redis_url)


# ============================================================================
# CACHE STATISTICS
# ============================================================================

@dataclass
class CacheStats:
    """Cache performance statistics"""
    l0_size: int  # Number of items
    l0_hit_rate: float  # Percentage
    l1_size: int
    l1_hit_rate: float
    l2_size_mb: float
    l2_hit_rate: float
    total_lookups: int
    total_hits: int


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.gpc.poltergeist.haunt_cache import HauntCachePlane, CacheTier

cache = HauntCachePlane(
    redis_url="redis://localhost:6379",
    max_l0_items=100,
    max_l2_mb=10000,
)

# Store a capability after builder completes
capability = CachedCapability(
    capability_id="looker_connector_v1",
    artifact_hash=sha256_hash,
    artifact_bytes=compiled_wheel_bytes,
    source_hash=source_code_hash,
    policy_hash=policy_hash,
    pgl_agent_id="cap_looker_1",
    pgl_certificate="cert_looker_1_...",
    verified_at=datetime.utcnow(),
)

# Store at L2 (will cascade to L4)
await cache.put(capability, target_tier=CacheTier.L2_BUILD)

# Later, retrieve
capability = await cache.get("looker_connector_v1")
# Hits L1 (fast), or L2 (local), or L4 (reload)

# Invalidate when policy changes
await cache.invalidate("looker_connector_v1")
"""
