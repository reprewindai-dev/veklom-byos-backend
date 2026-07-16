import hashlib
import json
import logging
import uuid
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _hash_event(payload: Dict[str, Any], prev_event_hash: Optional[str]) -> str:
    """SHA-256 over canonical payload + previous link — the chain primitive."""
    body = {"payload": payload, "prev": prev_event_hash}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class PGLClient:
    """Sovereign PGL Gnomledger client.

    Backs the keystone invariant: no governed action executes anonymously.
    When constructed with a DB session it writes REAL, SHA-256 hash-chained
    certificates + ledger events to `pgl_certificates` / `pgl_ledger_events`.
    When no session is available (e.g. a hot path that has not yet been wired)
    it degrades to the simulated response so existing callers never break.

    IMPORTANT: persistence uses `flush`, NOT `commit`.  The orchestrator owns
    the surrounding transaction and commits via its own `_update_state`.
    """

    def __init__(self, db: Optional[AsyncSession] = None, pgl_endpoint: str = "http://pgl-ledger:50051"):
        if os.getenv("CAPPO_REQUIRE_PERSISTENT_PGL", "").lower() == "true" and db is None:
            raise RuntimeError("PGLClient must be initialized with a DB session in production (CAPPO_REQUIRE_PERSISTENT_PGL is set). Simulated fallback is forbidden.")
        self.db = db
        self.endpoint = pgl_endpoint

    @property
    def persistent(self) -> bool:
        return self.db is not None

    async def _last_hash(self, workspace_id: str) -> Optional[str]:
        from backend.db.models.pgl import PGLLedgerEvent
        row = (
            await self.db.execute(
                select(PGLLedgerEvent.event_hash)
                .where(PGLLedgerEvent.workspace_id == workspace_id)
                .order_by(desc(PGLLedgerEvent.id))
                .limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def _append_event(
        self, workspace_id: str, actor_id: str, certificate_id: Optional[str],
        event_type: str, payload: Dict[str, Any],
    ) -> str:
        from backend.db.models.pgl import PGLLedgerEvent
        prev = await self._last_hash(workspace_id)
        event_hash = _hash_event(payload, prev)
        self.db.add(PGLLedgerEvent(
            workspace_id=workspace_id,
            actor_id=actor_id,
            pgl_identity_id=actor_id,
            certificate_id=certificate_id,
            event_type=event_type,
            payload=payload,
            prev_event_hash=prev,
            event_hash=event_hash,
        ))
        await self.db.flush()
        return event_hash

    async def commit_intent(
        self,
        workspace_id: str,
        actor_id: str,
        genome_hash: str,
        constitution_hash: str,
        plan_hash: Optional[str] = None,
        tool_manifest_hash: Optional[str] = None,
        delegation_chain_hash: Optional[str] = None,
        input_hash: Optional[str] = None,
        scope: Optional[str] = "wallet:spend",
    ) -> Dict[str, Any]:
        """Commit constitutional identity + pre-execution proof. Returns a signed pre-execution certificate."""
        import hmac
        import json
        pre_execution_certificate_id = f"pgl_cert_pre_{uuid.uuid4().hex[:12]}"
        
        # Determine time-bounded expiration (default to 5 minutes)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=300)

        # Multi-key selection logic for rotation
        raw_keys = os.environ.get("PGL_AUTHORITY_KEYS_JSON")
        active_key_id = "v1"
        authority_key = "pgl_default_authority_signing_secret_key_v1".encode()
        
        if raw_keys:
            try:
                keys_config = json.loads(raw_keys)
                active_key_id = keys_config.get("active_key_id", "v1")
                authority_key = keys_config.get("keys", {}).get(active_key_id, "pgl_default_authority_signing_secret_key_v1").encode()
            except Exception:
                pass

        sign_payload = f"{pre_execution_certificate_id}:{actor_id}:{scope or ''}:{expires_at.isoformat()}"
        signature_hash = hmac.new(authority_key, sign_payload.encode(), hashlib.sha256).hexdigest()
        signature = f"{active_key_id}:{signature_hash}"

        result = {
            "status": "OPEN",
            "pre_execution_certificate_id": pre_execution_certificate_id,
            "genome_hash": genome_hash,
            "constitution_hash": constitution_hash,
            "plan_hash": plan_hash,
            "tool_manifest_hash": tool_manifest_hash,
            "delegation_chain_hash": delegation_chain_hash,
            "input_hash": input_hash,
            "signature": signature,
            "scope": scope,
            "expires_at": expires_at.isoformat(),
            "lineage_parent_hashes": [],
            "persisted": False,
        }

        if not self.persistent:
            logger.info(f"[PGL] (sim) commit_intent actor={actor_id} ws={workspace_id}")
            return result

        from backend.db.models.pgl import PGLCertificate
        self.db.add(PGLCertificate(
            certificate_id=pre_execution_certificate_id,
            kind="pre",
            workspace_id=workspace_id,
            actor_id=actor_id,
            pgl_identity_id=actor_id,  # Assume user/identity ID matches actor_id or resolves
            genome_hash=genome_hash,
            constitution_hash=constitution_hash,
            plan_hash=plan_hash,
            status="OPEN",
            signature=signature,
            expires_at=expires_at,
            scope=scope,
        ))
        event_hash = await self._append_event(
            workspace_id, actor_id, pre_execution_certificate_id, "commit_intent",
            {"genome_hash": genome_hash, "constitution_hash": constitution_hash, "plan_hash": plan_hash, "scope": scope, "expires_at": expires_at.isoformat()},
        )
        result["persisted"] = True
        result["event_hash"] = event_hash
        logger.info(f"[PGL] commit_intent persisted cert={pre_execution_certificate_id} hash={event_hash[:12]}")
        return result

    async def attest_outcome(
        self,
        pre_execution_certificate_id: str,
        output_hash: str,
        outcome_hash: str,
        operator_state_attestation: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record outcome/output hashes after execution. Issues the post-execution certificate."""
        post_execution_certificate_id = f"pgl_cert_post_{uuid.uuid4().hex[:12]}"
        result = {
            "status": "SUCCEEDED",
            "pre_execution_certificate_id": pre_execution_certificate_id,
            "post_execution_certificate_id": post_execution_certificate_id,
            "output_hash": output_hash,
            "outcome_hash": outcome_hash,
            "operator_state_attestation": operator_state_attestation,
            "persisted": False,
        }

        if not self.persistent:
            logger.info(f"[PGL] (sim) attest_outcome pre={pre_execution_certificate_id}")
            return result

        from backend.db.models.pgl import PGLCertificate
        # Resolve workspace/actor from the pre-certificate when not supplied.
        pre = (await self.db.execute(
            select(PGLCertificate).where(PGLCertificate.certificate_id == pre_execution_certificate_id)
        )).scalar_one_or_none()
        ws = workspace_id or (pre.workspace_id if pre else "unknown")
        actor = actor_id or (pre.actor_id if pre else "unknown")

        if pre:
            pre.status = "SUCCEEDED"
            pre.resolved_at = datetime.now(timezone.utc)

        self.db.add(PGLCertificate(
            certificate_id=post_execution_certificate_id,
            kind="post",
            workspace_id=ws,
            actor_id=actor,
            pgl_identity_id=actor,
            output_hash=output_hash,
            outcome_hash=outcome_hash,
            pre_certificate_id=pre_execution_certificate_id,
            status="SUCCEEDED",
            resolved_at=datetime.now(timezone.utc),
        ))
        event_hash = await self._append_event(
            ws, actor, post_execution_certificate_id, "attest_outcome",
            {"pre": pre_execution_certificate_id, "output_hash": output_hash, "outcome_hash": outcome_hash},
        )
        result["persisted"] = True
        result["event_hash"] = event_hash
        logger.info(f"[PGL] attest_outcome persisted cert={post_execution_certificate_id} hash={event_hash[:12]}")
        return result

    async def register_rollback(
        self,
        post_execution_certificate_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Register a rollback event in the ledger."""
        rollback_event_id = f"pgl_rb_{uuid.uuid4().hex[:12]}"
        result = {
            "status": "ROLLED_BACK",
            "rollback_event_id": rollback_event_id,
            "post_execution_certificate_id": post_execution_certificate_id,
            "reason": reason,
            "persisted": False,
        }

        if not self.persistent:
            logger.warning(f"[PGL] (sim) rollback post={post_execution_certificate_id} reason={reason}")
            return result

        from sqlalchemy.orm import aliased
        from backend.db.models.pgl import PGLCertificate

        PostCert = aliased(PGLCertificate, name="post_cert")
        PreCert = aliased(PGLCertificate, name="pre_cert")

        row = (await self.db.execute(
            select(PostCert, PreCert)
            .outerjoin(PreCert, PostCert.pre_certificate_id == PreCert.certificate_id)
            .where(PostCert.certificate_id == post_execution_certificate_id)
        )).first()

        post = row[0] if row else None
        pre = row[1] if row and len(row) > 1 else None

        ws = post.workspace_id if post else "unknown"
        actor = post.actor_id if post else "unknown"

        if post:
            post.status = "ROLLED_BACK"
            post.resolved_at = datetime.now(timezone.utc)
            if pre:
                pre.status = "ROLLED_BACK"
                pre.resolved_at = datetime.now(timezone.utc)

        event_hash = await self._append_event(
            ws, actor, post_execution_certificate_id, "rollback",
            {"rollback_event_id": rollback_event_id, "reason": reason},
        )
        result["persisted"] = True
        result["event_hash"] = event_hash
        logger.warning(f"[PGL] rollback persisted post={post_execution_certificate_id} hash={event_hash[:12]}")
        return result

    async def record_event(
        self, workspace_id: str, actor_id: str, certificate_id: Optional[str],
        event_type: str, payload: Dict[str, Any],
    ) -> Optional[str]:
        """Public: append a hash-chained ledger event for any governed moving part
        (route decisions, node executions, etc.). Returns the event hash, or None
        when no DB session is bound. Uses flush; caller owns the commit."""
        if not self.persistent:
            logger.info(f"[PGL] (sim) record_event {event_type} ws={workspace_id}")
            return None
        return await self._append_event(workspace_id, actor_id, certificate_id, event_type, payload)

    async def verify_chain(self, workspace_id: str) -> Dict[str, Any]:
        """Replay the workspace's ledger and verify the SHA-256 chain integrity."""
        if not self.persistent:
            return {"verified": False, "reason": "no_db_session", "events": 0}
        from backend.db.models.pgl import PGLLedgerEvent
        rows = (await self.db.execute(
            select(PGLLedgerEvent).where(PGLLedgerEvent.workspace_id == workspace_id)
            .order_by(PGLLedgerEvent.id.asc())
        )).scalars().all()
        prev = None
        for ev in rows:
            expected = _hash_event(ev.payload, prev)
            if ev.prev_event_hash != prev or ev.event_hash != expected:
                return {
                    "verified": False,
                    "broken_at_event_id": ev.id,
                    "events": len(rows),
                    "reason": "chain_integrity_break",
                }
            prev = ev.event_hash
        return {"verified": True, "events": len(rows), "head_hash": prev}

    async def resolve_genome(self, agent_id: str) -> str:
        """Resolve an agent's current genome hash. Reads the latest GenomeVersion when persistent."""
        if self.persistent:
            try:
                from backend.db.models.genome import GenomeVersion
                row = (await self.db.execute(
                    select(GenomeVersion.genome_hash)
                    .where(GenomeVersion.agent_id == agent_id)
                    .order_by(desc(GenomeVersion.version))
                    .limit(1)
                )).scalar_one_or_none()
                if row:
                    return row
            except Exception as e:  # pragma: no cover - defensive, agent_id may be non-int
                logger.debug(f"[PGL] resolve_genome fallback: {e}")
        return f"gnm_{uuid.uuid4().hex[:16]}"
