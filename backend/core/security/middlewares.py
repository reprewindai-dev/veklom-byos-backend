import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.security.auth import verify_token
import json

class ZeroTrustMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Public bypass routes
        public_prefixes = (
            "/status", "/health", "/api/v1/auth/login", "/api/v1/auth/register",
            "/api/v1/auth/refresh", "/static", "/assets", "/workspace",
            "/command-center", "/gpc", "/terminal", "/marketplace", "/docs",
            "/uptime", "/legal", "/irongrid", "/api/v1/webhooks", "/.well-known",
            "/robots.txt", "/llms.txt", "/sitemap.xml", "/favicon",
            "/apple-touch-icon.png", "/og-image.png", "/twitter-card.png",
            "/logo.png", "/icon.png", "/api/v1/ai/models", "/api/v1/pricing",
            "/api/v1/platform/pulse", "/api/v1/sdk/", "/api/v1/agent-use-cases",
            "/sdk/examples", "/mcp/", "/openapi.json"
        )
        
        if path == "/" or any(path.startswith(prefix) for prefix in public_prefixes):
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
