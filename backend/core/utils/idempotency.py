import json
import hashlib
from functools import wraps
from typing import Callable, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from backend.core.database.redis_client import redis_client

def idempotent_request(key_header: str = "Idempotency-Key", expire_seconds: int = 86400):
    """
    Decorator to ensure API idempotency. 
    If the same Idempotency-Key is provided within the expiration period,
    it returns the cached response instead of executing the function again.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            request: Request = kwargs.get("request") or next((a for a in args if isinstance(a, Request)), None)
            
            if not request:
                # If no request object is found in args/kwargs, bypass idempotency
                return await func(*args, **kwargs)
                
            idempotency_key = request.headers.get(key_header)
            
            if not idempotency_key:
                # If the header is missing, we allow execution but do not cache.
                # Alternatively, we could raise a 400 Bad Request if it's strictly required.
                return await func(*args, **kwargs)

            # Generate a unique hash for the cache key, binding the idempotency key to the specific route
            path_hash = hashlib.sha256(request.url.path.encode()).hexdigest()[:16]
            cache_key = f"idempotency:{path_hash}:{idempotency_key}"

            # Check if response already exists in Redis
            cached_response = await redis_client.get(cache_key)
            if cached_response:
                try:
                    cached_data = json.loads(cached_response)
                    return JSONResponse(
                        content=cached_data["content"],
                        status_code=cached_data["status_code"],
                        headers={**cached_data.get("headers", {}), "X-Idempotent-Replayed": "true"}
                    )
                except Exception:
                    pass  # Fallback to execution if cache is corrupted

            # Execute the actual endpoint logic
            response = await func(*args, **kwargs)

            # Cache the JSONResponse for future idempotent requests
            if isinstance(response, JSONResponse):
                cache_payload = {
                    "content": json.loads(response.body.decode("utf-8")),
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                await redis_client.set(cache_key, json.dumps(cache_payload), ex=expire_seconds)
                
            return response
        return wrapper
    return decorator
