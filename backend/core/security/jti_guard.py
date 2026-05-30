import logging
import os
import time
from typing import Optional
import redis.asyncio as redis
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class JtiStore:
    """Shared Redis JTI storage with automated in-memory LRU fallback."""
    
    def __init__(self, max_inmem: int = 100_000):
        self.max_inmem = max_inmem
        self._local = {}
        self.redis: Optional[redis.Redis] = None
        self.is_fallback = False
        
        # Configure Redis connection
        redis_url = os.getenv("REDIS_URL", settings.REDIS_URL)
        redis_enabled = os.getenv("REDIS_ENABLED", "True").lower() == "true"
        
        if redis_enabled and redis_url:
            try:
                self.redis = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=2.0,
                    socket_connect_timeout=2.0,
                    retry_on_timeout=True
                )
                logger.info("JtiStore Redis connection initialized.")
            except Exception as e:
                logger.warning(f"Could not connect JtiStore to Redis at {redis_url}, using in-memory: {e}")
                self.is_fallback = True
        else:
            self.is_fallback = True

    def _now(self) -> int:
        return int(time.time())

    async def set_if_absent(self, key: str, ttl: int) -> bool:
        """
        Atomic check-and-set.
        Returns True if key was set (meaning it did not exist), False if already present.
        """
        if ttl <= 0:
            ttl = 1
            
        # 1. Primary path: Redis NX (Not Exists) set
        if not self.is_fallback and self.redis:
            try:
                # SET key "1" NX EX ttl returns True if inserted, None/False if exists
                res = await self.redis.set(name=key, value="1", nx=True, ex=ttl)
                return bool(res)
            except Exception as e:
                logger.warning(f"JtiStore Redis set failed, degrading to local storage: {e}")
                logger.error("SECURITY_DEGRADED: Active JTI protection falling back to local memory.")
                self.is_fallback = True
                
        # 2. Fallback path: In-memory LRU cache
        now = self._now()
        
        # Bounded cleanup if memory exceeds limits
        if len(self._local) > self.max_inmem:
            # Lazy cleanup of expired items first
            expired_keys = [k for k, exp in self._local.items() if exp <= now]
            for k in expired_keys:
                del self._local[k]
                
            # If still over bounds, eject oldest 1%
            if len(self._local) > self.max_inmem:
                keys_to_drop = list(self._local.keys())[:max(1, self.max_inmem // 100)]
                for k in keys_to_drop:
                    del self._local[k]
                    
        # Check presence and expiration
        if key in self._local:
            if self._local[key] > now:
                return False  # Replay detected
                
        # Register new JTI
        self._local[key] = now + ttl
        return True


def compute_ttl(iat: int, exp: int, max_cap: int = 3600, skew: int = 60) -> int:
    """Compute TTL based on expiry claims, incorporating clock skew padding."""
    now = int(time.time())
    start = max(iat - skew, now - max_cap)
    ttl = min(exp + skew, now + max_cap) - now
    return max(1, min(ttl, max_cap))


def build_replay_key(iss: str, jti: str, aud: Optional[str]) -> str:
    """Constructs unique cache key partition."""
    a = aud or "-"
    return f"jti:{iss}:{a}:{jti}"


class JtiGuard:
    """JWT replay defense manager enforcing unique JTI and Audience claims."""
    
    def __init__(self, store: JtiStore, enforce_aud: bool = True, skew: int = 60):
        self.store = store
        self.enforce_aud = enforce_aud
        self.skew = skew

    async def check_and_commit(self, iss: str, jti: str, aud: Optional[str], iat: int, exp: int) -> None:
        """
        Verify claims integrity and attempt JTI registration.
        Raises ValueError on malformed payloads, PermissionError on replays.
        """
        if not jti:
            raise ValueError("JWT missing jti (required for replay protection)")
        if self.enforce_aud and not aud:
            raise ValueError("JWT missing aud and policy requires it")
            
        key = build_replay_key(iss, jti, aud)
        ttl = compute_ttl(iat, exp, skew=self.skew)

        
        is_fresh = await self.store.set_if_absent(key, ttl)
        if not is_fresh:
            logger.warning(f"Replay attack blocked: key={key}")
            raise PermissionError("Replay detected: token already consumed")
