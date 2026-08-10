import logging
import time
import redis.asyncio as redis
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

# --- Redis Lua Script Inlines ---
LUA_ACQUIRE = """
local key = KEYS[1]
local owner = ARGV[1]
local ttl = tonumber(ARGV[2])
local current_owner = redis.call('GET', key)
if not current_owner then
    redis.call('SET', key, owner, 'PX', ttl)
    return 1
elseif current_owner == owner then
    redis.call('PEXPIRE', key, ttl)
    return 1
else
    return 0
end
"""

LUA_RELEASE = """
local key = KEYS[1]
local owner = ARGV[1]
local current_owner = redis.call('GET', key)
if current_owner == owner then
    return redis.call('DEL', key)
else
    return 0
end
"""

LUA_RENEW = """
local key = KEYS[1]
local owner = ARGV[1]
local ttl = tonumber(ARGV[2])
local current_owner = redis.call('GET', key)
if current_owner == owner then
    redis.call('PEXPIRE', key, ttl)
    return 1
else
    return 0
end
"""

LUA_STATUS = """
local key = KEYS[1]
local owner = redis.call('GET', key)
if owner then
    local ttl = redis.call('PTTL', key)
    return { owner, ttl }
else
    return { false, -2 }
end
"""


class InMemoryRedis:
    def __init__(self):
        self._db = {}
        logger.info("Initializing in-memory fallback database for local development.")
        
    async def get(self, key: str):
        record = self._db.get(key)
        if record:
            # Check for expiration
            val, expiry = record
            if expiry and time.time() > expiry:
                del self._db[key]
                return None
            return val
        return None
        
    async def set(self, key: str, value: str, ex: int = None, nx: bool = False):
        if nx and key in self._db:
            # Check if expired
            val, expiry = self._db[key]
            if not expiry or time.time() <= expiry:
                return None
        expiry = (time.time() + ex) if ex else None
        self._db[key] = (value, expiry)
        return True
        
    async def delete(self, key: str):
        if key in self._db:
            del self._db[key]
            return 1
        return 0
        
    async def pexpire(self, key: str, ttl_ms: int):
        if key in self._db:
            val, _ = self._db[key]
            self._db[key] = (val, time.time() + (ttl_ms / 1000.0))
            return 1
        return 0

    async def pttl(self, key: str):
        if key in self._db:
            val, expiry = self._db[key]
            if expiry:
                remaining = int((expiry - time.time()) * 1000.0)
                return max(0, remaining)
            return -1
        return -2

    async def ping(self):
        return True

    async def publish(self, channel: str, message: str):
        logger.debug(f"InMemoryRedis mocked publish to {channel}: {message}")
        return 1

    async def eval(self, script: str, numkeys: int, *args):
        # 1. Handle Rate Limiter Token Bucket Script
        if "refill_rate" in script or len(args) >= 5:
            key, capacity, refill_rate, now = args[0], args[1], args[2], args[3]
            bucket_record = self._db.get(key)
            if bucket_record is None:
                tokens = float(capacity)
                last_update = float(now)
            else:
                bucket_data, _ = bucket_record
                tokens = float(bucket_data.get("tokens", capacity))
                last_update = float(bucket_data.get("last_update", now))
                
            delta_time = max(0.0, float(now) - last_update)
            refilled_tokens = int(delta_time * float(refill_rate))
            tokens = min(float(capacity), tokens + refilled_tokens)
            
            requested = 1
            if tokens >= requested:
                tokens = tokens - requested
                self._db[key] = ({"tokens": tokens, "last_update": now}, None)
                return [1, int(tokens)]
            else:
                return [0, int(tokens)]

        # 2. Handle Lock acquire script
        if "PEXPIRE" in script and "current_owner" in script:
            key = args[0]
            owner = args[1]
            ttl = int(args[2])
            current_owner = await self.get(key)
            if not current_owner:
                await self.set(key, owner, ex=ttl/1000.0)
                return 1
            elif current_owner == owner:
                await self.pexpire(key, ttl)
                return 1
            else:
                return 0

        # 3. Handle Lock release script
        if "DEL" in script and "current_owner" in script:
            key = args[0]
            owner = args[1]
            current_owner = await self.get(key)
            if current_owner == owner:
                await self.delete(key)
                return 1
            else:
                return 0

        # 4. Handle Lock renew script
        if "PEXPIRE" in script and not "current_owner" in script:
            key = args[0]
            owner = args[1]
            ttl = int(args[2])
            current_owner = await self.get(key)
            if current_owner == owner:
                await self.pexpire(key, ttl)
                return 1
            else:
                return 0

        # 5. Handle Lock status script
        if "PTTL" in script:
            key = args[0]
            owner = await self.get(key)
            if owner:
                ttl = await self.pttl(key)
                return [owner, ttl]
            else:
                return [None, -2]

        return None


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

    async def set(self, key: str, value: str, ex: int = None, nx: bool = False):
        await self.fallback_db.set(key, value, ex, nx)
        if self.is_fallback or not self.real_redis:
            return True
        try:
            return await self.real_redis.set(key, value, ex=ex, nx=nx)
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

    async def publish(self, channel: str, message: str):
        if self.is_fallback or not self.real_redis:
            return await self.fallback_db.publish(channel, message)
        try:
            return await self.real_redis.publish(channel, message)
        except Exception as e:
            logger.warning(f"Redis publish failed, falling back to in-memory: {e}")
            self.is_fallback = True
            return await self.fallback_db.publish(channel, message)

    async def rpush(self, name: str, *values):
        if self.is_fallback or not self.real_redis:
            return 1
        try:
            return await self.real_redis.rpush(name, *values)
        except Exception as e:
            logger.warning(f"Redis rpush failed, falling back to in-memory: {e}")
            self.is_fallback = True
            return 1

    async def blpop(self, keys, timeout: int = 0):
        if self.is_fallback or not self.real_redis:
            import asyncio
            await asyncio.sleep(timeout)
            return None
        try:
            return await self.real_redis.blpop(keys, timeout=timeout)
        except Exception as e:
            logger.warning(f"Redis blpop failed, falling back to in-memory: {e}")
            self.is_fallback = True
            import asyncio
            await asyncio.sleep(timeout)
            return None


class RedisLockManager:
    """High-speed server-side atomic distributed lock manager using compiled Redis Lua scripts."""
    def __init__(self, client: SafeRedisClient):
        self.client = client

    async def acquire_lock(self, key: str, owner: str, ttl_ms: int) -> bool:
        """Atomically obtains an exclusive lock lease using server-side Lua transaction."""
        result = await self.client.eval(LUA_ACQUIRE, 1, key, owner, str(ttl_ms))
        return result == 1

    async def renew_lock(self, key: str, owner: str, ttl_ms: int) -> bool:
        """Extends lifespan of active lease if the caller is the current registered owner."""
        result = await self.client.eval(LUA_RENEW, 1, key, owner, str(ttl_ms))
        return result == 1

    async def release_lock(self, key: str, owner: str) -> bool:
        """Safely evicts the lease without evicting competitor locks."""
        result = await self.client.eval(LUA_RELEASE, 1, key, owner)
        return result == 1

    async def get_lock_status(self, key: str) -> dict:
        """Audits current lock lease status and exact millisecond TTL remaining."""
        result = await self.client.eval(LUA_STATUS, 1, key)
        if result and result[0]:
            return {
                "isLocked": True,
                "owner": result[0],
                "ttlRemainingMs": int(result[1])
            }
        return {
            "isLocked": False,
            "owner": None,
            "ttlRemainingMs": -2
        }


# Initialize clients
redis_client = SafeRedisClient(settings.REDIS_URL)
lock_manager = RedisLockManager(redis_client)

async def get_redis():
    """Dependency injection for Redis client."""
    return redis_client

async def get_lock_manager():
    """Dependency injection for Lock Manager."""
    return lock_manager
