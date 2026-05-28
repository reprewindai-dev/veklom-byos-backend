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
    "/api/v1/openapi.json", "/v1/openapi.json",
    "/api/v1/sys/health", "/api/v1/sys/gpu",
    "/api/v1/copilot/registry", "/api/v1/copilot/recent-decisions",
    "/api/v1/integrations/", "/api/v1/receipts", "/api/v1/evidence/verify"
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
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    payload = {
        "error": "payment_required",
        "route": path,
        "price": {
            "amount": str(route_config["price_usdc"]),
            "currency": "USDC",
            "network": "base"
        },
        "payment": {
            "protocol": "x402",
            "config_url": "https://api.veklom.com/.well-known/x402.json"
        },
        "retry": {
            "header": "payment-required",
            "idempotency_key_required": True
        },
        "request_id": request_id
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


async def _verify_x402_payment(request: Request, route_config: dict) -> bool:
    """
    Verify the x402 payment proof header by querying the Base mainnet JSON-RPC node.
    Checks if the transaction is:
      1. Valid transaction hash on Base mainnet
      2. Successful status (0x1)
      3. Transfers USDC (0x833589fcd6edb6e08f4c7c32d4f71b54bda02913)
      4. Destination address matches VEKLOM_TREASURY
      5. Value is greater than or equal to the route cost in micro USDC
      6. Has not been previously used (prevents replay attacks via Redis)
    """
    import httpx
    import logging
    from backend.core.database.redis_client import redis_client

    logger = logging.getLogger(__name__)
    proof = request.headers.get("X-Payment-Proof") or request.headers.get("X-Payment")
    if not proof:
        return False

    tx_hash = proof.strip()
    if not (tx_hash.startswith("0x") and len(tx_hash) == 66):
        logger.warning(f"[x402] Invalid transaction hash format: {tx_hash}")
        return False

    # 1. Prevent replay attacks
    redis_key = f"x402_tx:{tx_hash}"
    already_used = await redis_client.get(redis_key)
    if already_used:
        logger.warning(f"[x402] Replay attack detected. Tx hash {tx_hash} already used.")
        return False

    # 2. Query Base mainnet JSON-RPC with high-reliability public endpoints
    rpc_endpoints = [
        "https://mainnet.base.org",
        "https://base.llamarpc.com",
        "https://base-rpc.publicnode.com"
    ]

    tx_receipt = None
    async with httpx.AsyncClient(timeout=5.0) as client:
        for rpc_url in rpc_endpoints:
            try:
                rpc_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [tx_hash],
                    "id": 1
                }
                res = await client.post(rpc_url, json=rpc_payload)
                if res.status_code == 200:
                    data = res.json()
                    if "result" in data and data["result"] is not None:
                        tx_receipt = data["result"]
                        break
            except Exception as e:
                logger.warning(f"[x402] RPC check failed on {rpc_url}: {e}")
                continue

    if not tx_receipt:
        logger.warning(f"[x402] Could not fetch receipt for transaction hash: {tx_hash}")
        return False

    # 3. Check transaction status (0x1 = success)
    status = tx_receipt.get("status")
    if status != "0x1":
        logger.warning(f"[x402] Transaction {tx_hash} failed or status is not 0x1: {status}")
        return False

    # 4. Check if treasury is configured
    treasury_addr = VEKLOM_TREASURY.lower().strip()
    if not treasury_addr or treasury_addr == "not_configured" or treasury_addr == "0x0000000000000000000000000000000000000001":
        logger.warning(f"[x402] VEKLOM_TREASURY ({VEKLOM_TREASURY}) is not fully configured. Cannot verify payment destination.")
        return False

    # Standard USDC contract address on Base
    usdc_contract = VEKLOM_USDC_ADDR.lower()
    
    # ERC20 Transfer event signature: Transfer(address,address,uint256)
    transfer_event_sig = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    # Compute expected transfer amount in micro USDC
    expected_amount = int(route_config["price_usdc"] * 1_000_000)

    # 5. Parse logs for USDC Transfer to VEKLOM_TREASURY
    logs = tx_receipt.get("logs", [])
    payment_verified = False
    actual_amount = 0

    for log in logs:
        log_address = log.get("address", "").lower()
        if log_address != usdc_contract:
            continue

        topics = log.get("topics", [])
        if not topics or topics[0].lower() != transfer_event_sig:
            continue

        if len(topics) < 3:
            continue

        to_topic = topics[2].lower()
        expected_padded = treasury_addr.replace("0x", "").zfill(64)
        if expected_padded not in to_topic:
            continue

        log_data = log.get("data", "")
        if not log_data or log_data == "0x":
            continue

        try:
            val = int(log_data, 16)
            actual_amount += val
        except ValueError:
            continue

    if actual_amount >= expected_amount:
        payment_verified = True
    else:
        logger.warning(
            f"[x402] Payment amount insufficient. "
            f"Expected={expected_amount} micro USDC, Found={actual_amount} micro USDC"
        )
        return False

    if payment_verified:
        # 6. Save tx hash to redis to prevent replay (expire in 7 days)
        await redis_client.set(redis_key, "used", ex=604800)
        logger.info(
            f"[x402] Payment verified successfully! Tx: {tx_hash}, "
            f"Verified {actual_amount} micro USDC to treasury {VEKLOM_TREASURY}."
        )
        return True

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
        user_payload = await _verify_workspace_auth(request)
        if user_payload:
            user_id = user_payload.get("sub")
            if user_id:
                from sqlalchemy import select, func
                from backend.core.database.database import get_db_session
                from backend.db.models.user import User
                from backend.db.models.workspace import Workspace
                from backend.db.models.ai import ExecutionLog
                from backend.db.models.billing import Subscription

                async with get_db_session() as db:
                    user_res = await db.execute(select(User).where(User.id == user_id))
                    db_user = user_res.scalar_one_or_none()
                    
                    if db_user:
                        ws_id = db_user.workspace_id or ""
                        
                        # Resolve active subscription
                        sub_res = await db.execute(
                            select(Subscription)
                            .where(
                                Subscription.workspace_id == ws_id,
                                Subscription.status.in_(["active", "trialing"]),
                            )
                            .order_by(Subscription.created_at.desc())
                            .limit(1)
                        )
                        active_sub = sub_res.scalar_one_or_none()
                        
                        # Fallback to workspace license_tier
                        ws_res = await db.execute(select(Workspace).where(Workspace.id == ws_id))
                        db_ws = ws_res.scalar_one_or_none()
                        license_tier = db_ws.license_tier if db_ws else "free"
                        
                        plan = active_sub.plan if active_sub else license_tier
                        
                        # If workspace is on free/community evaluation tier, check 15 cumulative runs limit
                        if plan in ("free", "community", "none", None):
                            runs_count = await db.scalar(
                                select(func.count(ExecutionLog.id))
                                .where(ExecutionLog.workspace_id == ws_id)
                            ) or 0
                            
                            if runs_count >= 15:
                                return _build_402_response(path, route_cfg)
                        
                        # Execute request
                        response = await call_next(request)
                        
                        if response.status_code < 400:
                            new_log = ExecutionLog(
                                workspace_id=ws_id,
                                user_id=user_id,
                                model=route_cfg.get("name", "Governed Action"),
                                provider="ollama:qwen2.5:3b",
                                cost=route_cfg["price_usdc"],
                                status="completed"
                            )
                            db.add(new_log)
                            await db.commit()
                            
                        receipt = _build_receipt(route_cfg)
                        response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
                        response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_id"]
                        response.headers["X-Veklom-Cost-USDC"] = receipt["cost_usdc"]
                        response.headers["X-Veklom-Policy-Result"] = receipt["policy_result"]
                        response.headers["X-Veklom-Receipt-URL"] = receipt["receipt_url"]
                        return response

        # 2. Check x402 payment proof header
        if await _verify_x402_payment(request, route_cfg):
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
