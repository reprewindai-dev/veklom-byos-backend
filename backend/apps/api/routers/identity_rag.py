"""identity_rag router – governs Identity-RAG fee metering.

Service boundary
----------------
This router is responsible for validating the incoming request and
computing the deterministic idempotency key.  It then delegates **all**
fee persistence to :class:`SettlementLedgerRepository`.

No ``SettlementLedger`` rows are written directly in this file.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.db.repositories.settlement_repo import SettlementLedgerRepository

router = APIRouter(prefix="/identity-rag", tags=["identity-rag"])


def _build_idempotency_key(
    tenant_id: str,
    execution_id: str,
    fee_type: str,
    provider: str,
) -> str:
    """Derive a deterministic idempotency key from the four core dimensions.

    Using SHA-256 (truncated to 64 hex chars) keeps the key compact while
    making accidental collisions across different (tenant, execution) pairs
    effectively impossible.
    """
    raw = f"{tenant_id}:{execution_id}:{fee_type}:{provider}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


@router.post("/fee", status_code=status.HTTP_201_CREATED)
async def record_identity_rag_fee(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: str,
    execution_id: str,
    provider: str = "veklom",
    fee_type: str = "identity_rag",
    amount: int,
    currency: str = "USDC",
    authority_run_id: Optional[str] = None,
) -> dict:
    """Record a metered fee for an Identity-RAG execution.

    Idempotent: replaying the same (tenant_id, execution_id, fee_type,
    provider) returns the existing ledger row with HTTP 201 (the caller
    cannot distinguish new from replay at this endpoint – that is the
    point).
    """
    idempotency_key = _build_idempotency_key(
        tenant_id=tenant_id,
        execution_id=execution_id,
        fee_type=fee_type,
        provider=provider,
    )

    repo = SettlementLedgerRepository(db)
    row = await repo.create_fee_entry(
        tenant_id=tenant_id,
        provider=provider,
        fee_type=fee_type,
        amount=amount,
        currency=currency,
        idempotency_key=idempotency_key,
        execution_id=execution_id,
        authority_run_id=authority_run_id,
    )
    await db.commit()

    return {
        "ledger_id": str(row.id),
        "idempotency_key": row.idempotency_key,
        "status": row.status.value,
        "amount": row.amount,
        "currency": row.currency,
    }
