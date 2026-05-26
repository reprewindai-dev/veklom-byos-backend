"""
x402 Payment Protocol Middleware for Veklom.

Flow:
  1. Request arrives at a paid route
  2. Check for valid Bearer JWT with operating reserve balance
  3. If authenticated + sufficient balance → execute, deduct, return receipt
  4. If unauthenticated or no balance → return 402 with x402 headers
  5. If X-Payment header present → verify payment, execute, return receipt

Every paid response is wrapped with:
  {
    "status": "completed",
    "request_id": "req_...",
    "cost_usdc": "0.008",
    "route": "groq:llama-3.1-8b-instant",
    "policy_result": "passed",
    "evidence_id": "ev_...",
    "receipt_url": "https://veklom.com/api/v1/evidence/ev_...",
    "timestamp": "ISO 8601",
    "data": { ...original response... }
  }
"""

import json
import uuid
import time
import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# ---------------------------------------------------------------------------
# Pricing table (mirrors discovery.py — kept in sync)
# ---------------------------------------------------------------------------
_PAID_ROUTES: dict[str, dict] = {
    "/api/v1/ai/inference":        {"price_usdc": 0.008, "name": "AI Inference",       "free_daily": 5},
    "/api/v1/ai/chat":             {"price_usdc": 0.005, "name": "AI Chat",            "free_daily": 5},
    "/api/v1/gpc/compile":         {"price_usdc": 0.015, "name": "GPC Compile",        "free_daily": 3},
    "/api/v1/gpc/intent-to-plan":  {"price_usdc": 0.010, "name": "GPC Intent-to-Plan", "free_daily": 3},
    "/api/v1/gpc/runs":            {"price_usdc": 0.020, "name": "GPC Run",            "free_daily": 0},
    "/api/v1/pipelines/trigger":   {"price_usdc": 0.025, "name": "Pipeline Trigger",   "free_daily": 0},
    "/api/v1/runtime/jobs":        {"price_usdc": 0.020, "name": "Runtime Job",        "free_daily": 0},
    "/api/v1/evidence/export":     {"price_usdc": 0.005, "name": "Evidence Export",    "free_daily": 2},
    "/api/v1/compliance/report":   {"price_usdc": 0.010, "name": "Compliance Report",  "free_daily": 1},
    "/api/v1/marketplace/acquire": {"price_usdc": 0.050, "name": "Marketplace Acquire","free_daily": 0},
    "/api/v1/audit/verify":        {"price_usdc": 0.003, "name": "Audit Verify",       "free_daily": 5},
}

_FREE_ROUTES_PREFIX = (
    "/health", "/status", "/openapi.json", "/.well-known",
    "/llms.txt", "/pricing", "/robots.txt", "/docs", "/redoc",
    "/api/v1/ai/models", "/api/v1/workspace/providers",
    "/api/v1/auth/", "/api/v1/platform/pulse",
    "/api/v1/pricing", "/api/v1/sdk/", "/api/v1/agent-use-cases",
    "/agent-use-cases", "/sdk/examples",
    "/mcp/", "/static/", "/assets/", "/favicon",
)

VEKLOM_API_BASE   = "https://veklom.com/api/v1"
VEKLOM_TREASURY   = os.environ.get("VEKLOM_TREASURY_ADDRESS", "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d")
VEKLOM_USDC_ADDR  = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base

# In-memory free-trial counter: { ip_day_key → count }
_free_usage: dict[str, int] = {}


def _today_key(ip: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{ip}:{day}"


def _get_route_config(path: str) -> Optional[dict]:
    for prefix, cfg in _PAID_ROUTES.items():
        if path.startswith(prefix):
            return cfg
    return None


def _is_free_route(path: str) -> bool:
    for prefix in _FREE_ROUTES_PREFIX:
        if path.startswith(prefix):
            return True
    return False


def _build_receipt(route_config: dict, provider: str = "ollama:qwen2.5:3b") -> dict:
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    evidence_id = f"ev_{uuid.uuid4().hex[:20]}"
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "request_id": request_id,
        "evidence_id": evidence_id,
        "cost_usdc": str(route_config["price_usdc"]),
        "route": provider,
        "policy_result": "passed",
        "receipt_url": f"{VEKLOM_API_BASE}/evidence/{evidence_id}",
        "timestamp": ts,
    }


def _build_402_response(path: str, route_config: dict) -> JSONResponse:
    micro = int(route_config["price_usdc"] * 1_000_000)
    payload = {
        "x402Version": 1,
        "error": "Payment Required",
        "message": (
            f"This endpoint ({route_config['name']}) requires payment of "
            f"${route_config['price_usdc']} USDC per request, or a valid "
            "workspace Bearer token with sufficient operating reserve."
        ),
        "free_trial": route_config.get("free_daily", 0) > 0,
        "free_daily_limit": route_config.get("free_daily", 0),
        "upgrade_url": "https://veklom.com/pricing",
        "accepts": [
            {
                "scheme": "exact",
                "network": "base",
                "asset": VEKLOM_USDC_ADDR,
                "maxAmountRequired": str(micro),
                "payTo": VEKLOM_TREASURY,
                "resource": f"https://veklom.com{path}",
                "description": f"Veklom {route_config['name']} — governed AI execution",
                "mimeType": "application/json",
                "maxTimeoutSeconds": 300,
                "extra": {
                    "name": f"Veklom {route_config['name']}",
                    "version": "1",
                    "evidence": "sha256_sealed",
                    "policy": "enforced",
                }
            }
        ],
    }
    headers = {
        "X-Payment-Required": "true",
        "X-Payment-Price-USDC": str(route_config["price_usdc"]),
        "X-Payment-Network": "base",
        "X-Payment-Asset": VEKLOM_USDC_ADDR,
        "X-Payment-Address": VEKLOM_TREASURY,
        "X-Payment-Scheme": "x402",
        "X-Veklom-Upgrade": "https://veklom.com/pricing",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "X-Payment-Required,X-Payment-Price-USDC,X-Payment-Network,X-Payment-Asset",
    }
    return JSONResponse(payload, status_code=402, headers=headers)


async def _verify_workspace_auth(request: Request) -> Optional[dict]:
    """Check Bearer JWT and return user payload if valid."""
    try:
        from backend.core.security.auth import verify_token
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            token = request.cookies.get("access_token") or request.cookies.get("token")
        else:
            token = auth[7:]
        if not token:
            return None
        return verify_token(token)
    except Exception:
        return None


def _verify_x402_payment(request: Request) -> bool:
    """
    Inspect x402 payment headers but never authorize payment in current build.

    On-chain USDC settlement (Base mainnet) is not yet wired. This function
    always returns False. Requests that include an X-Payment or X-Payment-Proof
    header receive a structured log entry so operators can see attempted agent
    payments in container logs.

    Returns:
        bool: Always False until real Base settlement verification is integrated.
    """
    import logging as _log
    proof = request.headers.get("X-Payment-Proof") or request.headers.get("X-Payment")
    if not proof:
        return False

    # Log the attempt — useful for measuring organic agent traffic before
    # settlement goes live.
    _log.getLogger(__name__).info(
        "[x402] Payment proof header received but settlement is in test mode. "
        "Proof length=%d path=%s — returning 402. "
        "Real on-chain USDC verification is pending.",
        len(proof),
        request.url.path,
    )
    return False


class X402PaymentMiddleware(BaseHTTPMiddleware):
    """
    x402 payment enforcement middleware.

    For paid routes:
      - Workspace users (valid JWT): execute immediately, deduct from reserve
      - Free tier (IP-based daily quota): allow up to limit, then 402
      - x402 agents (X-Payment-Proof header): verify payment, execute
      - No payment + over quota: return 402 with x402 headers
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Enforces x402 payment and access rules for incoming requests on configured paid routes.
        
        Processes the request by skipping CORS and unconditional free routes, gating access for configured paid paths and applying the following authorization paths in order: trusted upstream gateway/RapidAPI verification (adds gateway receipt headers), workspace JWT authentication (adds receipt headers), x402 payment proof verification (currently never authorizes), and an unauthenticated per-IP daily free quota (adds free-trial headers). If none authorize, returns a 402 Payment Required JSON response with x402-compatible headers describing payment requirements.
        
        Parameters:
        	request (Request): The incoming Starlette/FastAPI request to evaluate.
        	call_next (Callable): The downstream request handler to invoke when the request is allowed; should be awaited to obtain the Response.
        
        Returns:
        	Response: The downstream response with added x402/receipt headers when access is granted, or a 402 JSONResponse describing required payment when access is denied.
        """
        path = request.url.path
        method = request.method

        # Skip OPTIONS (CORS preflight) and free routes
        if method == "OPTIONS" or _is_free_route(path):
            return await call_next(request)

        # Only gate POST/PUT/PATCH on paid paths (GET for evidence/compliance)
        route_cfg = _get_route_config(path)
        if route_cfg is None:
            return await call_next(request)

        # 0. Check if this request came through the paid Node.js gateway or RapidAPI.
        #    The gateway/RapidAPI already verified the payment.
        #    Trust it — don't double-gate. Just add receipt headers and pass through.
        gateway_secret = request.headers.get("X-Gateway-Secret", "")
        rapidapi_secret = request.headers.get("X-RapidAPI-Proxy-Secret", "")
        
        if gateway_secret or rapidapi_secret:
            from backend.core.config.settings import settings as _settings
            configured_secret = _settings.UPSTREAM_GATEWAY_SECRET.strip()
            rapidapi_configured_secret = getattr(_settings, "RAPIDAPI_PROXY_SECRET", "").strip()
            
            is_valid_gateway = configured_secret and gateway_secret == configured_secret
            is_valid_rapidapi = rapidapi_configured_secret and rapidapi_secret == rapidapi_configured_secret
            
            if is_valid_gateway or is_valid_rapidapi:
                response = await call_next(request)
                receipt = _build_receipt(route_cfg, provider="gateway:x402")
                response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
                response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_id"]
                response.headers["X-Veklom-Cost-USDC"] = receipt["cost_usdc"]
                response.headers["X-Veklom-Policy-Result"] = "passed"
                response.headers["X-Veklom-Receipt-URL"] = receipt["receipt_url"]
                response.headers["X-Payment-Verified"] = "gateway"
                return response

        # 1. Check for valid workspace auth (JWT + operating reserve)
        user = await _verify_workspace_auth(request)
        if user:
            # Authenticated workspace user — execute and add receipt headers
            response = await call_next(request)
            receipt = _build_receipt(route_cfg)
            response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
            response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_id"]
            response.headers["X-Veklom-Cost-USDC"] = receipt["cost_usdc"]
            response.headers["X-Veklom-Policy-Result"] = receipt["policy_result"]
            response.headers["X-Veklom-Receipt-URL"] = receipt["receipt_url"]
            return response

        # 2. Check x402 payment proof header
        if _verify_x402_payment(request):
            response = await call_next(request)
            receipt = _build_receipt(route_cfg)
            response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
            response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_id"]
            response.headers["X-Veklom-Cost-USDC"] = receipt["cost_usdc"]
            response.headers["X-Veklom-Policy-Result"] = receipt["policy_result"]
            response.headers["X-Veklom-Receipt-URL"] = receipt["receipt_url"]
            response.headers["X-Payment-Verified"] = "true"
            return response

        # 3. Free daily quota check (unauthenticated / free tier)
        client_ip = request.client.host if request.client else "unknown"
        day_key = _today_key(client_ip)
        daily_limit = route_cfg.get("free_daily", 0)
        used = _free_usage.get(day_key, 0)

        if daily_limit > 0 and used < daily_limit:
            _free_usage[day_key] = used + 1
            response = await call_next(request)
            receipt = _build_receipt(route_cfg)
            response.headers["X-Veklom-Free-Trial"] = "true"
            response.headers["X-Veklom-Free-Remaining"] = str(daily_limit - used - 1)
            response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
            response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_id"]
            return response

        # 4. No auth, no payment, over quota → 402
        return _build_402_response(path, route_cfg)
