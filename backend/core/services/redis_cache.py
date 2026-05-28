"""Redis cache service for webhook idempotency."""

import json
from typing import Optional

import redis.asyncio as redis
from backend.core.config.settings import settings


class RedisCache:
    """Redis cache for webhook idempotency and replay protection."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.enabled = settings.REDIS_ENABLED and bool(settings.REDIS_URL)
        
        if self.enabled:
            try:
                self.client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                print("Redis cache initialized")
            except Exception as e:
                print(f"Failed to initialize Redis cache: {e}")
                self.enabled = False
        else:
            print("Redis cache disabled")
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        if not self.enabled or not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set a value in cache with TTL."""
        if not self.enabled or not self.client:
            return False
        try:
            await self.client.set(key, value, ex=ttl)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        if not self.enabled or not self.client:
            return False
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self.enabled or not self.client:
            return False
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False
    
    async def close(self):
        """Close the Redis connection."""
        if self.client:
            await self.client.close()


# Global instance
redis_cache = RedisCache()
