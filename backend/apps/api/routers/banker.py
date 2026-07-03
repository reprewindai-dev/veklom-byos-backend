"""
Banker Agent Router — Admin-only autonomous payment management endpoints.

Routes:
  GET  /api/v1/banker/status      — wallet address, USDC balance, daily spend, enabled state
  GET  /api/v1/banker/ledger      — paginated spend history from agent_wallet_ledger
  POST /api/v1/banker/pay         — manually trigger a one-shot payment (admin use)
  POST /api/v1/banker/self-prove  — full end-to-end settlement proof (for Chet)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.services.banker_agent import (
    BankerAgentService,
    BankerAgentError,
    BankerAgentConfigError,
    BankerAgentInsufficientFundsError,
    BankerAgentDailyLimitError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/banker", tags=["Banker Agent"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BankerStatusResponse(BaseModel):
    enabled:            bool
    agent_address:      Optional[str]
    usdc_balance:       float
    daily_spend:        dict
    treasury_address:   str
    usdc_contract:      str
    network:            str
    chain_id:           int


class ManualPayRequest(BaseModel):
    to_address:  str   = Field(..., description="Recipient EVM address (0x...)")
    amount_usdc: float = Field(..., gt=0, description="Amount in USDC (e.g. 0.10)")
    purpose:     str   = Field("manual_payment", description="Short description for audit trail")
    route:       str   = Field("/manual", description="Route label for ledger context")


class ManualPayResponse(BaseModel):
    status:     str
    tx_hash:    str
    amount_usdc: float
    to_address:  str
    basescan_url: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status", response_model=BankerStatusResponse)
async def banker_status():
    """
    Returns the current state of the Banker Agent wallet:
    address, USDC balance, daily spend, and enabled flag.
    Does NOT require authentication — status is non-sensitive.
    """
    enabled       = BankerAgentService.is_enabled()
    agent_address = BankerAgentService.get_agent_address()
    daily_spend   = BankerAgentService.get_daily_spend()

    usdc_balance = 0.0
    if agent_address:
        try:
            usdc_balance = await BankerAgentService.get_usdc_balance_usdc()
        except Exception as exc:
            logger.warning(f"[BankerRouter] Could not fetch USDC balance: {exc}")

    return BankerStatusResponse(
        enabled          = enabled,
        agent_address    = agent_address,
        usdc_balance     = usdc_balance,
        daily_spend      = daily_spend,
        treasury_address = settings.VEKLOM_TREASURY_ADDRESS,
        usdc_contract    = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        network          = "base",
        chain_id         = 8453,
    )


@router.get("/ledger")
async def banker_ledger(
    page:     int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated spend history from the agent_wallet_ledger table.
    Records are ordered newest-first.
    """
    from backend.db.models.agent_wallet import AgentWalletLedger

    q = select(AgentWalletLedger).order_by(desc(AgentWalletLedger.created_at))
    if status_filter:
        q = q.where(AgentWalletLedger.status == status_filter)

    count_q = select(func.count()).select_from(AgentWalletLedger)
    if status_filter:
        count_q = count_q.where(AgentWalletLedger.status == status_filter)

    total   = (await db.execute(count_q)).scalar() or 0
    offset  = (page - 1) * per_page
    rows    = (await db.execute(q.offset(offset).limit(per_page))).scalars().all()

    return {
        "page":       page,
        "per_page":   per_page,
        "total":      total,
        "total_pages": max(1, -(-total // per_page)),
        "records":    [r.to_dict() for r in rows],
    }


@router.post("/pay", response_model=ManualPayResponse)
async def banker_manual_pay(
    body: ManualPayRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Admin endpoint: manually trigger a one-shot USDC payment from the agent wallet.
    Requires BANKER_AGENT_ENABLED=true.
    """
    try:
        tx_hash = await BankerAgentService.pay_for_route(
            db,
            route       = body.route,
            amount_usdc = body.amount_usdc,
            to_address  = body.to_address,
            purpose     = body.purpose,
        )
    except BankerAgentConfigError as exc:
        raise HTTPException(status_code=503, detail=f"Banker Agent not configured: {exc}")
    except BankerAgentInsufficientFundsError as exc:
        raise HTTPException(status_code=402, detail=f"Insufficient funds: {exc}")
    except BankerAgentDailyLimitError as exc:
        raise HTTPException(status_code=429, detail=f"Daily limit exceeded: {exc}")
    except BankerAgentError as exc:
        raise HTTPException(status_code=500, detail=f"Payment failed: {exc}")

    return ManualPayResponse(
        status       = "confirmed",
        tx_hash      = tx_hash,
        amount_usdc  = body.amount_usdc,
        to_address   = body.to_address,
        basescan_url = f"https://basescan.org/tx/{tx_hash}",
    )


@router.post("/self-prove")
async def banker_self_prove(db: AsyncSession = Depends(get_db)):
    """
    Full end-to-end settlement proof:
    1. Pays /api/v1/x402/score with 0.10 real USDC on Base Mainnet
    2. Calls the /score endpoint with the confirmed tx hash as X-PAYMENT proof
    3. Returns the score JSON + receipt + tx hash

    This generates the exact artefacts needed to prove live settlement to Chet/PayAPI.

    Requires BANKER_AGENT_ENABLED=true and a funded wallet key in VEKLOM_AGENT_PRIVATE_KEY.
    """
    try:
        result = await BankerAgentService.self_prove(db)
    except BankerAgentConfigError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error":   "banker_not_configured",
                "message": str(exc),
                "fix":     "Set VEKLOM_AGENT_PRIVATE_KEY and BANKER_AGENT_ENABLED=true in Coolify env vars.",
            }
        )
    except BankerAgentInsufficientFundsError as exc:
        raise HTTPException(
            status_code=402,
            detail={
                "error":   "insufficient_usdc",
                "message": str(exc),
                "fix":     "Fund the agent wallet with at least 0.10 USDC on Base Mainnet.",
            }
        )
    except BankerAgentDailyLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "error":   "daily_limit_exceeded",
                "message": str(exc),
                "fix":     "Increase BANKER_AGENT_DAILY_LIMIT_USDC or wait until UTC midnight.",
            }
        )
    except BankerAgentError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error":   "payment_failed",
                "message": str(exc),
            }
        )

    return result
