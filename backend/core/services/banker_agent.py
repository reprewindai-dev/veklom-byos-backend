"""
BankerAgentService — Operator-triggered payment ledger for Veklom.

Gold-Standard Architecture:
─────────────────────────────────────────────────────────────────────────────
The Banker Agent does NOT sign or broadcast transactions. The signer is the
operator's connected Base Account in the browser, via @base-org/account SDK
(already installed in veklom-control-plane via wagmi/connectors baseAccount()).

This backend service is responsible for:
  1. Idempotency: Refuse to create two payment rows for the same job.
  2. Preparation: Create a `pending` Payment row before the frontend sends.
  3. Proof Persistence: Accept the tx_hash from the frontend, verify the Base
     receipt directly, then record confirmed settlement data.

Flow:
  1. Operator clicks "Pay" in the UI.
  2. Frontend calls POST /api/v1/banker/pay/prepare
     → Backend creates a pending Payment row, returns payment_id.
  3. Frontend submits the transaction via the Base Account wagmi provider
     (wallet_sendCalls or eth_sendTransaction).
  4. Frontend calls POST /api/v1/banker/pay/confirm with tx_hash.
     → Backend verifies the Base USDC transfer and records proof.
─────────────────────────────────────────────────────────────────────────────
"""

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class BankerAgentError(Exception):
    pass

class BankerAgentConfigError(BankerAgentError):
    pass

class BankerAgentDuplicatePaymentError(BankerAgentError):
    pass

class BankerAgentProofError(BankerAgentError):
    pass


__all__ = [
    "BankerAgentService",
    "BankerAgentError",
    "BankerAgentConfigError",
    "BankerAgentDuplicatePaymentError",
    "BankerAgentProofError",
]


BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
BASE_USDC_CONTRACT = os.getenv("BASE_USDC_CONTRACT", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _normalize_address(value: str) -> str:
    clean = str(value or "").strip().lower()
    if not clean.startswith("0x") or len(clean) != 42:
        raise BankerAgentProofError("Invalid EVM address")
    try:
        int(clean[2:], 16)
    except ValueError as exc:
        raise BankerAgentProofError("Invalid EVM address") from exc
    return clean


def _validate_tx_hash(tx_hash: str) -> str:
    clean = str(tx_hash or "").strip().lower()
    if not clean.startswith("0x") or len(clean) != 66:
        raise BankerAgentProofError("Invalid Base transaction hash")
    try:
        int(clean[2:], 16)
    except ValueError as exc:
        raise BankerAgentProofError("Invalid Base transaction hash") from exc
    return clean


def _topic_address(topic: str) -> str:
    clean = str(topic or "").lower().replace("0x", "")
    if len(clean) != 64:
        raise BankerAgentProofError("Invalid indexed address topic in Base receipt")
    return f"0x{clean[-40:]}"


async def _base_rpc(method: str, params: list[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(BASE_RPC_URL, json=payload)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise BankerAgentProofError(f"Base RPC {method} request failed") from exc

    data = response.json()
    if data.get("error"):
        message = data["error"].get("message", "unknown")
        raise BankerAgentProofError(f"Base RPC {method} error: {message}")
    return data.get("result")


async def _verify_payment_receipt(payment: Any, tx_hash: str, chain_id: int) -> dict[str, Any]:
    if int(chain_id) != BASE_CHAIN_ID:
        raise BankerAgentProofError("Banker payments must settle on Base Mainnet chain_id=8453")
    if str(payment.asset).upper() != "USDC":
        raise BankerAgentProofError("Only Base USDC banker payments are currently supported")

    checked_tx_hash = _validate_tx_hash(tx_hash)
    expected_to = _normalize_address(payment.to_address)
    expected_amount_micro = int(
        (Decimal(payment.amount) * Decimal("1000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )

    receipt = await _base_rpc("eth_getTransactionReceipt", [checked_tx_hash])
    if not receipt:
        raise BankerAgentProofError("Payment transaction was not found on Base")
    if str(receipt.get("status", "")).lower() != "0x1":
        raise BankerAgentProofError("Payment transaction did not succeed on Base")

    tx = await _base_rpc("eth_getTransactionByHash", [checked_tx_hash])
    if not tx:
        raise BankerAgentProofError("Payment transaction metadata was not found on Base")
    tx_to = _normalize_address(str(tx.get("to", "")))

    transfer_match: dict[str, Any] | None = None
    for log in receipt.get("logs") or []:
        topics = [str(topic).lower() for topic in (log.get("topics") or [])]
        if len(topics) < 3 or topics[0] != ERC20_TRANSFER_TOPIC:
            continue
        if _normalize_address(str(log.get("address", ""))) != _normalize_address(BASE_USDC_CONTRACT):
            continue

        from_addr = _topic_address(topics[1])
        to_addr = _topic_address(topics[2])
        amount_micro = int(str(log.get("data", "0x0")), 16)
        if to_addr == expected_to and amount_micro >= expected_amount_micro:
            transfer_match = {
                "from": from_addr,
                "to": to_addr,
                "amount_micro": amount_micro,
                "amount_usdc": str(Decimal(amount_micro) / Decimal("1000000")),
                "log_index": int(str(log.get("logIndex", "0x0")), 16),
            }
            break

    if not transfer_match:
        raise BankerAgentProofError("No matching Base USDC Transfer log found for recipient and amount")

    return {
        "tx_hash": checked_tx_hash,
        "chain_id": BASE_CHAIN_ID,
        "block_number": int(str(receipt.get("blockNumber", "0x0")), 16),
        "gas_used": int(str(receipt.get("gasUsed", "0x0")), 16),
        "tx_from": _normalize_address(str(tx.get("from", ""))),
        "tx_to": tx_to,
        "usdc_contract": _normalize_address(BASE_USDC_CONTRACT),
        "transfer": transfer_match,
        "basescan_url": f"https://basescan.org/tx/{checked_tx_hash}",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "proof_source": "base_rpc_receipt",
    }


# ---------------------------------------------------------------------------
# Main Service Class
# ---------------------------------------------------------------------------

class BankerAgentService:
    """
    Stateless service. All methods are classmethods.
    The banker does not hold keys. It is a ledger guardian.
    """

    @staticmethod
    def get_treasury_address() -> str:
        addr = os.environ.get("VEKLOM_TREASURY_ADDRESS", "").strip()
        if not addr or not addr.startswith("0x"):
            raise BankerAgentConfigError(
                "VEKLOM_TREASURY_ADDRESS is not configured or invalid. "
                "Set it in Coolify environment variables."
            )
        return addr

    @staticmethod
    async def prepare_payment(
        db,
        payment_object_type: str,
        payment_object_id: int,
        to_address: str,
        amount: float,
        asset: str = "USDC",
    ) -> dict:
        """
        Step 1 of the payment flow.

        Validates idempotency, enforces daily spending limits, calls PGL Gate,
        and creates a `pending` Payment row with the pre-execution certificate ID.
        Returns the payment record so the frontend knows the payment_id
        and can proceed to call the Base Account wallet provider.

        Raises BankerAgentDuplicatePaymentError if this job was already paid.
        """
        from backend.db.models.payment import Payment
        from backend.core.services.banker_pgl_guard import BankerAgentPGLGuard
        from datetime import timedelta

        treasury = BankerAgentService.get_treasury_address()
        checked_to_address = _normalize_address(to_address)
        checked_asset = str(asset or "").upper()
        if checked_asset != "USDC":
            raise BankerAgentProofError("Only Base USDC banker payments are currently supported")

        # Check for existing payment for this job
        result = await db.execute(
            select(Payment).where(
                Payment.payment_object_type == payment_object_type,
                Payment.payment_object_id == payment_object_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.status in ("confirmed", "success"):
                raise BankerAgentDuplicatePaymentError(
                    f"Payment for {payment_object_type}:{payment_object_id} "
                    f"was already settled (tx_hash={existing.tx_hash})."
                )
            if existing.status == "pending":
                # Return the existing pending row — frontend can continue
                logger.info(
                    f"[BankerAgent] Returning existing pending payment id={existing.id} "
                    f"for {payment_object_type}:{payment_object_id}"
                )
                return existing.to_dict()

        # Enforce daily spending cap (from environment or default 100.0 USDC)
        daily_limit = float(os.environ.get("BANKER_AGENT_DAILY_LIMIT_USDC", "100.0"))
        one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        tot_res = await db.execute(
            select(func.sum(Payment.amount)).where(
                Payment.from_address == treasury,
                Payment.status == "confirmed",
                Payment.settled_at >= one_day_ago
            )
        )
        # Import func dynamically in case it's not present globally
        from sqlalchemy import func
        settled_sum = Decimal(str((await db.execute(
            select(func.sum(Payment.amount)).where(
                Payment.from_address == treasury,
                Payment.status == "confirmed",
                Payment.settled_at >= one_day_ago
            )
        )).scalar() or "0.0"))

        if float(settled_sum) + amount > daily_limit:
            raise BankerAgentError(
                f"Daily spending limit of {daily_limit} USDC exceeded. "
                f"Already spent in last 24h: {settled_sum} USDC, attempting: {amount} USDC."
            )

        # Call PGL Gate — issues pre-execution certificate
        pgl_ctx = await BankerAgentPGLGuard.require(
            db=db,
            route=f"{payment_object_type}:{payment_object_id}",
            amount_usdc=amount,
            to_address=checked_to_address,
            purpose="banker_payment"
        )
        pre_cert_id = pgl_ctx.pre_execution_cert_id

        # Create new pending row with certificate ID
        new_payment = Payment(
            payment_object_type=payment_object_type,
            payment_object_id=payment_object_id,
            from_address=treasury,
            to_address=checked_to_address,
            asset=checked_asset,
            amount=Decimal(str(amount)),
            status="pending",
            pre_execution_cert_id=pre_cert_id,
        )
        db.add(new_payment)
        try:
            await db.commit()
            await db.refresh(new_payment)
        except IntegrityError:
            await db.rollback()
            raise BankerAgentDuplicatePaymentError(
                f"Concurrent payment attempt detected for "
                f"{payment_object_type}:{payment_object_id}."
            )

        logger.info(
            f"[BankerAgent] Created pending payment id={new_payment.id} "
            f"| PGL Cert: {pre_cert_id} | {amount} {asset} → {to_address}"
        )
        return new_payment.to_dict()

    @staticmethod
    async def confirm_payment(
        db,
        payment_object_type: str,
        payment_object_id: int,
        tx_hash: str,
        chain_id: int = 8453,
        block_number: Optional[int] = None,
        gas_used: Optional[int] = None,
    ) -> dict:
        """
        Step 2 of the payment flow.

        Called by the frontend after the Base Account wallet provider
        (wallet_sendCalls / eth_sendTransaction) returns a tx_hash.

        Fetches the Base receipt, verifies a successful Base USDC transfer to
        the prepared recipient for at least the prepared amount, and only then
        marks the payment as confirmed.
        """
        from backend.db.models.payment import Payment
        from backend.core.services.banker_pgl_guard import BankerAgentPGLGuard, BankerPGLContext
        from backend.core.services.banker_pgl_guard import (
            BANKER_AGENT_WORKSPACE,
            BANKER_AGENT_ACTOR_ID,
            BANKER_GENOME_HASH,
            BANKER_CONSTITUTION_HASH,
        )

        result = await db.execute(
            select(Payment).where(
                Payment.payment_object_type == payment_object_type,
                Payment.payment_object_id == payment_object_id,
            )
        )
        payment = result.scalar_one_or_none()

        if not payment:
            raise BankerAgentError(
                f"No pending payment found for {payment_object_type}:{payment_object_id}. "
                "Call /prepare first."
            )

        if payment.status in ("confirmed", "success"):
            logger.info(
                f"[BankerAgent] Payment id={payment.id} already confirmed, returning."
            )
            return payment.to_dict()

        checked_tx_hash = _validate_tx_hash(tx_hash)
        tx_result = await db.execute(
            select(Payment).where(Payment.tx_hash == checked_tx_hash)
        )
        tx_payment = tx_result.scalar_one_or_none()
        if tx_payment and tx_payment.id != payment.id:
            raise BankerAgentDuplicatePaymentError(
                f"Transaction hash {checked_tx_hash} is already attached to "
                f"payment id={tx_payment.id}."
            )

        # Reconstruct the PGL Context for attestation
        pgl_ctx = BankerPGLContext(
            pgl_identity_id=payment.pre_execution_cert_id or "",
            workspace_id=BANKER_AGENT_WORKSPACE,
            actor_id=BANKER_AGENT_ACTOR_ID,
            pre_execution_cert_id=payment.pre_execution_cert_id or "",
            genome_hash=BANKER_GENOME_HASH,
            constitution_hash=BANKER_CONSTITUTION_HASH,
            intent_hash=BankerAgentPGLGuard._build_intent_hash(
                route=f"{payment_object_type}:{payment_object_id}",
                amount_usdc=float(payment.amount),
                to_address=payment.to_address,
            )
        )

        try:
            proof = await _verify_payment_receipt(payment, checked_tx_hash, chain_id)
        except Exception as exc:
            # If verification fails, attest failure to PGL and re-raise
            if payment.pre_execution_cert_id:
                await BankerAgentPGLGuard.attest_failure(db, pgl_ctx, str(exc))
            raise

        payment.tx_hash = proof["tx_hash"]
        payment.chain_id = proof["chain_id"]
        payment.block_number = proof["block_number"]
        payment.gas_used = proof["gas_used"]
        payment.from_address = proof["transfer"]["from"]
        payment.to_address = proof["transfer"]["to"]
        payment.settled_at = datetime.now(timezone.utc)
        payment.status = "confirmed"

        # Attest success to PGL
        if payment.pre_execution_cert_id:
            await BankerAgentPGLGuard.attest_success(
                db=db,
                pgl_ctx=pgl_ctx,
                tx_hash=proof["tx_hash"],
                block_number=proof["block_number"]
            )

        await db.commit()
        await db.refresh(payment)

        logger.info(
            f"[BankerAgent] ✅ Payment id={payment.id} confirmed. "
            f"TxHash: {proof['tx_hash']} | Block: {proof['block_number']}"
        )
        return payment.to_dict()

    @staticmethod
    async def get_ledger(
        db,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[str] = None,
    ) -> dict:
        """Returns paginated payment history."""
        from backend.db.models.payment import Payment
        from sqlalchemy import select, func, desc

        q = select(Payment).order_by(desc(Payment.created_at))
        if status_filter:
            q = q.where(Payment.status == status_filter)

        count_q = select(func.count()).select_from(Payment)
        if status_filter:
            count_q = count_q.where(Payment.status == status_filter)

        from sqlalchemy import func
        total = (await db.execute(count_q)).scalar() or 0
        offset = (page - 1) * per_page
        rows = (await db.execute(q.offset(offset).limit(per_page))).scalars().all()

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, -(-total // per_page)),
            "records": [r.to_dict() for r in rows],
        }
