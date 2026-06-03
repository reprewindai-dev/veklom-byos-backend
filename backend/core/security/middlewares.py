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
            "/status", "/health", "/api/health", "/api/v1/auth/login", "/api/v1/auth/register",
            "/api/v1/health", "/redoc",
            "/api/v1/auth/eval-session", "/api/v1/auth/providers",
            "/api/v1/auth/signup", "/api/v1/auth/signin",
            "/api/v1/evaluations/start", "/api/v1/smoke/eval-token",
            "/api/v1/auth/refresh", "/api/v1/auth/github", "/static", "/assets", "/workspace",
            "/login", "/signup", "/api/v1/complaints",
            "/config.js", "/base-attribution.js", "/auth-gate.js", "/addons-inject.js", "/overview-live.js",
            "/workspace-enhance.js", "/pipeline-live.js", "/playground-live.js", "/user-identity-inject.js", "/copilot-widget.js",
            "/command-center", "/control-plane-next", "/gpc", "/terminal", "/marketplace", "/docs",
            "/uptime", "/legal", "/license", "/vendor-agreement", "/irongrid", "/api/v1/webhooks", "/api/v1/edge", "/.well-known",
            "/robots.txt", "/llms.txt", "/sitemap.xml", "/favicon",
            "/apple-touch-icon.png", "/og-image.png", "/twitter-card.png",
            "/logo.png", "/icon.png", "/api/v1/ai/models", "/api/v1/pricing", "/api/v1/subscriptions/plans", "/api/v1/subscriptions/current", "/status/data",
            "/api/v1/platform/pulse", "/api/v1/sdk/", "/api/v1/agent-use-cases",
            "/sdk/examples", "/mcp/", "/openapi.json", "/api/v1/openapi.json",
            "/v1/openapi.json", "/api/v1/sys/health", "/api/v1/sys/gpu",
            "/api/v1/copilot/registry", "/api/v1/copilot/recent-decisions",
            "/api/v1/workspace/overview/live", "/api/v1/integrations/pagerduty",
            "/api/v1/receipts", "/api/v1/evidence/verify",
            "/api/v1/ai/inference", "/api/v1/ai/chat", "/api/v1/gpc/compile",
            "/api/v1/gpc/intent-to-plan", "/api/v1/gpc/runs", "/api/v1/pipelines/trigger",
            "/api/v1/runtime/jobs", "/api/v1/evidence/export", "/api/v1/compliance/report",
            "/api/v1/marketplace/acquire", "/api/v1/audit/verify", "/api/v1/webhook", "/api/v1/x402",
            "/api/v1/ai/complete", "/api/v1/playground/inference", "/api/v1/playground/sessions",
            "/api/v1/playground/tools", "/api/v1/playground/prompts", "/api/v1/connectors/fax",
            "/api/v1/contact", "/api/v1/feedback"
            "/api/v1/playground/tools", "/api/v1/playground/prompts",
            "/api/v1/agentic_commerce/product_feed", "/api/v1/agentic_commerce/feed.csv"
        )
        
        if path == "/" or any(path.startswith(prefix) for prefix in public_prefixes):
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        # Cookie fallback — fixes session hydration race on page loads after login
        cookie_token = request.cookies.get("access_token")
        
        if not auth_header and not api_key_header and not cookie_token:
            return JSONResponse(status_code=401, content={"detail": "Missing authentication credentials"})
            
        try:
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = verify_token(token, enforce_replay=False)
                request.state.user_id = payload.get("sub")
            elif api_key_header:
                if not api_key_header.startswith("byos_"):
                    return JSONResponse(status_code=401, content={"detail": "Invalid API Key format"})
                request.state.api_key = api_key_header
            elif cookie_token:
                # Accept HttpOnly cookie set on login/register
                payload = verify_token(cookie_token, enforce_replay=False)
                request.state.user_id = payload.get("sub")
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
                        payload = verify_token(token, enforce_replay=False)
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

import asyncio
from backend.db.models.telemetry import AgentCall

class AgentTelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not (path.startswith("/api/v1/ai") or path.startswith("/api/v1/playground") or path.startswith("/api/v1/exec")):
            return await call_next(request)
            
        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        
        tenant_id = getattr(request.state, "workspace_id", "unknown")
        if not tenant_id or tenant_id == "unknown":
            tenant_id = getattr(request.state, "user_id", "anonymous")
            
        status_code = response.status_code
        policy_result = getattr(request.state, "policy_result", "allow" if status_code < 400 else "error")
        policy_error_code = getattr(request.state, "policy_error_code", None)
        model_key = getattr(request.state, "model_key", "unknown")
        context_tokens = getattr(request.state, "context_tokens", 0)
        input_tokens = getattr(request.state, "input_tokens", 0)
        output_tokens = getattr(request.state, "output_tokens", 0)
        
        async def write_telemetry():
            try:
                async with async_session() as session:
                    call = AgentCall(
                        tenant_id=tenant_id,
                        route=path,
                        model_key=model_key,
                        latency_ms=duration_ms,
                        http_status=status_code,
                        policy_result=policy_result,
                        policy_error_code=policy_error_code,
                        context_tokens=context_tokens,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens
                    )
                    session.add(call)
                    await session.commit()
            except Exception as e:
                print(f"[Telemetry] failed to write: {e}")
                
        asyncio.create_task(write_telemetry())
        return response


# Simple in-memory rate limiting for IP auth failures
ip_failures = {}

class IPRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/v1/auth/login"):
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        if client_ip in ip_failures:
            # 15 minute window
            ip_failures[client_ip] = [ts for ts in ip_failures[client_ip] if now - ts < 900]
            if len(ip_failures[client_ip]) >= 5:
                import logging
                logging.warning(json.dumps({"event": "auth.ip.banned", "ip": client_ip, "reason": "Too many failed attempts"}))
                return JSONResponse(status_code=429, content={"detail": "Too many failed attempts. IP temporarily locked."})
                
        response = await call_next(request)
        if response.status_code == 401:
            import logging
            logging.warning(json.dumps({"event": "auth.login.failed", "ip": client_ip}))
            if client_ip not in ip_failures:
                ip_failures[client_ip] = []
            ip_failures[client_ip].append(now)
            
        return response
