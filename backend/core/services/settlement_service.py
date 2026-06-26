"""
A402 Atomic Service Channels (ASCs) Settlement Service.
Binds service execution directly to payment releases using TEE-assisted logic.
Follows the 4-phase flow: Lock, Execute, Bind, Settle.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models.ledger import SettlementLedger, SettlementStatus

logger = logging.getLogger(__name__)

class SettlementService:
    """
    Manages A402 ASC transaction flows across four phases:
    1. Lock (Initialization/Holding funds)
    2. Execute (Conditional commitment via provider)
    3. Bind (Cryptographic evidence/receipt verification)
    4. Settle (Aggregated/Finalized release)
    """

    @staticmethod
    async def initialize_channel(
        db: AsyncSession,
        tenant_id: str,
        provider: str,
        fee_type: str,
        amount: int,
        currency: str = "USDC",
        execution_id: Optional[str] = None
    ) -> SettlementLedger:
        """Phase 1: Lock - Initialize channel and hold funds."""
        ledger_entry = SettlementLedger(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider=provider,
            fee_type=fee_type,
            amount=amount,
            currency=currency,
            status=SettlementStatus.PENDING,
            idempotency_key=f"lock_{uuid.uuid4().hex[:16]}",
            execution_id=execution_id
        )
        db.add(ledger_entry)
        await db.commit()
        logger.info(f"Phase 1 (Lock): Channel {ledger_entry.id} initialized for {amount} {currency}")
        return ledger_entry

    @staticmethod
    async def record_execution(
        db: AsyncSession,
        ledger_id: uuid.UUID,
        authority_run_id: str
    ) -> bool:
        """Phase 2: Execute - Record the start of execution/conditional commitment."""
        stmt = select(SettlementLedger).where(SettlementLedger.id == ledger_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry:
            return False

        entry.authority_run_id = authority_run_id
        await db.commit()
        logger.info(f"Phase 2 (Execute): Recorded execution {authority_run_id} for channel {ledger_id}")
        return True

    @staticmethod
    async def bind_execution(
        db: AsyncSession,
        ledger_id: uuid.UUID,
        execution_hash: str,
        payment_proof_id: Optional[str] = None
    ) -> bool:
        """Phase 3: Bind - Verify cryptographic evidence/receipt and bind to payment."""
        stmt = select(SettlementLedger).where(SettlementLedger.id == ledger_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry or entry.status != SettlementStatus.PENDING:
            return False

        # In production, this would involve verifying a TEE signature or ZK proof
        if not execution_hash or len(execution_hash) < 32:
            logger.error(f"Invalid execution hash for binding {ledger_id}")
            entry.status = SettlementStatus.FAILED
            entry.failure_reason = "INVALID_BINDING_EVIDENCE"
            await db.commit()
            return False

        entry.payment_proof_id = payment_proof_id
        # We don't settle yet, just bind the evidence
        entry.metadata_json = entry.metadata_json or {}
        entry.metadata_json["execution_hash"] = execution_hash
        entry.metadata_json["bound_at"] = datetime.now(timezone.utc).isoformat()

        await db.commit()
        logger.info(f"Phase 3 (Bind): Execution bound for channel {ledger_id} with hash {execution_hash[:10]}...")
        return True

    @staticmethod
    async def finalize_settlement(
        db: AsyncSession,
        ledger_id: uuid.UUID,
        released_amount: int,
        external_tx_id: Optional[str] = None
    ) -> bool:
        """Phase 4: Settle - Release funds based on binding."""
        stmt = select(SettlementLedger).where(SettlementLedger.id == ledger_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry or entry.status == SettlementStatus.SETTLED:
            return False

        # Verify binding exists
        if not entry.metadata_json or "execution_hash" not in entry.metadata_json:
            logger.error(f"Cannot settle unbound channel {ledger_id}")
            return False

        if released_amount > entry.amount:
            logger.error(f"Release amount {released_amount} exceeds locked amount {entry.amount}")
            return False

        entry.status = SettlementStatus.SETTLED
        entry.external_payment_id = external_tx_id
        entry.settlement_tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"[:128]
        entry.updated_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info(f"Phase 4 (Settle): Channel {ledger_id} finalized. Released {released_amount} {entry.currency}")
        return True

    @staticmethod
    async def batch_settle(
        db: AsyncSession,
        tenant_id: str
    ) -> List[uuid.UUID]:
        """Aggregates multiple ASC settlements into a single logical batch."""
        stmt = select(SettlementLedger).where(
            SettlementLedger.tenant_id == tenant_id,
            SettlementLedger.status == SettlementStatus.PENDING
        )
        result = await db.execute(stmt)
        pending_entries = result.scalars().all()

        processed_ids = []
        for entry in pending_entries:
            # Only settle if bound
            if entry.metadata_json and "execution_hash" in entry.metadata_json:
                entry.status = SettlementStatus.SETTLED
                processed_ids.append(entry.id)

        await db.commit()
        return processed_ids
