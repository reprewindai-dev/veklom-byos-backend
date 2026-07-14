import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import backend.core.database.redis_client as redis_module
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate-limiting middleware backed by Redis.
    Limits are enforced dynamically based on authentication status.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Allow health checks and internal routes to bypass rate limiting
        if request.url.path.startswith(("/health", "/_ping", "/status", "/openapi.json", "/.well-known")):
            return await call_next(request)
            
        # Determine client identifier (prefer authenticated user, fallback to IP)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # We don't parse the full JWT here for performance; we just use the token hash as a key
            # In a real setup, you'd extract the `sub` or `workspace_id`.
            client_id = f"ratelimit:auth:{hash(auth_header)}"
            capacity = 100
            refill_rate = 5.0  # 5 tokens per second
        else:
            ip = request.client.host if request.client else "unknown_ip"
            client_id = f"ratelimit:ip:{ip}"
            capacity = 20
            refill_rate = 1.0  # 1 token per second
            
        # In production, if Redis is down (is_fallback is True), we bypass rate limiting
        # rather than blocking all traffic.
        if redis_module.redis_client.is_fallback:
            return await call_next(request)
            
        try:
            # Token bucket implementation via Redis Lua Script for atomicity
            lua_script = """
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local requested = 1

            local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
            local tokens = tonumber(bucket[1])
            local last_update = tonumber(bucket[2])

            if tokens == nil then
                tokens = capacity
                last_update = now
            end

            -- Refill tokens
            local delta_time = math.max(0, now - last_update)
            local refilled_tokens = math.floor(delta_time * refill_rate)
            tokens = math.min(capacity, tokens + refilled_tokens)

            if tokens >= requested then
                tokens = tokens - requested
                redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
                redis.call('EXPIRE', key, math.ceil(capacity / refill_rate))
                return {1, tokens}
            else
                return {0, tokens}
            end
            """
            
            now_ts = time.time()
            result = await redis_module.redis_client.eval(lua_script, 1, client_id, capacity, refill_rate, now_ts)
            
            allowed, remaining_tokens = result
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {client_id}")
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too Many Requests", "detail": "Rate limit exceeded. Please slow down."},
                    headers={"Retry-After": "1"}
                )
                
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(remaining_tokens)
            return response
            
        except Exception as e:
            logger.error(f"RateLimit middleware error: {e}")
            # Fail open if Redis throws an exception
            return await call_next(request)
