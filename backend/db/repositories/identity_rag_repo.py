from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.authority import AuthorityRun
from backend.db.models.ledger import SettlementLedger
from backend.db.models.lineage import BirthCertificate
from backend.db.models.pgl import PGLCertificate, PGLIdentity
from backend.db.repositories.settlement_repo import mark_settlement_released, write_identity_rag_fee
from backend.schemas.identity_rag import (
    GoldenRecordFinancials,
    GoldenRecordGovernance,
    GoldenRecordIdentity,
    GoldenRecordResponse,
)

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
        select(func.count()).select_from(PGLCertificate).where(PGLCertificate.pgl_identity_id == pgl.id)
    )
    lineage_depth = await db.scalar(
        select(func.count()).select_from(BirthCertificate).where(BirthCertificate.pgl_identity_id == pgl.id)
    )

    #   Financial truth: SettlementLedger is canonical for volume and reliability.
    # ⚡ Bolt Optimization: Batch settlement ledger aggregation into a single query
    fin_row = (await db.execute(
        select(
            func.coalesce(func.sum(SettlementLedger.locked_amount_minor), 0),
            func.coalesce(func.sum(SettlementLedger.released_amount_minor), 0),
            func.coalesce(func.sum(case((SettlementLedger.settlement_state.in_(["rejected", "failed"]), 1), else_=0)), 0),
            func.count()
        ).select_from(SettlementLedger).where(SettlementLedger.payee_id == pgl.id)
    )).first()

    total_x402_volume_minor, released_volume_minor, rejected_settlement_count, total_settlement_count = fin_row or (0, 0, 0, 0)

    #   Governance truth: AuthorityRun + PGLLedgerEvent are canonical.
    try:
        from backend.db.models.pgl import PGLLedgerEvent
        # ⚡ Bolt Optimization: Batch event count queries
        events_row = (await db.execute(
            select(
                func.coalesce(func.sum(case((PGLLedgerEvent.event_type == "quarantine", 1), else_=0)), 0),
                func.coalesce(func.sum(case((PGLLedgerEvent.event_type == "kleros_dispute", 1), else_=0)), 0),
            ).select_from(PGLLedgerEvent).where(PGLLedgerEvent.pgl_identity_id == pgl.id)
        )).first()
        quarantine_count, kleros_dispute_count = events_row or (0, 0)
    except Exception:
        quarantine_count = 0
        kleros_dispute_count = 0

    # ⚡ Bolt Optimization: Batch authority run count queries
    auth_row = (await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((AuthorityRun.final_resolution == "denied", 1), else_=0)), 0)
        ).select_from(AuthorityRun).where(AuthorityRun.agent_id == pgl.id)
    )).first()
    total_authority_runs, denied_runs = auth_row or (0, 0)

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
