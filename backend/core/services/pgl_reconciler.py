"""
pgl_reconciler.py — Background SLA and Certificate State Reconciler

Ensures no pre-execution certificate remains open indefinitely.
Scans for OPEN certificates that have exceeded their expires_at timeframe,
updates them to ABANDONED, and appends a corresponding event to the ledger chain.
"""

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, update
from backend.core.database.database import get_db_session
from backend.db.models.pgl import PGLCertificate, PGLLedgerEvent
from backend.services.pgl_client import PGLClient

logger = logging.getLogger(__name__)

async def reconcile_orphaned_certificates() -> int:
    """
    Finds all PGLCertificates in OPEN status where expires_at has passed.
    Transitions them to ABANDONED, and appends a rollback/reconciliation event to the ledger.
    """
    now = datetime.now(timezone.utc)
    reconciled_count = 0

    try:
        async with get_db_session() as db:
            # Query expired OPEN certificates
            stmt = select(PGLCertificate).where(
                PGLCertificate.status == "OPEN",
                PGLCertificate.kind == "pre",
                PGLCertificate.expires_at < now
            )
            result = await db.execute(stmt)
            expired_certs = result.scalars().all()

            if not expired_certs:
                return 0

            pgl = PGLClient(db=db)
            for cert in expired_certs:
                logger.warning(
                    f"[Reconciler] Found orphaned certificate {cert.certificate_id} "
                    f"issued for actor {cert.actor_id} (expired at {cert.expires_at})"
                )
                
                # Update DB state
                cert.status = "ABANDONED"
                cert.resolved_at = now
                db.add(cert)
                
                # Append event to the hash-chained ledger
                await pgl.record_event(
                    workspace_id=cert.workspace_id,
                    actor_id=cert.actor_id,
                    certificate_id=cert.certificate_id,
                    event_type="reconciliation_abandoned",
                    payload={
                        "certificate_id": cert.certificate_id,
                        "original_status": "OPEN",
                        "new_status": "ABANDONED",
                        "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
                        "reconciled_at": now.isoformat(),
                        "reason": "SLA execution timeout exceeded"
                    }
                )
                reconciled_count += 1
            
            await db.commit()
            if reconciled_count > 0:
                logger.info(f"[Reconciler] Successfully resolved {reconciled_count} orphaned certificates.")
                
    except Exception as e:
        logger.error(f"[Reconciler] Exception occurred during certificate reconciliation: {e}")

    return reconciled_count

async def run_reconciler_loop(interval_seconds: int = 60):
    """Loop runner for background reconciliation task."""
    logger.info("[Reconciler] Starting background PGL Certificate Reconciler daemon...")
    while True:
        await reconcile_orphaned_certificates()
        await asyncio.sleep(interval_seconds)
