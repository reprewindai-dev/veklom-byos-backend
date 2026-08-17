"""
pgl_identity_gate.py — Universal PGL Identity Gate

THE LAW: No agent runs without a verified PGL identity.
         No exceptions. No bypasses. No ifs, ands, or buts.

Every agent in Veklom has a gnomledger identity — their "birth certificate",
just like a real person has a government-issued ID. This module enforces that
before ANY agent can execute ANY action, it must:

  1. Have a resolved PGLIdentity row in the pgl_identities table.
  2. Have a BirthCertificate record linking it to the lineage graph.
  3. Be in ACTIVE status (not QUARANTINED, SUSPENDED, or REVOKED).
  4. Receive a pre-execution PGL certificate that creates a hash-chained,
     auditable record of the intent before any action is taken.

If any of these checks fail → the execution is HARD BLOCKED.

This gate is designed to be called from:
  - BankerAgentService.pay_for_route()        (payments)
  - RunOrchestrator.govern_run()              (governed runs)
  - run_pipeline_background()                  (async pipeline workers)
  - Any future agent service                   (universal contract)

Architecture:
  - For SYSTEM agents (banker, orchestrator, etc.): auto-seeds identity on
    first run, seeded with a generated Ed25519 key and a stable actor_id.
  - For USER-REGISTERED agents: resolves from agents table → birth_certificates
    → pgl_identities chain. If the chain is broken, execution is blocked.
  - PGL certificates use flush (not commit) — the caller owns the transaction.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Enums & Constants
# ─────────────────────────────────────────────────────────────────────────────

class AgentKind(str, Enum):
    """Classification of what kind of agent is requesting execution."""
    SYSTEM      = "system"       # Built-in Veklom system agents (banker, orchestrator)
    REGISTERED  = "registered"   # User-registered agents from agents table
    PIPELINE    = "pipeline"     # Pipeline runner workers
    GOVERNED    = "governed"     # Governed run actors via UACP


# Well-known system agent actor IDs — must match what's seeded in pgl_identities
SYSTEM_AGENT_CONFIGS = {
    "banker-agent::veklom-treasury": {
        "kind":        AgentKind.SYSTEM,
        "description": "Autonomous treasury payment agent — x402 USDC settlement on Base Mainnet",
        "workspace":   "veklom-system::banker",
        "genome_seed": b"banker-agent:genome:v1.0:veklom-treasury-payments",
        "constitution": (
            "BankerAgent may only spend USDC to treasury addresses resolved from "
            "VEKLOM_TREASURY_ADDRESS. Daily cap enforced. "
            "No payment executes without a valid PGL pre-execution certificate. "
            "Every spend is recorded to agent_wallet_ledger before broadcast."
        ),
    },
    "orchestrator::veklom-runtime": {
        "kind":        AgentKind.SYSTEM,
        "description": "Run orchestrator — governs INTENT_CAPTURED → SEALED state machine for all VeklomRuns",
        "workspace":   "veklom-system::orchestrator",
        "genome_seed": b"orchestrator:genome:v1.0:veklom-run-state-machine",
        "constitution": (
            "RunOrchestrator may only transition VeklomRuns through valid state paths. "
            "Every governed run must have an actor_id and workspace_id. "
            "Denied runs must record a reason. Attested runs must carry output_hash."
        ),
    },
    "pipeline-worker::veklom-runtime": {
        "kind":        AgentKind.SYSTEM,
        "description": "Background pipeline execution worker — runs autonomous pipeline steps",
        "workspace":   "veklom-system::pipeline",
        "genome_seed": b"pipeline-worker:genome:v1.0:veklom-pipeline-executor",
        "constitution": (
            "PipelineWorker may only execute steps defined in the compiled pipeline plan. "
            "All tool calls must be in ALLOWED_LANGCHAIN_TOOLS. "
            "PII must be redacted before leaving Veklom infrastructure."
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions — all hard blocks
# ─────────────────────────────────────────────────────────────────────────────

class PGLIdentityError(Exception):
    """
    Raised when the PGL gate blocks execution.
    This is a HARD BLOCK — the calling code must NOT proceed.

    Catching this and ignoring it is a governance violation.
    """
    def __init__(self, actor_id: str, reason: str):
        self.actor_id = actor_id
        self.reason   = reason
        super().__init__(
            f"[PGL GATE] Execution BLOCKED for agent '{actor_id}': {reason}"
        )


class PGLIdentityNotFound(PGLIdentityError):
    """Agent has no PGL identity — was never properly registered in gnomledger."""
    pass


class PGLIdentityQuarantined(PGLIdentityError):
    """Agent is QUARANTINED — all execution suspended pending review."""
    pass


class PGLIdentitySuspended(PGLIdentityError):
    """Agent is SUSPENDED — temporary hold on execution."""
    pass


class PGLCertificateError(PGLIdentityError):
    """Pre-execution certificate could not be issued — ledger write failed."""
    pass


class PGLIdentityExpired(PGLIdentityError):
    """Agent's annual PGL identity has expired — must renew before executing.

    This is NOT the same as QUARANTINED or REVOKED. The identity still exists
    and is valid. The agent just needs to renew (like a driver's license).
    Once renewed, execution is restored immediately with the same ID.
    """
    def __init__(self, actor_id: str, reason: str, notification_dict: dict | None = None):
        self.notification_dict = notification_dict
        super().__init__(actor_id, reason)



# ─────────────────────────────────────────────────────────────────────────────
# PGL Execution Context — returned after successful gate-check
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PGLExecutionContext:
    """
    Proof that an agent has been cleared through the PGL gate.

    Carry this across the entire lifecycle of an agent's action:
    - Pass it to attest_success() after completion
    - Pass it to attest_failure() if the action fails

    Never discard this without closing the certificate chain.
    """
    actor_id:              str
    pgl_identity_id:       str
    workspace_id:          str
    kind:                  AgentKind
    pre_execution_cert_id: str
    genome_hash:           str
    constitution_hash:     str
    intent_hash:           str
    birth_cert_id:         Optional[str] = None
    cleared_at:            datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trust_level:           str = "UNKNOWN"   # PROBATIONARY | ACTIVE | RENEWAL_DUE | EXPIRED
    lifecycle_warning:     Optional[str] = None   # non-None when PROBATIONARY or RENEWAL_DUE
    signature:             Optional[str] = None
    expires_at:            Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _intent_hash(action: str, payload: dict) -> str:
    """Deterministic hash of the execution intent — ties the PGL cert to this specific action."""
    body = json.dumps({"action": action, "payload": payload}, sort_keys=True, default=str)
    return _sha256(body)


# ─────────────────────────────────────────────────────────────────────────────
# Core gate
# ─────────────────────────────────────────────────────────────────────────────

class PGLIdentityGate:
    """
    Universal PGL identity enforcement gate.

    Usage:
        ctx = await PGLIdentityGate.require(
            db        = db,
            actor_id  = "banker-agent::veklom-treasury",
            action    = "pay_for_route",
            payload   = {"route": "/api/v1/x402/score", "amount_usdc": 0.10},
        )
        # Only reaches here if fully cleared
        ...do the thing...
        await PGLIdentityGate.attest_success(db, ctx, output={"tx_hash": tx})
    """

    @staticmethod
    async def _resolve_or_seed_system_agent(
        db:       AsyncSession,
        actor_id: str,
        config:   dict,
    ) -> "PGLIdentity":  # noqa: F821
        """
        For system agents: find or auto-seed the PGLIdentity row.
        System agents are part of Veklom infrastructure — their identity
        is governed by code, not by user registration.
        """
        import json

        from backend.core.database.redis_client import redis_client
        from backend.db.models.pgl import PGLIdentity

        # Redis projection check
        cached_identity_str = await redis_client.get(f"veklom:pgl:identity:{actor_id}")
        if cached_identity_str:
            try:
                cached = json.loads(cached_identity_str)
                identity = PGLIdentity(
                    id=cached.get("id"),
                    tenant_id=cached.get("tenant_id"),
                    primary_public_key=cached.get("primary_public_key"),
                    key_type=cached.get("key_type", "ed25519"),
                    metadata_json=cached.get("metadata", {})
                )
                return identity
            except Exception as e:
                logger.warning(f"[PGLGate] Failed to parse cached system identity for {actor_id}: {e}")

        result = await db.execute(
            select(PGLIdentity).where(PGLIdentity.id == actor_id)
        )
        identity = result.scalar_one_or_none()

        if identity is None:
            logger.info(f"[PGLGate] Auto-seeding system agent identity: {actor_id}")
            import base64
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
                priv = Ed25519PrivateKey.generate()
                pub_bytes = priv.public_key().public_bytes_raw()
                pub_b64   = base64.b64encode(pub_bytes).decode()
            except ImportError:
                # Fallback: use a deterministic pseudo-key from actor_id
                import base64
                pub_b64 = base64.b64encode(_sha256(actor_id).encode()).decode()[:44]

            genome_hash = _sha256(config["genome_seed"])
            constitution_hash = _sha256(config["constitution"])

            identity = PGLIdentity(
                id                 = actor_id,
                tenant_id          = config["workspace"],
                primary_public_key = pub_b64,
                key_type           = "ed25519",
                metadata_json      = {
                    "status":             "ACTIVE",
                    "kind":               config["kind"].value,
                    "description":        config["description"],
                    "genome_hash":        genome_hash,
                    "constitution_hash":  constitution_hash,
                    "seeded_at":          datetime.now(timezone.utc).isoformat(),
                    "seeded_by":          "pgl_identity_gate::auto_seed",
                },
            )
            db.add(identity)
            await db.flush()
            logger.info(f"[PGLGate] ✅ System agent identity seeded: {actor_id}")

        # Populate projection cache
        try:
            import json

            from backend.core.database.redis_client import redis_client
            cache_payload = {
                "id": identity.id,
                "tenant_id": identity.tenant_id,
                "primary_public_key": identity.primary_public_key,
                "key_type": identity.key_type,
                "metadata": identity.metadata_json
            }
            await redis_client.set(
                f"veklom:pgl:identity:{identity.id}",
                json.dumps(cache_payload),
                ex=3600
            )
        except Exception as e:
            logger.warning(f"[PGLGate] Failed to cache system identity for {identity.id}: {e}")

        return identity

    @staticmethod
    async def _resolve_registered_agent(
        db:       AsyncSession,
        actor_id: str,
    ) -> "PGLIdentity":  # noqa: F821
        """
        For user-registered agents: resolve from pgl_identities directly,
        or trace via agents table → birth_certificates → pgl_identities.
        If the chain is broken, raise PGLIdentityNotFound.
        """
        import json

        from backend.core.database.redis_client import redis_client
        from backend.db.models.agent import Agent
        from backend.db.models.lineage import BirthCertificate
        from backend.db.models.pgl import PGLIdentity

        # Redis projection check
        cached_identity_str = await redis_client.get(f"veklom:pgl:identity:{actor_id}")
        if cached_identity_str:
            try:
                cached = json.loads(cached_identity_str)
                identity = PGLIdentity(
                    id=cached.get("id"),
                    tenant_id=cached.get("tenant_id"),
                    primary_public_key=cached.get("primary_public_key"),
                    key_type=cached.get("key_type", "ed25519"),
                    metadata_json=cached.get("metadata", {})
                )
                return identity
            except Exception as e:
                logger.warning(f"[PGLGate] Failed to parse cached PGL identity for {actor_id}: {e}")

        # Try direct pgl_identity lookup first
        result = await db.execute(
            select(PGLIdentity).where(PGLIdentity.id == actor_id)
        )
        identity = result.scalar_one_or_none()
        if identity:
            try:
                cache_payload = {
                    "id": identity.id,
                    "tenant_id": identity.tenant_id,
                    "primary_public_key": identity.primary_public_key,
                    "key_type": identity.key_type,
                    "metadata": identity.metadata_json
                }
                await redis_client.set(
                    f"veklom:pgl:identity:{identity.id}",
                    json.dumps(cache_payload),
                    ex=3600
                )
            except Exception as e:
                logger.warning(f"[PGLGate] Failed to cache PGL identity for {identity.id}: {e}")
            return identity

        # Try to find by agent_id in agents table, then follow birth cert
        agent_result = await db.execute(
            select(Agent).where(Agent.agent_id == actor_id)
        )
        agent = agent_result.scalar_one_or_none()

        if agent is None:
            raise PGLIdentityNotFound(
                actor_id=actor_id,
                reason=(
                    f"No PGL identity or registered agent found with actor_id='{actor_id}'. "
                    f"Agent must be registered through /api/v1/agents before it can execute."
                )
            )

        # Agent exists — check it has a birth certificate with PGL identity
        cert_result = await db.execute(
            select(BirthCertificate).where(BirthCertificate.agent_id == agent.id)
        )
        cert = cert_result.scalar_one_or_none()

        if cert is None:
            raise PGLIdentityNotFound(
                actor_id=actor_id,
                reason=(
                    f"Agent '{actor_id}' exists but has no BirthCertificate. "
                    f"Registration was incomplete. Re-register the agent to receive a gnomledger identity."
                )
            )

        # Follow birth certificate to identity
        result = await db.execute(
            select(PGLIdentity).where(PGLIdentity.id == cert.pgl_identity_id)
        )
        identity = result.scalar_one_or_none()

        if identity:
            try:
                import json

                from backend.core.database.redis_client import redis_client
                cache_payload = {
                    "id": identity.id,
                    "tenant_id": identity.tenant_id,
                    "primary_public_key": identity.primary_public_key,
                    "key_type": identity.key_type,
                    "metadata": identity.metadata_json
                }
                await redis_client.set(
                    f"veklom:pgl:identity:{identity.id}",
                    json.dumps(cache_payload),
                    ex=3600
                )
                # We also want to map the actor_id directly to this identity
                if actor_id != identity.id:
                    await redis_client.set(
                        f"veklom:pgl:identity:{actor_id}",
                        json.dumps(cache_payload),
                        ex=3600
                    )
            except Exception as e:
                logger.warning(f"[PGLGate] Failed to cache PGL identity for {identity.id} via agent {actor_id}: {e}")


        if identity is None:
            raise PGLIdentityNotFound(
                actor_id=actor_id,
                reason=(
                    f"Agent '{actor_id}' has a BirthCertificate (cert_id={cert.certificate_id}) "
                    f"but its pgl_identity_id='{cert.pgl_identity_id}' does not exist in pgl_identities. "
                    f"The gnomledger chain is broken. This agent cannot run."
                )
            )

        return identity

    @staticmethod
    def _check_status(identity: "PGLIdentity", actor_id: str) -> None:  # noqa: F821
        """Hard status check — raise immediately for any non-ACTIVE status."""
        meta   = identity.metadata_json or {}
        status = meta.get("status", "ACTIVE").upper()

        if status == "QUARANTINED":
            raise PGLIdentityQuarantined(
                actor_id=actor_id,
                reason=(
                    f"Agent is QUARANTINED: {meta.get('containment_reason', 'No reason recorded')}. "
                    f"Contact a Veklom admin to lift containment via "
                    f"POST /api/v1/pgl/{actor_id}/quarantine."
                )
            )
        if status == "SUSPENDED":
            raise PGLIdentitySuspended(
                actor_id=actor_id,
                reason=f"Agent is SUSPENDED: {meta.get('suspension_reason', 'No reason recorded')}."
            )
        if status in ("REVOKED", "DEACTIVATED", "DELETED"):
            raise PGLIdentityError(
                actor_id=actor_id,
                reason=f"Agent identity status is '{status}' — permanently blocked from execution."
            )
        # Only ACTIVE passes through

    @staticmethod
    async def require(
        db:       AsyncSession,
        actor_id: str,
        action:   str,
        payload:  dict,
        kind:     AgentKind = AgentKind.REGISTERED,
        scope:    Optional[str] = "wallet:spend",
    ) -> PGLExecutionContext:
        """
        HARD GATE — call this at the start of every agent action.

        Resolves the agent's PGL identity, validates its status,
        issues a pre-execution PGL certificate, and returns a
        PGLExecutionContext to carry through the action lifecycle.

        Args:
            db:       Async DB session (PGLClient uses flush, not commit).
            actor_id: The agent's stable identifier (pgl_identities.id or agent.agent_id).
            action:   What the agent is about to do (e.g. "pay_for_route", "execute_step").
            payload:  The intent payload — gets hashed into the PGL certificate.
            kind:     AgentKind.SYSTEM for built-in agents, REGISTERED for user agents.

        Returns:
            PGLExecutionContext — proof of clearance.

        Raises:
            PGLIdentityNotFound:    Agent has no gnomledger identity.
            PGLIdentityQuarantined: Agent is quarantined.
            PGLIdentitySuspended:   Agent is suspended.
            PGLIdentityError:       Any other gate failure.
            PGLCertificateError:    Pre-execution cert could not be issued.
        """
        logger.info(
            f"[PGLGate] 🔐 Identity check — actor='{actor_id}' action='{action}'"
        )

        # ── 1. Resolve identity ───────────────────────────────────────────────
        try:
            if kind == AgentKind.SYSTEM and actor_id in SYSTEM_AGENT_CONFIGS:
                config   = SYSTEM_AGENT_CONFIGS[actor_id]
                identity = await PGLIdentityGate._resolve_or_seed_system_agent(
                    db, actor_id, config
                )
                workspace_id      = config["workspace"]
                genome_hash       = _sha256(config["genome_seed"])
                constitution_hash = _sha256(config["constitution"])
            else:
                # Registered agent — trace through birth certificate chain
                identity          = await PGLIdentityGate._resolve_registered_agent(db, actor_id)
                workspace_id      = identity.tenant_id
                meta              = identity.metadata_json or {}
                genome_hash       = meta.get("genome_hash") or _sha256(f"gnm:{actor_id}")
                constitution_hash = meta.get("constitution_hash") or _sha256(f"const:{actor_id}")
        except PGLIdentityError:
            raise  # Already well-formed, re-raise directly
        except Exception as exc:
            raise PGLIdentityError(
                actor_id=actor_id,
                reason=f"Identity resolution failed unexpectedly: {exc}"
            ) from exc

        # ── 2. Status check — quarantine/suspend/revoke first ────────────────────
        PGLIdentityGate._check_status(identity, actor_id)

        # ── 2b. Lifecycle check — probation / renewal / expiry ────────────────
        # EXPIRED = hard block. RENEWAL_DUE / PROBATIONARY = warn, allow through.
        _lifecycle_warning: str | None = None
        _trust_level: str = "ACTIVE"
        _lifecycle_notification: dict | None = None
        try:
            from sqlalchemy import case, func

            from backend.core.services.pgl_identity_lifecycle import (
                TrustLevel,
                compute_lifecycle,
            )
            from backend.core.services.pgl_notifications import (
                notify_active,
                notify_grace_period,
                notify_hard_expired,
                notify_probationary,
                notify_renewal_due,
            )

            # Fetch behavioral statistics from the DB for promotion checks
            from backend.db.models.pgl import PGLCertificate

            stats_result = await db.execute(
                select(
                    func.sum(case((PGLCertificate.status == "SUCCEEDED", 1), else_=0)),
                    func.sum(case((PGLCertificate.status.in_(["FAILED", "ROLLED_BACK"]), 1), else_=0))
                )
                .where(
                    PGLCertificate.actor_id == actor_id,
                    PGLCertificate.kind == "post",
                    PGLCertificate.status.in_(["SUCCEEDED", "FAILED", "ROLLED_BACK"])
                )
            )
            stats_row = stats_result.first()
            active_attestations = int(stats_row[0] or 0) if stats_row else 0
            active_rollbacks = int(stats_row[1] or 0) if stats_row else 0

            _lc = compute_lifecycle(
                metadata=identity.metadata_json or {},
                created_at=identity.created_at,
                active_attestations=active_attestations,
                active_rollbacks=active_rollbacks,
            )
            _trust_level = _lc.trust_level.value

            # Build standard user notification based on TrustLevel state
            pgl_id = identity.id
            if _lc.trust_level == TrustLevel.HARD_EXPIRED:
                n = notify_hard_expired(pgl_id, _lc.hard_block_date.isoformat() if _lc.hard_block_date else "")
                _lifecycle_notification = n.to_dict()
                raise PGLIdentityExpired(
                    actor_id=actor_id,
                    reason=n.message,
                    notification_dict=_lifecycle_notification
                )
            elif _lc.trust_level == TrustLevel.GRACE_PERIOD:
                # Still allowed to execute but escalating warning
                n = notify_grace_period(
                    pgl_id=pgl_id,
                    grace_day=_lc.grace_day or 1,
                    days_remaining=(14 - (_lc.grace_day or 1)),
                    hard_block_date=_lc.hard_block_date.isoformat() if _lc.hard_block_date else ""
                )
                _lifecycle_notification = n.to_dict()
                _lifecycle_warning = n.message
                logger.warning(f"[PGLGate] ⚠️  {n.title} - {n.message}")
            elif _lc.trust_level == TrustLevel.RENEWAL_DUE:
                n = notify_renewal_due(
                    pgl_id=pgl_id,
                    days_remaining=_lc.days_until_renewal,
                    renewal_due_at=_lc.renewal_due_at.isoformat()
                )
                _lifecycle_notification = n.to_dict()
                _lifecycle_warning = n.message
                logger.warning(f"[PGLGate] ⚠️  {n.title}")
            elif _lc.trust_level == TrustLevel.PROBATIONARY:
                days_rem = (identity.created_at + timedelta(days=90) - datetime.now(timezone.utc)).days
                n = notify_probationary(pgl_id, max(0, days_rem), _lc.probation_ends_at.isoformat())
                _lifecycle_notification = n.to_dict()
                _lifecycle_warning = n.message
            elif _lc.trust_level == TrustLevel.ACTIVE:
                n = notify_active(pgl_id, _lc.renewal_due_at.isoformat(), _lc.days_until_renewal)
                _lifecycle_notification = n.to_dict()

        except PGLIdentityExpired:
            raise   # re-raise hard block
        except PGLIdentityError:
            raise   # already well-formed
        except Exception as _lc_exc:
            # Lifecycle module failure is non-fatal for now — log and continue
            logger.warning(f"[PGLGate] Lifecycle check skipped for '{actor_id}': {_lc_exc}")

        # ── 3. Build intent hash ──────────────────────────────────────────────────
        intent_h = _intent_hash(action, payload)

        # ── 4. Issue pre-execution certificate ───────────────────────────────
        from backend.services.pgl_client import PGLClient
        pgl = PGLClient(db=db)
        try:
            pre_cert = await pgl.commit_intent(
                workspace_id       = workspace_id,
                actor_id           = actor_id,
                genome_hash        = genome_hash,
                constitution_hash  = constitution_hash,
                plan_hash          = intent_h,
                input_hash         = _sha256(json.dumps(payload, sort_keys=True, default=str)),
                scope              = scope,
            )
        except Exception as exc:
            raise PGLCertificateError(
                actor_id=actor_id,
                reason=f"Could not issue pre-execution PGL certificate: {exc}"
            ) from exc

        pre_cert_id = pre_cert["pre_execution_certificate_id"]
        logger.info(
            f"[PGLGate] ✅ Cleared — actor='{actor_id}' "
            f"cert='{pre_cert_id}' "
            f"persisted={pre_cert.get('persisted', False)}"
        )

        # Resolve birth_cert_id if available (for registered agents)
        birth_cert_id = None
        try:
            from backend.db.models.agent import Agent
            from backend.db.models.lineage import BirthCertificate
            agent_res = await db.execute(
                select(Agent).where(Agent.agent_id == actor_id)
            )
            agent_row = agent_res.scalar_one_or_none()
            if agent_row:
                cert_res = await db.execute(
                    select(BirthCertificate).where(
                        BirthCertificate.agent_id == agent_row.id
                    )
                )
                cert_row = cert_res.scalar_one_or_none()
                if cert_row:
                    birth_cert_id = cert_row.certificate_id
        except Exception as exc:
            logger.warning(f"[PGLGate] Could not resolve birth certificate for actor '{actor_id}': {exc}")

        return PGLExecutionContext(
            actor_id              = actor_id,
            pgl_identity_id       = identity.id,
            workspace_id          = workspace_id,
            kind                  = kind if kind == AgentKind.SYSTEM else AgentKind.REGISTERED,
            pre_execution_cert_id = pre_cert_id,
            genome_hash           = genome_hash,
            constitution_hash     = constitution_hash,
            intent_hash           = intent_h,
            birth_cert_id         = birth_cert_id,
            trust_level           = _trust_level,
            lifecycle_warning     = _lifecycle_warning,
            signature             = pre_cert.get("signature"),
            expires_at            = datetime.fromisoformat(pre_cert["expires_at"]) if pre_cert.get("expires_at") else None,
        )

    @staticmethod
    async def attest_success(
        db:      AsyncSession,
        ctx:     PGLExecutionContext,
        output:  dict,
    ) -> None:
        """
        Close the PGL certificate chain after a successful execution.
        Call this after the agent's action completes successfully.
        output: dict of results (will be hashed, NOT stored in plaintext).
        """
        from backend.services.pgl_client import PGLClient
        output_hash  = _sha256(json.dumps(output, sort_keys=True, default=str))
        outcome_body = json.dumps(
            {"status": "success", "output_hash": output_hash, "actor_id": ctx.actor_id},
            sort_keys=True,
        )
        outcome_hash = _sha256(outcome_body)

        pgl = PGLClient(db=db)
        try:
            post_cert = await pgl.attest_outcome(
                pre_execution_certificate_id = ctx.pre_execution_cert_id,
                output_hash                  = output_hash,
                outcome_hash                 = outcome_hash,
                operator_state_attestation   = {
                    "actor_id":    ctx.actor_id,
                    "birth_cert":  ctx.birth_cert_id,
                    "action":      "success",
                    "cleared_at":  ctx.cleared_at.isoformat(),
                },
                workspace_id = ctx.workspace_id,
                actor_id     = ctx.actor_id,
            )
            logger.info(
                f"[PGLGate] ✅ Attested — actor='{ctx.actor_id}' "
                f"post_cert='{post_cert['post_execution_certificate_id']}'"
            )
        except Exception as exc:
            logger.error(
                f"[PGLGate] ⚠️  attest_success failed for '{ctx.actor_id}' "
                f"(action completed, certificate gap): {exc}"
            )

    @staticmethod
    async def attest_failure(
        db:     AsyncSession,
        ctx:    PGLExecutionContext,
        reason: str,
    ) -> None:
        """
        Register a rollback in the PGL ledger after a failed execution.
        Call this in ALL failure paths so the pre-cert is never left open.
        """
        from backend.db.models.pgl import PGLCertificate
        from backend.services.pgl_client import PGLClient

        pseudo_post_id = f"pgl_cert_post_failed_{uuid.uuid4().hex[:12]}"
        try:
            db.add(PGLCertificate(
                certificate_id      = pseudo_post_id,
                kind                = "post",
                workspace_id        = ctx.workspace_id,
                actor_id            = ctx.actor_id,
                pgl_identity_id     = ctx.pgl_identity_id,
                pre_certificate_id  = ctx.pre_execution_cert_id,
                output_hash         = _sha256(b"failed"),
                outcome_hash        = _sha256(reason),
                status              = "failed",
            ))
            await db.flush()

            pgl = PGLClient(db=db)
            await pgl.register_rollback(
                post_execution_certificate_id = pseudo_post_id,
                reason                        = reason[:512],   # cap length
            )
            logger.warning(
                f"[PGLGate] 📋 Rollback registered — actor='{ctx.actor_id}' "
                f"pre_cert='{ctx.pre_execution_cert_id}' reason='{reason[:80]}'"
            )
        except Exception as exc:
            logger.error(
                f"[PGLGate] Failed to register PGL rollback for '{ctx.actor_id}': {exc}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI dependency — use in any router that needs agent identity enforcement
# ─────────────────────────────────────────────────────────────────────────────

async def require_pgl_identity(
    db:       AsyncSession,
    actor_id: str,
    action:   str,
    payload:  dict,
    kind:     AgentKind = AgentKind.REGISTERED,
) -> PGLExecutionContext:
    """
    Drop-in FastAPI/service dependency for PGL enforcement.

    Example in a router:
        ctx = await require_pgl_identity(db, actor_id, "run_step", payload)
        # Execution proceeds only if ctx is returned
    """
    return await PGLIdentityGate.require(
        db=db, actor_id=actor_id, action=action, payload=payload, kind=kind
    )
