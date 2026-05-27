import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.security.auth import verify_token
import json

from backend.core.database.database import async_session
from sqlalchemy import select
from backend.db.models.user import User, APIKey
from backend.db.models.security import KillSwitchState

class ZeroTrustMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Public bypass routes
        public_prefixes = (
            "/status", "/health", "/api/v1/health", "/api/v1/auth/login", "/api/v1/auth/register",
            "/api/v1/auth/refresh", "/api/v1/auth/github", "/api/v1/auth/providers",
            "/static", "/assets", "/workspace",
            "/command-center", "/operator-center", "/gpc", "/terminal", "/marketplace",
            "/docs", "/redoc",
            "/uptime", "/legal", "/irongrid", "/api/v1/webhooks", "/.well-known",
            "/robots.txt", "/llms.txt", "/sitemap.xml", "/favicon",
            "/apple-touch-icon.png", "/og-image.png", "/twitter-card.png",
            "/logo.png", "/icon.png", "/api/v1/ai/models", "/api/v1/pricing",
            "/api/v1/platform/pulse", "/api/v1/sdk/", "/api/v1/agent-use-cases",
            "/sdk/examples", "/mcp/", "/openapi.json", "/api/v1/openapi.json",
            "/v1/openapi.json", "/api/v1/sys/health", "/api/v1/sys/gpu",
            "/api/v1/copilot/registry", "/api/v1/copilot/recent-decisions",
            "/api/v1/workspace/overview/live", "/api/v1/integrations/pagerduty"
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
        return response


class IntelligentRoutingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Placeholder for intelligent routing logic
        return await call_next(request)


class BudgetCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_paid_path = (
            path.startswith("/api/v1/ai") or
            path.startswith("/api/v1/playground/inference") or
            path.startswith("/api/v1/exec") or
            path.startswith("/v1/chat/completions") or
            (path.startswith("/api/v1/pipelines") and path.endswith("/run"))
        )
        
        workspace_id = None
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if is_paid_path:
            try:
                async with async_session() as session:
                    if auth_header and auth_header.startswith("Bearer "):
                        token = auth_header.split(" ")[1]
                        payload = verify_token(token)
                        user_id = payload.get("sub")
                        if user_id:
                            result = await session.execute(select(User).where(User.id == user_id))
                            user = result.scalar_one_or_none()
                            if user:
                                workspace_id = user.workspace_id
                    elif api_key_header:
                        key_prefix = api_key_header[:10]
                        result = await session.execute(select(APIKey).where(APIKey.key_prefix == key_prefix))
                        api_key = result.scalar_one_or_none()
                        if api_key:
                            workspace_id = api_key.workspace_id
            except Exception as e:
                print(f"[BudgetCheckMiddleware] warning: failed to resolve workspace_id: {e}")
                
        if is_paid_path and workspace_id:
            try:
                async with async_session() as session:
                    result = await session.execute(
                        select(KillSwitchState).where(
                            KillSwitchState.workspace_id == workspace_id,
                            KillSwitchState.is_active == True
                        )
                    )
                    kill_switch = result.scalar_one_or_none()
                    if kill_switch:
                        return JSONResponse(
                            status_code=402,
                            content={
                                "detail": "Emergency halt active. All AI executions paused via Cost Kill Switch.",
                                "kill_switch_active": True,
                                "reason": kill_switch.reason or "Runaway usage detected",
                                "activated_at": kill_switch.activated_at.isoformat() if kill_switch.activated_at else None
                            }
                        )
            except Exception as e:
                print(f"[BudgetCheckMiddleware] warning: failed to check kill switch state: {e}")
                
        return await call_next(request)

