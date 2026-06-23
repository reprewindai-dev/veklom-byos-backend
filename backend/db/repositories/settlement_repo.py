from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.ledger import SettlementLedger, SettlementState


@dataclass
class SettlementWriteContext:
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID | None
    payer_id: uuid.UUID
    payee_id: uuid.UUID
    protected_route: str
    service_name: str
    amount_minor: int
    currency_code: str
    network_id: str | None
    payment_proof_hash: str | None
    dedupe_key: str
    request_fingerprint: str | None
    execution_hash: str
    asc_channel_id: str | None = None
    metadata_json: dict | None = None


def build_execution_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


async def create_or_get_settlement_lock(
    db: AsyncSession,
    ctx: SettlementWriteContext,
) -> SettlementLedger:
    existing = await db.scalar(
        select(SettlementLedger).where(
            SettlementLedger.tenant_id == ctx.tenant_id,
            SettlementLedger.dedupe_key == ctx.dedupe_key,
        )
    )
    if existing is not None:
        if ctx.request_fingerprint and existing.request_fingerprint and existing.request_fingerprint != ctx.request_fingerprint:
            raise ValueError("dedupe_key reuse with different request fingerprint")
        return existing

    row = SettlementLedger(
        tenant_id=ctx.tenant_id,
        workspace_id=ctx.workspace_id,
        payer_id=ctx.payer_id,
        payee_id=ctx.payee_id,
        asc_channel_id=ctx.asc_channel_id,
        protected_route=ctx.protected_route,
        service_name=ctx.service_name,
        currency_code=ctx.currency_code,
        network_id=ctx.network_id,
        quoted_amount_minor=ctx.amount_minor,
        locked_amount_minor=ctx.amount_minor,
        released_amount_minor=0,
        payment_proof_hash=ctx.payment_proof_hash,
        execution_hash=ctx.execution_hash,
        settlement_state=SettlementState.locked,
        dedupe_key=ctx.dedupe_key,
        request_fingerprint=ctx.request_fingerprint,
        metadata_json=ctx.metadata_json,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(SettlementLedger).where(
                SettlementLedger.tenant_id == ctx.tenant_id,
                SettlementLedger.dedupe_key == ctx.dedupe_key,
            )
        )
        if existing is None:
            raise
        return existing

    return row


async def mark_settlement_released(
    db: AsyncSession,
    ledger_id,
    *,
    released_amount_minor: int | None = None,
    metadata_patch: dict | None = None,
) -> SettlementLedger:
    row = await db.get(SettlementLedger, ledger_id, with_for_update=True)
    if row is None:
        raise ValueError("settlement row not found")

    if row.settlement_state in {SettlementState.released, SettlementState.refunded}:
        return row

    if row.settlement_state in {SettlementState.rejected, SettlementState.failed}:
        raise ValueError("cannot release a rejected or failed settlement")

    release_amount = released_amount_minor if released_amount_minor is not None else row.locked_amount_minor
    if release_amount < 0 or release_amount > row.locked_amount_minor:
        raise ValueError("invalid released_amount_minor")

    row.released_amount_minor = release_amount
    row.settlement_state = SettlementState.released
    row.fulfilled_at = row.fulfilled_at or datetime.now(timezone.utc)
    row.settled_at = datetime.now(timezone.utc)
    if metadata_patch:
        row.metadata_json = {**(row.metadata_json or {}), **metadata_patch}

    await db.flush()
    return row


async def mark_settlement_rejected(
    db: AsyncSession,
    ledger_id,
    *,
    reason: str,
    state: SettlementState = SettlementState.rejected,
    metadata_patch: dict | None = None,
) -> SettlementLedger:
    row = await db.get(SettlementLedger, ledger_id, with_for_update=True)
    if row is None:
        raise ValueError("settlement row not found")

    if row.settlement_state in {SettlementState.released, SettlementState.refunded}:
        raise ValueError("cannot reject a released/refunded settlement")

    row.settlement_state = state
    row.failure_reason = reason
    row.settled_at = datetime.now(timezone.utc)
    if metadata_patch:
        row.metadata_json = {**(row.metadata_json or {}), **metadata_patch}

    await db.flush()
    return row


async def write_identity_rag_fee(
    db: AsyncSession,
    *,
    tenant_id,
    workspace_id,
    requester_provider_id,
    veklom_payee_id,
    payment_proof_hash,
    agent_lookup_key: str,
    resolution_payload: dict,
    amount_minor: int = 1_000_000,
) -> SettlementLedger:
    execution_hash = build_execution_hash(
        {
            "service": "identity_rag.resolve",
            "agent_lookup_key": agent_lookup_key,
            "resolution_payload": resolution_payload,
            "amount_minor": amount_minor,
        }
    )

    ctx = SettlementWriteContext(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        payer_id=requester_provider_id,
        payee_id=veklom_payee_id,
        protected_route="/api/v1/pgl/identity-rag/resolve",
        service_name="identity_rag.resolve",
        amount_minor=amount_minor,
        currency_code="USDC",
        network_id="base",
        payment_proof_hash=payment_proof_hash,
        dedupe_key=f"identity-rag:{requester_provider_id}:{agent_lookup_key}:{amount_minor}",
        request_fingerprint=build_execution_hash({"agent_lookup_key": agent_lookup_key, "amount_minor": amount_minor}),
        execution_hash=execution_hash,
        metadata_json={
            "agent_lookup_key": agent_lookup_key,
            "source": "identity_rag",
        },
    )

    return await create_or_get_settlement_lock(db, ctx)


async def write_capi_compile_fee(
    db: AsyncSession,
    *,
    tenant_id,
    workspace_id,
    requester_provider_id,
    veklom_payee_id,
    payment_proof_hash,
    agent_id: str,
    policy_bundle_hash: str,
    amount_minor: int = 50_000_000,
) -> SettlementLedger:
    execution_hash = build_execution_hash(
        {
            "service": "capi.compile",
            "agent_id": agent_id,
            "policy_bundle_hash": policy_bundle_hash,
            "amount_minor": amount_minor,
        }
    )

    ctx = SettlementWriteContext(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        payer_id=requester_provider_id,
        payee_id=veklom_payee_id,
        protected_route="/api/v1/governed/capi/compile",
        service_name="capi.compile",
        amount_minor=amount_minor,
        currency_code="USDC",
        network_id="base",
        payment_proof_hash=payment_proof_hash,
        dedupe_key=f"capi:{requester_provider_id}:{agent_id}:{policy_bundle_hash}",
        request_fingerprint=build_execution_hash({"agent_id": agent_id, "policy_bundle_hash": policy_bundle_hash}),
        execution_hash=execution_hash,
        metadata_json={
            "agent_id": agent_id,
            "policy_bundle_hash": policy_bundle_hash,
            "source": "capi",
        },
    )

    return await create_or_get_settlement_lock(db, ctx)
