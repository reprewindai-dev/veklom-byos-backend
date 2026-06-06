"""Genome (PGL) read surface — /api/v1/genome/*.

The identity inner engine made visible: PGL certificates, the hash-chained
life ledger, and chain verification.  All workspace-scoped and read-only here;
writes happen inside the governed orchestrator (commit/attest/rollback).

No fabrication: when a workspace has no PGL activity yet, endpoints return empty
lists with an explicit reason so the UI shows an honest empty state.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.pgl import PGLCertificate, PGLLedgerEvent
from backend.services.pgl_client import PGLClient

router = APIRouter(prefix="/genome", tags=["Genome (PGL)"])


def _ws(user) -> str:
    return user.workspace_id or "default"


@router.get("/certificates")
async def list_certificates(
    limit: int = Query(100, ge=1, le=500),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = _ws(user)
    rows = (await db.execute(
        select(PGLCertificate).where(PGLCertificate.workspace_id == ws)
        .order_by(desc(PGLCertificate.created_at)).limit(limit)
    )).scalars().all()
    if not rows:
        return {"items": [], "source": "empty", "reason": "No PGL certificates issued for this workspace yet. Certificates are minted when a governed run reaches COMMITTED."}
    return {
        "items": [{
            "certificate_id": c.certificate_id,
            "kind": c.kind,
            "actor_id": c.actor_id,
            "genome_hash": c.genome_hash,
            "plan_hash": c.plan_hash,
            "output_hash": c.output_hash,
            "outcome_hash": c.outcome_hash,
            "pre_certificate_id": c.pre_certificate_id,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in rows],
        "source": "db",
        "count": len(rows),
    }


@router.get("/ledger")
async def life_ledger(
    limit: int = Query(200, ge=1, le=1000),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = _ws(user)
    rows = (await db.execute(
        select(PGLLedgerEvent).where(PGLLedgerEvent.workspace_id == ws)
        .order_by(desc(PGLLedgerEvent.id)).limit(limit)
    )).scalars().all()
    if not rows:
        return {"items": [], "source": "empty", "reason": "No PGL ledger events for this workspace yet."}
    return {
        "items": [{
            "id": e.id,
            "actor_id": e.actor_id,
            "certificate_id": e.certificate_id,
            "event_type": e.event_type,
            "payload": e.payload,
            "prev_event_hash": e.prev_event_hash,
            "event_hash": e.event_hash,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        } for e in rows],
        "source": "db",
        "count": len(rows),
    }


@router.get("/verify")
async def verify_chain(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Replay this workspace's PGL ledger and verify SHA-256 chain integrity."""
    ws = _ws(user)
    pgl = PGLClient(db)
    return await pgl.verify_chain(ws)
