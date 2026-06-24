from __future__ import annotations

"""Canonical SettlementLedgerRepository.

This is the **single source of truth** for all fee persistence.  No other
module is permitted to instantiate or write ``SettlementLedger`` rows
directly; all callers must go through this class.

Idempotency contract
--------------------
The database enforces a unique constraint on ``idempotency_key``.  The
``create_fee_entry`` method exploits this as a deterministic upsert:

1. INSERT via ``db.flush()`` inside a SAVEPOINT.
2. On ``IntegrityError`` (duplicate key), roll back **only the savepoint**
   so the outer transaction remains healthy.
3. Re-fetch and return the existing row.

This pattern is safe under concurrent requests because the constraint
guarantee comes from Postgres, not from application-level locking.

State machine
-------------
``PENDING → SETTLED``  via :meth:`mark_settled`
``PENDING → FAILED``   via :meth:`mark_failed`

Terminal states cannot be re-transitioned; attempting to do so raises
``ValueError`` with a descriptive message.
"""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.ledger import SettlementLedger, SettlementStatus

_TERMINAL_STATES = {SettlementStatus.SETTLED, SettlementStatus.FAILED}


class SettlementLedgerRepository:
    """Repository for :class:`~backend.db.models.ledger.SettlementLedger`.

    Accepts an open :class:`sqlalchemy.ext.asyncio.AsyncSession`; the
    caller is responsible for committing or rolling back the outer
    transaction.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ──────────────────────────────────────────────────────────────────
    # Write helpers
    # ──────────────────────────────────────────────────────────────────

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
        """Insert a new fee entry or return the existing one.

        Uses a nested SAVEPOINT so an ``IntegrityError`` on the unique
        ``idempotency_key`` constraint only rolls back the inner
        savepoint, leaving the caller's outer transaction intact.

        Returns the existing row unchanged when the key already exists
        (idempotent replay is safe).
        """
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
            # Use a nested transaction (SAVEPOINT) so the outer session
            # is not poisoned on a duplicate-key collision.
            async with self.db.begin_nested():
                await self.db.flush([row])
        except IntegrityError:
            # Duplicate idempotency_key – fetch and return the winner.
            existing = await self.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing
            # Should never reach here; re-raise if the constraint that
            # triggered the error is not the idempotency_key uniqueness.
            raise

        return row

    async def mark_settled(
        self,
        *,
        ledger_id: str,
        settlement_tx_hash: Optional[str] = None,
        external_payment_id: Optional[str] = None,
    ) -> SettlementLedger:
        """Transition a PENDING row to SETTLED.

        Raises
        ------
        ValueError
            If the row does not exist, or is already in a terminal state.
        """
        row = await self._get_or_raise(ledger_id)
        if row.status in _TERMINAL_STATES:
            raise ValueError(
                f"SettlementLedger {ledger_id} is already {row.status.value}; "
                "cannot transition to SETTLED."
            )
        row.status = SettlementStatus.SETTLED
        if settlement_tx_hash is not None:
            row.settlement_tx_hash = settlement_tx_hash
        if external_payment_id is not None:
            row.external_payment_id = external_payment_id
        await self.db.flush()
        return row

    async def mark_failed(
        self,
        *,
        ledger_id: str,
        failure_code: str,
        failure_reason: Optional[str] = None,
    ) -> SettlementLedger:
        """Transition a PENDING row to FAILED.

        Raises
        ------
        ValueError
            If the row does not exist, or is already in a terminal state.
        """
        row = await self._get_or_raise(ledger_id)
        if row.status in _TERMINAL_STATES:
            raise ValueError(
                f"SettlementLedger {ledger_id} is already {row.status.value}; "
                "cannot transition to FAILED."
            )
        row.status = SettlementStatus.FAILED
        row.failure_code = failure_code
        row.failure_reason = failure_reason
        await self.db.flush()
        return row

    # ──────────────────────────────────────────────────────────────────
    # Read helpers
    # ──────────────────────────────────────────────────────────────────

    async def get_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[SettlementLedger]:
        """Return the row matching ``idempotency_key``, or ``None``."""
        stmt = select(SettlementLedger).where(
            SettlementLedger.idempotency_key == idempotency_key
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_execution(
        self, execution_id: str, *, tenant_id: Optional[str] = None
    ) -> Sequence[SettlementLedger]:
        """Return all ledger rows for a given execution, optionally filtered
        by ``tenant_id`` for cross-tenant safety."""
        stmt = select(SettlementLedger).where(
            SettlementLedger.execution_id == execution_id
        )
        if tenant_id is not None:
            stmt = stmt.where(SettlementLedger.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_unsettled(
        self,
        tenant_id: Optional[str] = None,
        *,
        limit: int = 500,
    ) -> Sequence[SettlementLedger]:
        """Return PENDING rows ordered oldest-first (natural settlement
        order).  Use ``tenant_id`` to scope to a single tenant.

        Parameters
        ----------
        limit:
            Safety cap to prevent runaway scans; defaults to 500.
        """
        stmt = (
            select(SettlementLedger)
            .where(SettlementLedger.status == SettlementStatus.PENDING)
            .order_by(SettlementLedger.created_at.asc())
            .limit(limit)
        )
        if tenant_id is not None:
            stmt = stmt.where(SettlementLedger.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    async def _get_or_raise(self, ledger_id: str) -> SettlementLedger:
        row = await self.db.get(SettlementLedger, ledger_id)
        if row is None:
            raise ValueError(f"SettlementLedger row not found: {ledger_id}")
        return row
