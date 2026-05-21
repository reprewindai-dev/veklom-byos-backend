import logging
import redis.asyncio as redis
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

# Create an async redis connection pool using the provided URL
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        retry_on_timeout=True
    )
except Exception as e:
    logger.error(f"Failed to initialize Redis client: {e}")
    redis_client = None

async def get_redis() -> redis.Redis:
    """Dependency injection for Redis client."""
    return redis_client
