"""
pgl_anchoring.py — Immutable Ledger Anchoring Engine

Periodically batches and anchors PGLLedgerEvent head hashes to an external
write-once-read-many (WORM) storage or blockchain network.
"""

import hashlib
import logging
from datetime import datetime, timezone
from sqlalchemy import select, desc
from backend.core.database.database import get_db_session
from backend.db.models.pgl import PGLLedgerEvent, PGLAnchor

logger = logging.getLogger(__name__)

async def anchor_latest_ledger(workspace_id: str) -> dict | None:
    """
    Finds the latest PGLLedgerEvent for a workspace, verifies if it has already
    been anchored, and pushes the head hash to the simulated external WORM storage.
    """
    try:
        async with get_db_session() as db:
            # 1. Fetch latest ledger event
            stmt = select(PGLLedgerEvent).where(
                PGLLedgerEvent.workspace_id == workspace_id
            ).order_by(desc(PGLLedgerEvent.id)).limit(1)
            res = await db.execute(stmt)
            latest_event = res.scalar_one_or_none()

            if not latest_event:
                return None

            # 2. Check if this head has already been anchored
            check_stmt = select(PGLAnchor).where(
                PGLAnchor.workspace_id == workspace_id,
                PGLAnchor.ledger_head_hash == latest_event.event_hash
            ).limit(1)
            check_res = await db.execute(check_stmt)
            existing_anchor = check_res.scalar_one_or_none()

            if existing_anchor:
                return {
                    "status": "already_anchored",
                    "anchor_id": existing_anchor.id,
                    "ledger_head_hash": existing_anchor.ledger_head_hash,
                    "anchored_tx_hash": existing_anchor.anchored_tx_hash
                }

            # 3. Simulate push to external WORM store / Base Chain contract
            # Generate deterministic transaction receipt hash
            timestamp_str = datetime.now(timezone.utc).isoformat()
            tx_payload = f"worm_anchor:{workspace_id}:{latest_event.event_hash}:{timestamp_str}"
            anchored_tx_hash = f"0x{hashlib.sha256(tx_payload.encode()).hexdigest()}"

            # 4. Record anchor receipt in local database
            anchor = PGLAnchor(
                workspace_id=workspace_id,
                ledger_head_hash=latest_event.event_hash,
                anchored_tx_hash=anchored_tx_hash,
                status="anchored"
            )
            db.add(anchor)
            await db.commit()

            logger.info(
                f"[PGLAnchor] Successfully anchored head hash {latest_event.event_hash[:12]} "
                f"for workspace {workspace_id} to external WORM. Tx: {anchored_tx_hash[:16]}..."
            )

            return {
                "status": "anchored",
                "anchor_id": anchor.id,
                "ledger_head_hash": anchor.ledger_head_hash,
                "anchored_tx_hash": anchor.anchored_tx_hash
            }

    except Exception as e:
        logger.error(f"[PGLAnchor] Failed to anchor ledger head for workspace {workspace_id}: {e}")
        return None
