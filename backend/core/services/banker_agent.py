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
  3. Proof Persistence: Accept the tx_hash from the frontend and record
     confirmed settlement data (block_number, gas_used, settled_at).

Flow:
  1. Operator clicks "Pay" in the UI.
  2. Frontend calls POST /api/v1/banker/pay/prepare
     → Backend creates a pending Payment row, returns payment_id.
  3. Frontend submits the transaction via the Base Account wagmi provider
     (wallet_sendCalls or eth_sendTransaction).
  4. Frontend calls POST /api/v1/banker/pay/confirm with tx_hash + metadata.
     → Backend updates the row to status=confirmed and records proof.
─────────────────────────────────────────────────────────────────────────────
"""

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

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


__all__ = [
    "BankerAgentService",
    "BankerAgentError",
    "BankerAgentConfigError",
    "BankerAgentDuplicatePaymentError",
]


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

        Validates idempotency and creates a `pending` Payment row.
        Returns the payment record so the frontend knows the payment_id
        and can proceed to call the Base Account wallet provider.

        Raises BankerAgentDuplicatePaymentError if this job was already paid.
        """
        from backend.db.models.payment import Payment

        treasury = BankerAgentService.get_treasury_address()

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

        # Create new pending row
        new_payment = Payment(
            payment_object_type=payment_object_type,
            payment_object_id=payment_object_id,
            from_address=treasury,
            to_address=to_address,
            asset=asset,
            amount=Decimal(str(amount)),
            status="pending",
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
            f"| {amount} {asset} → {to_address}"
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
        (wallet_sendCalls / eth_sendTransaction) returns a confirmed tx_hash.

        Records the on-chain settlement proof and marks the payment as confirmed.
        """
        from backend.db.models.payment import Payment

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

        payment.tx_hash = tx_hash
        payment.chain_id = chain_id
        payment.block_number = block_number
        payment.gas_used = gas_used
        payment.settled_at = datetime.now(timezone.utc)
        payment.status = "confirmed"

        await db.commit()
        await db.refresh(payment)

        logger.info(
            f"[BankerAgent] ✅ Payment id={payment.id} confirmed. "
            f"TxHash: {tx_hash} | Block: {block_number}"
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
