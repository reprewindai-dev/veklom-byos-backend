from __future__ import annotations

from decimal import Decimal
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.ledger import SettlementLedger, SettlementStatus


class SettlementLedgerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[SettlementLedger]:
        stmt = select(SettlementLedger).where(
            SettlementLedger.idempotency_key == idempotency_key
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_fee_entry(
        self,
        *,
        tenant_id: str,
        provider: str,
        fee_type: str,
        amount: int,
        currency: str,
        idempotency_key: str,
        execution_id: Optional[str] = None,
        authority_run_id: Optional[str] = None,
        payment_proof_id: Optional[str] = None,
        external_payment_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> SettlementLedger:
        existing = await self.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        row = SettlementLedger(
            tenant_id=tenant_id,
            provider=provider,
            fee_type=fee_type,
            amount=amount,
            currency=currency,
            status=SettlementStatus.PENDING,
            idempotency_key=idempotency_key,
            execution_id=execution_id,
            authority_run_id=authority_run_id,
            payment_proof_id=payment_proof_id,
            external_payment_id=external_payment_id,
            metadata_json=metadata or {},
        )
        self.db.add(row)

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing
            raise

        return row

    async def mark_settled(
        self,
        *,
        ledger_id: str,
        settlement_tx_hash: Optional[str] = None,
        external_payment_id: Optional[str] = None,
    ) -> SettlementLedger:
        row = await self.db.get(SettlementLedger, ledger_id)
        if not row:
            raise ValueError(f"SettlementLedger row not found: {ledger_id}")

        row.status = SettlementStatus.SETTLED
        row.settlement_tx_hash = settlement_tx_hash
        row.external_payment_id = external_payment_id or row.external_payment_id
        await self.db.flush()
        return row

    async def mark_failed(
        self,
        *,
        ledger_id: str,
        failure_code: str,
        failure_reason: Optional[str] = None,
    ) -> SettlementLedger:
        row = await self.db.get(SettlementLedger, ledger_id)
        if not row:
            raise ValueError(f"SettlementLedger row not found: {ledger_id}")

        row.status = SettlementStatus.FAILED
        row.failure_code = failure_code
        row.failure_reason = failure_reason
        await self.db.flush()
        return row

    async def get_for_execution(self, execution_id: str) -> Sequence[SettlementLedger]:
        stmt = select(SettlementLedger).where(
            SettlementLedger.execution_id == execution_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_unsettled(self, tenant_id: Optional[str] = None) -> Sequence[SettlementLedger]:
        stmt = select(SettlementLedger).where(
            SettlementLedger.status == SettlementStatus.PENDING
        )
        if tenant_id:
            stmt = stmt.where(SettlementLedger.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
