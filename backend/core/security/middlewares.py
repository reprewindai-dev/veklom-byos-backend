import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.security.auth import verify_token
import json

class ZeroTrustMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/" or path.startswith("/status") or path.startswith("/health") or path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register") or path.startswith("/api/v1/auth/refresh") or path.startswith("/static") or path.startswith("/assets") or path.startswith("/workspace") or path.startswith("/command-center") or path.startswith("/gpc") or path.startswith("/terminal") or path.startswith("/marketplace") or path.startswith("/docs") or path.startswith("/uptime") or path.startswith("/legal"):
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if not auth_header and not api_key_header:
            return JSONResponse(status_code=401, content={"detail": "Missing authentication credentials"})
            
        try:
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                request.state.user_id = payload.get("sub")
            elif api_key_header:
                if not api_key_header.startswith("byos_"):
                    return JSONResponse(status_code=401, content={"detail": "Invalid API Key format"})
                request.state.api_key = api_key_header
        except Exception as e:
            return JSONResponse(status_code=401, content={"detail": f"Invalid credentials: {str(e)}"})
            
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        # Note: Actual metrics collection to Prometheus/StatsD would go here
        return response


class IntelligentRoutingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Placeholder for intelligent routing logic
        return await call_next(request)


class BudgetCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Placeholder for budget check logic
        # if budget_exhausted:
        #    return JSONResponse(status_code=402, content={"detail": "Budget exhausted"})
        return await call_next(request)
