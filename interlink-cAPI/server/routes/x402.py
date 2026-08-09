"""
GET /capi/x402 — x402 config and pricing manifest.
Migrated from the legacy Next.js cAPI container to be the canonical source of truth.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["x402"])

# Wallet addresses & chain config
PAYMENT_WALLET = "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"
ID_WALLET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
CHAIN_ID = "eip155:8453"
BASE_APP_ID = "6a20f24cc341f72c2f573eb5"

# Per-route pricing in USDC
PRICES: dict[str, str] = {
    "/api/compose": "0.015",
    "/api/request": "0.010",
    "/api/audit": "0.005",
    "/api/pgl": "0.005",
    "/api/replay": "0.005",
    "/api/state": "0.003",
    "/api/discover": "0.003",
    "/api/budget": "0.003",
    "/capi/mcp/call": "0.010",
    "/capi/intent": "0.010",
    "/capi/governance": "0.005",
}


@router.get("/x402")
async def x402_config():
    """
    x402 config and pricing for agents and wallets.
    This is the canonical x402 manifest for capi.veklom.com.
    """
    return JSONResponse({
        "x402_version": 2,
        "provider": "Veklom cAPI — Covenant Execution Gateway",
        "chain": CHAIN_ID,
        "payment_wallet": PAYMENT_WALLET,
        "identity_wallet": ID_WALLET,
        "usdc_contract": USDC_CONTRACT,
        "base_app_id": BASE_APP_ID,
        "prices": PRICES,
        "spec": "https://x402.org",
        "discovery": "/.well-known/x402.json",
    })


@router.get("/.well-known/x402.json")
async def x402_well_known():
    """
    Well-known x402 discovery document for automated client discovery.
    """
    return JSONResponse({
        "x402_version": 2,
        "accepts": [
            {
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "0.020",
                "resource": "capi.veklom.com",
                "description": "Veklom cAPI governed compute — pay-per-call USDC on Base",
                "mimeType": "application/json",
                "payTo": PAYMENT_WALLET,
                "maxTimeoutSeconds": 30,
                "asset": USDC_CONTRACT,
                "extra": {
                    "name": "USD Coin",
                    "version": "2",
                },
            }
        ],
    })
