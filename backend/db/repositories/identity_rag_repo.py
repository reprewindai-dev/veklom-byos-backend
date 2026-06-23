from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.identity_rag import (
    GoldenRecordResponse,
    GoldenRecordFinancials,
    GoldenRecordGovernance,
    GoldenRecordIdentity,
)
from backend.db.models.pgl import PGLIdentity, Certificate, Lineage
from backend.db.models.ai import ExecLog
from backend.db.models.authority import AuthorityRun
from backend.db.models.ledger import SettlementLedger
from backend.db.repositories.settlement_repo import write_identity_rag_fee, mark_settlement_released

# Canonical Veklom treasury payee UUID – should come from settings in production.
VEKLOM_TREASURY_ID = "00000000-0000-0000-0000-76656b6c6f6d"


async def resolve_identity_golden_record(
    db: AsyncSession,
    agent_id: str | None,
    public_key: str | None,
    requester_provider_id: str,
    resolution_fee_minor: int,
    payment_proof,
) -> GoldenRecordResponse | None:
    # ── 1. Resolve PGLIdentity ──────────────────────────────────────────────
    stmt = select(PGLIdentity)
    if agent_id:
        stmt = stmt.where(PGLIdentity.id == agent_id)
    else:
        stmt = stmt.where(PGLIdentity.public_key == public_key)

    pgl = await db.scalar(stmt)
    if pgl is None:
        return None

    # ── 2. Deterministic survivorship aggregations ──────────────────────────
    #   Identity root: PGLIdentity is canonical.
    certificate_count = await db.scalar(
        select(func.count()).select_from(Certificate).where(Certificate.pgl_identity_id == pgl.id)
    )
    lineage_depth = await db.scalar(
        select(func.count()).select_from(Lineage).where(Lineage.pgl_identity_id == pgl.id)
    )

    #   Financial truth: SettlementLedger is canonical for volume and reliability.
    total_x402_volume_minor = await db.scalar(
        select(func.coalesce(func.sum(SettlementLedger.locked_amount_minor), 0))
        .where(SettlementLedger.payee_id == pgl.id)
    )
    released_volume_minor = await db.scalar(
        select(func.coalesce(func.sum(SettlementLedger.released_amount_minor), 0))
        .where(SettlementLedger.payee_id == pgl.id)
    )
    rejected_settlement_count = await db.scalar(
        select(func.count()).select_from(SettlementLedger).where(
            SettlementLedger.payee_id == pgl.id,
            SettlementLedger.settlement_state.in_(["rejected", "failed"]),
        )
    )
    total_settlement_count = await db.scalar(
        select(func.count()).select_from(SettlementLedger).where(SettlementLedger.payee_id == pgl.id)
    )

    #   Governance truth: AuthorityRun + PGLLedgerEvent are canonical.
    try:
        from backend.db.models.pgl import PGLLedgerEvent
        quarantine_count = await db.scalar(
            select(func.count()).select_from(PGLLedgerEvent).where(
                PGLLedgerEvent.pgl_identity_id == pgl.id,
                PGLLedgerEvent.event_type == "quarantine",
            )
        )
        kleros_dispute_count = await db.scalar(
            select(func.count()).select_from(PGLLedgerEvent).where(
                PGLLedgerEvent.pgl_identity_id == pgl.id,
                PGLLedgerEvent.event_type == "kleros_dispute",
            )
        )
    except Exception:
        quarantine_count = 0
        kleros_dispute_count = 0

    total_authority_runs = await db.scalar(
        select(func.count()).select_from(AuthorityRun).where(AuthorityRun.agent_id == pgl.id)
    )
    denied_runs = await db.scalar(
        select(func.count()).select_from(AuthorityRun).where(
            AuthorityRun.agent_id == pgl.id,
            AuthorityRun.final_resolution == "denied",
        )
    )

    #   Derived trust: computed from canonical sources, never stored as mutable truth.
    bounce_rate = 0.0
    if total_settlement_count:
        bounce_rate = float(rejected_settlement_count or 0) / float(total_settlement_count)

    # ── 3. Fee recording via canonical settlement path ─────────────────────
    #   The payment_proof is validated upstream by require_payment_proof.
    #   We only persist the ledger row here; we never trust the request body
    #   to claim payment state.
    proof_hash = None
    tenant_id_val = None
    workspace_id_val = None
    if isinstance(payment_proof, dict):
        proof_hash = payment_proof.get("payment_proof_hash") or payment_proof.get("proof_hash")
        tenant_id_val = payment_proof.get("tenant_id")
        workspace_id_val = payment_proof.get("workspace_id")

    import uuid as _uuid
    tenant_id = _uuid.UUID(str(tenant_id_val)) if tenant_id_val else _uuid.UUID("00000000-0000-0000-0000-000000000001")
    workspace_id = _uuid.UUID(str(workspace_id_val)) if workspace_id_val else None
    try:
        payer_uuid = _uuid.UUID(str(requester_provider_id))
    except Exception:
        payer_uuid = _uuid.uuid5(_uuid.NAMESPACE_URL, str(requester_provider_id))

    agent_lookup_key = str(agent_id or public_key or pgl.id)
    resolution_payload = {"pgl_identity_id": str(pgl.id)}

    ledger_row = await write_identity_rag_fee(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        requester_provider_id=payer_uuid,
        veklom_payee_id=_uuid.UUID(VEKLOM_TREASURY_ID),
        payment_proof_hash=proof_hash,
        agent_lookup_key=agent_lookup_key,
        resolution_payload=resolution_payload,
        amount_minor=resolution_fee_minor,
    )

    # Mark released immediately – service was fulfilled.
    await mark_settlement_released(
        db,
        ledger_row.id,
        metadata_patch={"pgl_identity_id": str(pgl.id)},
    )

    # ── 4. Build and return the Golden Record ──────────────────────────────
    return GoldenRecordResponse(
        pgl_identity=GoldenRecordIdentity(
            pgl_identity_id=str(pgl.id),
            public_key=getattr(pgl, "public_key", None),
            lineage_depth=int(lineage_depth or 0),
            certificate_count=int(certificate_count or 0),
            created_at=getattr(pgl, "created_at", None),
        ),
        financials=GoldenRecordFinancials(
            total_x402_volume_minor=int(total_x402_volume_minor or 0),
            released_volume_minor=int(released_volume_minor or 0),
            rejected_settlement_count=int(rejected_settlement_count or 0),
            bounce_rate=bounce_rate,
        ),
        governance=GoldenRecordGovernance(
            total_authority_runs=int(total_authority_runs or 0),
            denied_runs=int(denied_runs or 0),
            quarantine_count=int(quarantine_count or 0),
            kleros_dispute_count=int(kleros_dispute_count or 0),
        ),
        trust_summary={
            "has_quarantine_history": int(quarantine_count or 0) > 0,
            "has_kleros_disputes": int(kleros_dispute_count or 0) > 0,
            "bounce_rate_band": "high" if bounce_rate >= 0.20 else "normal",
        },
        source_counts={
            "certificates": int(certificate_count or 0),
            "lineage_events": int(lineage_depth or 0),
            "authority_runs": int(total_authority_runs or 0),
            "settlements": int(total_settlement_count or 0),
        },
        generated_at=datetime.now(timezone.utc),
        resolution_fee_minor=resolution_fee_minor,
        charged_to_provider_id=requester_provider_id,
    )
