"""
A402 Atomic Service Channels (ASCs) Settlement Service.
Binds service execution directly to payment releases using TEE-assisted logic.
Aligned with SQL migration 003_settlement_ledger.sql.
"""

import uuid
import logging
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models.ledger import SettlementLedger, SettlementStatus
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class SettlementService:
    """
    Manages A402 ASC transaction flows across four phases:
    1. Initialization (Locking funds)
    2. Execution (Conditional commitment)
    3. Cryptographic Binding (Verifying receipt)
    4. Aggregated Settlement (Releasing funds)
    """

    @staticmethod
    async def initialize_channel(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        payer_id: uuid.UUID,
        payee_id: uuid.UUID,
        protected_route: str,
        service_name: str,
        amount_minor: int,
        dedupe_key: str,
        currency: str = "USDC"
    ) -> SettlementLedger:
        """Phase 1: Channel Initialization."""
        # execution_hash is generated here as a conditional commitment
        execution_hash = hashlib.sha256(f"{tenant_id}:{dedupe_key}:{datetime.now(timezone.utc)}".encode()).hexdigest()

        ledger_entry = SettlementLedger(
            id=uuid.uuid4(),
            tenant_id=str(tenant_id),
            payer_id=str(payer_id),
            payee_id=str(payee_id),
            protected_route=protected_route,
            service_name=service_name,
            locked_amount_minor=amount_minor,
            quoted_amount_minor=amount_minor,
            currency_code=currency,
            status=SettlementStatus.PENDING,
            execution_hash=execution_hash,
            dedupe_key=dedupe_key,
            idempotency_key=f"asc_{uuid.uuid4().hex[:16]}"
        )
        db.add(ledger_entry)
        await db.commit()
        return ledger_entry

    @staticmethod
    async def release_settlement(
        db: AsyncSession,
        execution_hash: str,
        released_amount_minor: int,
        tee_signature: str = ""
    ) -> bool:
        """Phase 3 & 4: Cryptographic Binding & Aggregated Settlement."""
        stmt = select(SettlementLedger).where(SettlementLedger.execution_hash == execution_hash)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry:
            logger.error(f"Settlement record with hash {execution_hash} not found.")
            return False

        if entry.status == SettlementStatus.SETTLED:
            logger.warning(f"Settlement with hash {execution_hash} already processed.")
            return True

        # Verify TEE-assisted signature (Software implementation using HMAC as proxy)
        if tee_signature:
            expected_sig = hmac.new(
                settings.JWT_SECRET_KEY.encode(),
                execution_hash.encode(),
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(tee_signature, expected_sig):
                logger.error(f"Invalid TEE signature for settlement {entry.id}.")
                entry.status = SettlementStatus.FAILED
                entry.failure_reason = "INVALID_TEE_SIGNATURE"
                await db.commit()
                return False

        if released_amount_minor > entry.locked_amount_minor:
            logger.error(f"Release amount {released_amount_minor} exceeds locked amount {entry.locked_amount_minor}.")
            return False

        # Update entry
        entry.released_amount_minor = released_amount_minor
        entry.settlement_tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"[:128]
        entry.status = SettlementStatus.SETTLED
        entry.settled_at = datetime.now(timezone.utc)
        entry.fulfilled_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info(f"ASC Settlement {entry.id} released for {released_amount_minor} minor units.")
        return True

    @staticmethod
    async def batch_settle(
        db: AsyncSession,
        tenant_id: str
    ) -> List[uuid.UUID]:
        """Aggregates multiple ASC settlements into a single logical batch (Reducing costs)."""
        stmt = select(SettlementLedger).where(
            SettlementLedger.tenant_id == tenant_id,
            SettlementLedger.status == SettlementStatus.PENDING
        )
        result = await db.execute(stmt)
        pending_entries = result.scalars().all()

        processed_ids = []
        for entry in pending_entries:
            # Simulate aggregation to L2 gateway
            entry.status = SettlementStatus.SETTLED
            entry.settled_at = datetime.now(timezone.utc)
            processed_ids.append(entry.id)

        await db.commit()
        return processed_ids
