import logging
import redis.asyncio as redis
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class InMemoryRedis:
    def __init__(self):
        self._db = {}
        logger.info("Initializing in-memory fallback database for local development.")
        
    async def get(self, key: str):
        return self._db.get(key)
        
    async def set(self, key: str, value: str, ex: int = None):
        self._db[key] = value
        return True
        
    async def delete(self, key: str):
        if key in self._db:
            del self._db[key]
            return 1
        return 0
        
    async def ping(self):
        return True

    async def eval(self, script: str, numkeys: int, key: str, capacity: int, refill_rate: float, now: float):
        # Fallback Python implementation of the token bucket rate limiter lua script
        bucket = self._db.get(key)
        if bucket is None:
            tokens = float(capacity)
            last_update = float(now)
        else:
            tokens = float(bucket.get("tokens", capacity))
            last_update = float(bucket.get("last_update", now))
            
        delta_time = max(0.0, float(now) - last_update)
        refilled_tokens = int(delta_time * float(refill_rate))
        tokens = min(float(capacity), tokens + refilled_tokens)
        
        requested = 1
        if tokens >= requested:
            tokens = tokens - requested
            self._db[key] = {"tokens": tokens, "last_update": now}
            return [1, int(tokens)]
        else:
            return [0, int(tokens)]

class SafeRedisClient:
    def __init__(self, redis_url: str):
        self.url = redis_url
        self.real_redis = None
        self.fallback_db = InMemoryRedis()
        self.is_fallback = False
        self._init_real_redis()

    def _init_real_redis(self):
        try:
            self.real_redis = redis.from_url(
                self.url,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                retry_on_timeout=True
            )
        except Exception as e:
            logger.warning(f"Could not connect to Redis at {self.url}, using in-memory database: {e}")
            self.real_redis = None
            self.is_fallback = True

    async def get(self, key: str):
        if self.is_fallback or not self.real_redis:
            return await self.fallback_db.get(key)
        try:
            return await self.real_redis.get(key)
        except Exception as e:
            logger.warning(f"Redis get failed, falling back to in-memory: {e}")
            self.is_fallback = True
            return await self.fallback_db.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        await self.fallback_db.set(key, value, ex)
        if self.is_fallback or not self.real_redis:
            return True
        try:
            return await self.real_redis.set(key, value, ex=ex)
        except Exception as e:
            logger.warning(f"Redis set failed, falling back to in-memory: {e}")
            self.is_fallback = True
            return True

    async def delete(self, key: str):
        await self.fallback_db.delete(key)
        if self.is_fallback or not self.real_redis:
            return 1
        try:
            return await self.real_redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed, falling back to in-memory: {e}")
            self.is_fallback = True
            return 1

    async def eval(self, script: str, numkeys: int, *args):
        if self.is_fallback or not self.real_redis:
            return await self.fallback_db.eval(script, numkeys, *args)
        try:
            return await self.real_redis.eval(script, numkeys, *args)
        except Exception as e:
            logger.warning(f"Redis eval failed, falling back to in-memory: {e}")
            self.is_fallback = True
            return await self.fallback_db.eval(script, numkeys, *args)

    async def ping(self):
        if self.is_fallback or not self.real_redis:
            return True
        try:
            return await self.real_redis.ping()
        except Exception as e:
            self.is_fallback = True
            return True

# Initialize the Safe client
redis_client = SafeRedisClient(settings.REDIS_URL)

async def get_redis():
    """Dependency injection for Redis client."""
    return redis_client
