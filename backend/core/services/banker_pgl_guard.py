"""
BankerAgentPGLGuard — Hard PGL gate for the Banker Agent.

RULE: No if, and, or but — every agent goes through PGL. If it hasn't, it can't run.

This module wraps the PGLClient to provide a strict identity checkpoint
specifically for the Banker Agent. It must be called at the very start of
BankerAgentService.pay_for_route() before anything else (including key
loading). If PGL identity resolution fails for any reason, the payment
is HARD BLOCKED and a BankerAgentPGLError is raised.

What this does:
  1. Resolves the Banker Agent's PGL identity from pgl_identities using the
     canonical agent actor_id ("banker-agent::veklom-treasury").
  2. Checks the identity status — QUARANTINED agents are denied.
  3. Commits a `commit_intent` (pre-execution certificate) to the PGL ledger,
     recording genome_hash, constitution_hash, and the payment intent payload.
  4. Returns a PGLContext object containing the pre_cert_id and pgl_identity_id
     for downstream attest_outcome after confirmation.
  5. After payment confirms (or fails), `attest_outcome` or `register_rollback`
     is called to close the PGL certificate chain.

Architecture note:
  PGLClient.commit_intent() uses `flush` not `commit` — the surrounding
  BankerAgent DB session owns the transaction. We commit once at the end.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.pgl_client import PGLClient

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Canonical Banker Agent identity constants
# ─────────────────────────────────────────────────────────────────────────────

# This actor_id must exist in pgl_identities (auto-seeded on first run below).
BANKER_AGENT_ACTOR_ID    = "banker-agent::veklom-treasury"
BANKER_AGENT_WORKSPACE   = "veklom-system::banker"

# Constitution hash: keccak256 of the hard-coded behavioral rules for this agent.
# If the rules change, this hash changes and the ledger shows the divergence.
_CONSTITUTION_TEXT = (
    "BankerAgent may only spend USDC to treasury addresses resolved from "
    "VEKLOM_TREASURY_ADDRESS. Daily cap = BANKER_AGENT_DAILY_LIMIT_USDC. "
    "No payment executes without a valid PGL pre-execution certificate. "
    "Every spend is recorded to agent_wallet_ledger before broadcast."
)
BANKER_CONSTITUTION_HASH = hashlib.sha256(_CONSTITUTION_TEXT.encode()).hexdigest()

# Genome hash: keccak256 of this file's module identity (stable per version).
BANKER_GENOME_HASH = hashlib.sha256(
    b"banker-agent:genome:v1.0:veklom-treasury-payments"
).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class BankerAgentPGLError(Exception):
    """
    Raised when the PGL gate HARD BLOCKS a Banker Agent payment.
    The payment will NOT proceed. This is intentional — it is the enforcement
    of the 'every agent goes through PGL' contract.
    """
    pass


# ─────────────────────────────────────────────────────────────────────────────
# PGL context returned after a successful gate-check
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BankerPGLContext:
    """Carries PGL certificate IDs across the pay_for_route lifecycle."""
    pgl_identity_id:           str
    workspace_id:              str
    actor_id:                  str
    pre_execution_cert_id:     str
    genome_hash:               str
    constitution_hash:         str
    intent_hash:               str


# ─────────────────────────────────────────────────────────────────────────────
# Guard implementation
# ─────────────────────────────────────────────────────────────────────────────

class BankerAgentPGLGuard:
    """
    Hard PGL gate for the Banker Agent.

    Call `await BankerAgentPGLGuard.require(db, route, amount_usdc, to_address)`
    at the START of every BankerAgentService payment method.

    If this raises BankerAgentPGLError → the payment is blocked, full stop.
    """

    @staticmethod
    async def _ensure_pgl_identity(db: AsyncSession) -> str:
        """
        Resolve the Banker Agent's PGL identity ID from the database.
        If no identity row exists, seeds one automatically (idempotent).
        Returns the pgl_identity id string.
        """
        from sqlalchemy import select
        from backend.db.models.pgl import PGLIdentity

        # Try to find existing identity
        result = await db.execute(
            select(PGLIdentity).where(PGLIdentity.id == BANKER_AGENT_ACTOR_ID)
        )
        identity = result.scalar_one_or_none()

        if identity is None:
            # Auto-seed the banker agent's PGL identity on first run
            logger.info(
                "[BankerPGL] Seeding Banker Agent PGL identity (first-time setup)..."
            )
            import base64
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

            priv_key   = Ed25519PrivateKey.generate()
            pub_key    = priv_key.public_key()
            pub_bytes  = pub_key.public_bytes_raw()
            pub_b64    = base64.b64encode(pub_bytes).decode()

            identity = PGLIdentity(
                id                 = BANKER_AGENT_ACTOR_ID,
                tenant_id          = BANKER_AGENT_WORKSPACE,
                primary_public_key = pub_b64,
                key_type           = "ed25519",
                metadata_json      = {
                    "status":      "ACTIVE",
                    "agent_type":  "banker",
                    "description": "Autonomous treasury payment agent — Veklom x402 settlement",
                    "genome_hash": BANKER_GENOME_HASH,
                    "constitution_hash": BANKER_CONSTITUTION_HASH,
                    "seeded_automatically": True,
                }
            )
            db.add(identity)
            await db.flush()
            logger.info(
                f"[BankerPGL] ✅ Banker Agent PGL identity seeded: {BANKER_AGENT_ACTOR_ID}"
            )

        # Check containment / quarantine
        meta = identity.metadata_json or {}
        status = meta.get("status", "ACTIVE")
        if status == "QUARANTINED":
            containment_reason = meta.get("containment_reason", "Unknown reason")
            raise BankerAgentPGLError(
                f"Banker Agent is QUARANTINED in PGL and cannot execute payments. "
                f"Reason: {containment_reason}. "
                f"Contact a Veklom admin to lift quarantine via POST /api/v1/pgl/{BANKER_AGENT_ACTOR_ID}/quarantine."
            )

        if status not in ("ACTIVE", "active"):
            raise BankerAgentPGLError(
                f"Banker Agent PGL identity status is '{status}' — not ACTIVE. "
                f"Cannot execute payments."
            )

        return identity.id

    @staticmethod
    def _build_intent_hash(route: str, amount_usdc: float, to_address: str) -> str:
        """
        SHA-256 of the payment intent — used as plan_hash in the PGL certificate.
        Ties this specific payment to the ledger record cryptographically.
        """
        intent_body = json.dumps({
            "route":        route,
            "amount_usdc":  amount_usdc,
            "to_address":   to_address.lower(),
        }, sort_keys=True)
        return hashlib.sha256(intent_body.encode()).hexdigest()

    @staticmethod
    async def require(
        db:           AsyncSession,
        route:        str,
        amount_usdc:  float,
        to_address:   str,
        purpose:      str = "x402_payment",
    ) -> BankerPGLContext:
        """
        HARD GATE — must be called before any payment is executed.

        Resolves the Banker Agent's PGL identity, checks it is ACTIVE,
        and commits a pre-execution certificate to the PGL ledger.

        Args:
            db:           Async DB session (for PGL certificate persistence).
            route:        API route being paid for (audit label).
            amount_usdc:  Payment amount (included in intent hash).
            to_address:   Recipient address (included in intent hash).
            purpose:      Short label for the PGL plan_hash context.

        Returns:
            BankerPGLContext with pre_cert_id for post-execution attestation.

        Raises:
            BankerAgentPGLError: If identity resolution or status check fails.
                                 Payment MUST NOT proceed if this is raised.
        """
        logger.info(
            f"[BankerPGL] 🔐 PGL gate check — route={route} amount={amount_usdc} USDC"
        )

        # 1. Resolve / seed PGL identity — hard block on failure
        try:
            pgl_identity_id = await BankerAgentPGLGuard._ensure_pgl_identity(db)
        except BankerAgentPGLError:
            raise
        except Exception as exc:
            raise BankerAgentPGLError(
                f"PGL identity resolution failed for Banker Agent — payment blocked. "
                f"Error: {exc}"
            ) from exc

        # 2. Build intent hash (plan_hash in PGL certificate)
        intent_hash = BankerAgentPGLGuard._build_intent_hash(route, amount_usdc, to_address)

        # 3. Commit pre-execution certificate to PGL ledger
        pgl = PGLClient(db=db)
        try:
            pre_cert = await pgl.commit_intent(
                workspace_id        = BANKER_AGENT_WORKSPACE,
                actor_id            = BANKER_AGENT_ACTOR_ID,
                genome_hash         = BANKER_GENOME_HASH,
                constitution_hash   = BANKER_CONSTITUTION_HASH,
                plan_hash           = intent_hash,
                tool_manifest_hash  = hashlib.sha256(b"tools:usdc-transfer:erc20:base-mainnet").hexdigest(),
                input_hash          = hashlib.sha256(
                    f"{route}:{amount_usdc}:{to_address}:{purpose}".encode()
                ).hexdigest(),
                scope               = "wallet:spend",
            )
        except Exception as exc:
            raise BankerAgentPGLError(
                f"PGL commit_intent failed — cannot issue pre-execution certificate. "
                f"Payment blocked. Error: {exc}"
            ) from exc

        pre_cert_id = pre_cert["pre_execution_certificate_id"]
        logger.info(
            f"[BankerPGL] ✅ Pre-execution certificate issued: {pre_cert_id} "
            f"(persisted={pre_cert.get('persisted', False)})"
        )

        return BankerPGLContext(
            pgl_identity_id       = pgl_identity_id,
            workspace_id          = BANKER_AGENT_WORKSPACE,
            actor_id              = BANKER_AGENT_ACTOR_ID,
            pre_execution_cert_id = pre_cert_id,
            genome_hash           = BANKER_GENOME_HASH,
            constitution_hash     = BANKER_CONSTITUTION_HASH,
            intent_hash           = intent_hash,
        )

    @staticmethod
    async def attest_success(
        db:          AsyncSession,
        pgl_ctx:     BankerPGLContext,
        tx_hash:     str,
        block_number: int,
    ) -> None:
        """
        Called after a payment is confirmed on-chain.
        Closes the PGL certificate chain with a post-execution attestation.

        output_hash  = SHA-256 of the confirmed tx_hash
        outcome_hash = SHA-256 of {tx_hash, block_number, status=confirmed}
        """
        output_hash  = hashlib.sha256(tx_hash.encode()).hexdigest()
        outcome_body = json.dumps({
            "tx_hash":      tx_hash,
            "block_number": block_number,
            "status":       "confirmed",
        }, sort_keys=True)
        outcome_hash = hashlib.sha256(outcome_body.encode()).hexdigest()

        pgl = PGLClient(db=db)
        try:
            post_cert = await pgl.attest_outcome(
                pre_execution_certificate_id = pgl_ctx.pre_execution_cert_id,
                output_hash                  = output_hash,
                outcome_hash                 = outcome_hash,
                operator_state_attestation   = {
                    "tx_hash":      tx_hash,
                    "block_number": block_number,
                    "chain_id":     8453,
                    "network":      "base-mainnet",
                    "status":       "confirmed",
                },
                workspace_id = pgl_ctx.workspace_id,
                actor_id     = pgl_ctx.actor_id,
            )
            logger.info(
                f"[BankerPGL] ✅ Post-execution certificate issued: "
                f"{post_cert['post_execution_certificate_id']} "
                f"(persisted={post_cert.get('persisted', False)})"
            )
        except Exception as exc:
            # Attestation failure is a warning, NOT a hard block (payment already confirmed)
            logger.error(
                f"[BankerPGL] ⚠️  attest_outcome failed (payment confirmed, ledger gap): {exc}"
            )

    @staticmethod
    async def attest_failure(
        db:      AsyncSession,
        pgl_ctx: BankerPGLContext,
        reason:  str,
    ) -> None:
        """
        Called when a payment fails (signing, broadcast, or confirmation timeout).
        Registers a rollback event in the PGL ledger so the pre-cert is closed.
        """
        pgl = PGLClient(db=db)
        try:
            # We need a pseudo post-cert to register rollback against
            # Use a synthetic post-cert tied to the pre-cert
            pseudo_post_cert = f"pgl_cert_post_failed_{uuid.uuid4().hex[:12]}"
            from backend.db.models.pgl import PGLCertificate
            db.add(PGLCertificate(
                certificate_id        = pseudo_post_cert,
                kind                  = "post",
                workspace_id          = pgl_ctx.workspace_id,
                actor_id              = pgl_ctx.actor_id,
                pgl_identity_id       = pgl_ctx.pgl_identity_id,
                pre_certificate_id    = pgl_ctx.pre_execution_cert_id,
                output_hash           = hashlib.sha256(b"failed").hexdigest(),
                outcome_hash          = hashlib.sha256(reason.encode()).hexdigest(),
                status                = "failed",
            ))
            await db.flush()
            await pgl.register_rollback(
                post_execution_certificate_id = pseudo_post_cert,
                reason                        = reason,
            )
            logger.warning(
                f"[BankerPGL] 📋 Rollback registered for pre-cert "
                f"{pgl_ctx.pre_execution_cert_id}: {reason}"
            )
        except Exception as exc:
            logger.error(f"[BankerPGL] Failed to register PGL rollback: {exc}")
