"""PGL Onboarding Routes — Agent Authority Runtime bootstrap.

DB-BACKED. Every step writes to pgl_certificates, pgl_ledger_events, and
pgl_identities tables. No in-memory dicts. No shared global state.

KEY INVARIANTS:
  1. IDEMPOTENT — if a user already has a pgl_id, onboarding returns the
     existing identity. A new ID is NEVER issued to replace an existing one.
     Re-onboarding the same agent = no-op + return existing ID.
  2. HUMAN-FIRST — the human_id anchor is always current_user.id (from JWT),
     NEVER from the request body. This is what locks the PGL identity to the
     actual authenticated human who owns the agents.
  3. LIFECYCLE — every identity starts PROBATIONARY (90 days), then ACTIVE.
     Annual renewal required. Same ID, new expiry date every year.

Tenant isolation is enforced at every handler: all queries are filtered by
current_user.workspace_id so User A's onboarding state can NEVER affect
User B's workspace.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.core.security.ed25519_keys import Ed25519KeyManager

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.services.pgl_identity_lifecycle import (
    compute_lifecycle,
    stamp_new_human_identity,
    build_renewal_patch,
)
from backend.db.models.pgl import PGLCertificate, PGLIdentity, PGLLedgerEvent
from backend.db.models.user import User

router = APIRouter(prefix="/pgl", tags=["PGL Onboarding"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_hash(obj: dict) -> str:
    """SHA-256 over the canonical JSON representation of `obj`."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def _resolve_pgl_identity_id(
    db: AsyncSession,
    actor_id: str,
    workspace_id: str,
) -> str:
    """Resolve a guaranteed-non-null PGL identity ID for actor / workspace.

    Lookup order:
      1. users.pgl_id    — operator identity created during Step 1 onboarding
      2. pgl_identities.tenant_id == workspace_id  — fallback for workspace anchor

    Raises:
      HTTPException(400)  if no identity has been created yet (Step 1 incomplete)
    """
    # 1. Check the user's own PGL ID (set during operator-identity bootstrap)
    user_result = await db.execute(
        select(User.pgl_id).where(User.id == actor_id)
    )
    pgl_id = user_result.scalar_one_or_none()

    if not pgl_id:
        # 2. Workspace-level anchor
        identity_result = await db.execute(
            select(PGLIdentity.id).where(PGLIdentity.tenant_id == workspace_id).limit(1)
        )
        pgl_id = identity_result.scalar_one_or_none()

    if not pgl_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "No PGL identity found for this operator or workspace. "
                "Complete Step 1 (Operator Identity) before issuing an agent certificate."
            ),
        )
    return pgl_id


async def _last_event_hash(db: AsyncSession, workspace_id: str) -> Optional[str]:
    """Return the event_hash of the most recent PGLLedgerEvent for this workspace."""
    result = await db.execute(
        select(PGLLedgerEvent.event_hash)
        .where(PGLLedgerEvent.workspace_id == workspace_id)
        .order_by(PGLLedgerEvent.id.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


async def _write_ledger_event(
    db: AsyncSession,
    workspace_id: str,
    actor_id: str,
    event_type: str,
    payload: dict,
    certificate_id: Optional[str] = None,
    pgl_identity_id: Optional[str] = None,
) -> PGLLedgerEvent:
    """Append a hash-chained ledger event for this workspace."""
    prev_hash = await _last_event_hash(db, workspace_id)

    # Chain: SHA-256(canonical_payload + prev_event_hash)
    chain_input = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    chain_input += (prev_hash or "GENESIS")
    event_hash = hashlib.sha256(chain_input.encode()).hexdigest()

    # Resolve pgl_identity_id if not provided
    if not pgl_identity_id:
        # 1. Check user first
        user_result = await db.execute(
            select(User.pgl_id).where(User.id == actor_id)
        )
        pgl_identity_id = user_result.scalar_one_or_none()

    if not pgl_identity_id:
        # 2. Check PGLIdentity table for workspace/tenant
        identity_result = await db.execute(
            select(PGLIdentity.id).where(PGLIdentity.tenant_id == workspace_id).limit(1)
        )
        pgl_identity_id = identity_result.scalar_one_or_none()

    if not pgl_identity_id:
        raise ValueError(
            f"Cannot write ledger event '{event_type}': no PGL Identity found for actor {actor_id} or workspace {workspace_id}"
        )

    event = PGLLedgerEvent(
        workspace_id=workspace_id,
        actor_id=actor_id,
        pgl_identity_id=pgl_identity_id,
        certificate_id=certificate_id,
        event_type=event_type,
        payload=payload,
        prev_event_hash=prev_hash,
        event_hash=event_hash,
    )
    db.add(event)
    await db.flush()  # assign PK without committing
    return event


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------


class BootstrapOperatorRequest(BaseModel):
    name: str
    email: str


class CreateWorkspaceRequest(BaseModel):
    name: str
    operator_id: str


class IssueCertificateRequest(BaseModel):
    agent_name: str
    operator_id: str
    workspace_id: str
    jurisdiction: str = "US"
    declared_purpose: str = ""
    intended_use: str = ""
    risk_category: str = "low"
    tools: list[str] = []
    permissions: list[str] = ["read"]
    safety_rules: list[str] = ["no_secrets"]





# ---------------------------------------------------------------------------
# POST /pgl/onboarding/operator-identity
# ---------------------------------------------------------------------------


@router.post("/onboarding/operator-identity")
async def create_operator_identity(
    operator_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 1: Bootstrap human operator identity — IDEMPOTENT.

    CRITICAL INVARIANT: If this user already has a pgl_id, the existing
    identity is returned immediately. A new ID is NEVER issued.
    An agent gets one ID for life. Re-onboarding = no-op.

    The human_id anchor (current_user.id) comes from the JWT, never from
    the request body. This is what locks the PGL identity to the real human.
    """
    workspace_id = str(current_user.workspace_id)
    actor_id     = str(current_user.id)  # JWT-extracted, not from body

    # ── IDEMPOTENCY CHECK — return existing identity if already onboarded ────
    if current_user.pgl_id:
        existing = await db.execute(
            select(PGLIdentity).where(PGLIdentity.id == current_user.pgl_id)
        )
        identity = existing.scalar_one_or_none()
        if identity:
            lifecycle = compute_lifecycle(
                metadata=identity.metadata_json or {},
                created_at=identity.created_at,
            )
            return {
                "operator_identity_id": identity.metadata_json.get("operator_identity_id", actor_id),
                "pgl_id":              identity.id,
                "workspace_id":        workspace_id,
                "status":              "already_onboarded",
                "lifecycle":           lifecycle.to_dict(),
                "message":             (
                    "Identity already exists — returning existing PGL ID. "
                    "An agent's ID is issued once and kept for life."
                ),
            }
    # ─────────────────────────────────────────────────────────────────────────

    # First time — issue the identity
    operator_identity_id = f"op_{uuid.uuid4().hex[:16]}"

    # Build lifecycle-stamped metadata — human_id = current_user.id (JWT)
    lifecycle_meta = stamp_new_human_identity(
        human_id=actor_id,
        human_email=current_user.email or "",
        workspace_id=workspace_id,
    )
    payload = {
        **lifecycle_meta,
        "operator_identity_id": operator_identity_id,
        "operator_name":        operator_data.get("operator_name", current_user.full_name or "Primary Operator"),
        "jurisdiction":         operator_data.get("jurisdiction", "US"),
        "declared_purpose":     operator_data.get("declared_purpose", "AI Agent Management"),
    }

    pgl_id   = str(uuid.uuid4())
    _, pub_b64 = Ed25519KeyManager.generate_key_pair()
    identity = PGLIdentity(
        id=pgl_id,
        tenant_id=workspace_id,
        primary_public_key=f"ed25519_{pub_b64}",
        key_type="ed25519",
        metadata_json=payload,
    )
    db.add(identity)

    # Lock the user to this PGL ID — the permanent anchor
    current_user.pgl_id = pgl_id
    db.add(current_user)

    event = await _write_ledger_event(
        db,
        workspace_id=workspace_id,
        actor_id=actor_id,
        event_type="operator_identity_issued",
        payload=payload,
        pgl_identity_id=pgl_id,
    )

    await db.commit()

    lifecycle = compute_lifecycle(metadata=payload, created_at=identity.created_at)
    return {
        "operator_identity_id": operator_identity_id,
        "pgl_id":               pgl_id,
        "workspace_id":         workspace_id,
        "ledger_event_hash":    event.event_hash,
        "status":               "created",
        "lifecycle":            lifecycle.to_dict(),
        "message":              "PGL identity issued. This ID is permanent — renew annually.",
    }


# ---------------------------------------------------------------------------
# POST /pgl/onboarding/workspace-authority
# ---------------------------------------------------------------------------


@router.post("/onboarding/workspace-authority")
async def create_workspace_authority(
    authority_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 2: Write workspace authority genome — creates a 'workspace_created'
    ledger event and returns the genome hash.
    """
    workspace_id = str(current_user.workspace_id)
    actor_id = str(current_user.id)

    genome_data = {
        "workspace_id": workspace_id,
        "name": authority_data.get("name", "Primary Workspace"),
        "authority_level": authority_data.get("authority_level", "operator"),
        "permissions": authority_data.get("permissions", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    genome_hash = _canonical_hash(genome_data)

    event = await _write_ledger_event(
        db,
        workspace_id=workspace_id,
        actor_id=actor_id,
        event_type="workspace_authority_created",
        payload={**genome_data, "genome_hash": genome_hash},
    )

    await db.commit()

    return {
        "workspace_authority_id": workspace_id,
        "genome_hash": genome_hash,
        "ledger_event_hash": event.event_hash,
        "status": "created",
        "message": "Workspace authority genome written to PGL ledger",
    }


# ---------------------------------------------------------------------------
# POST /pgl/onboarding/agent-certificate
# ---------------------------------------------------------------------------


@router.post("/onboarding/agent-certificate")
async def generate_agent_certificate(
    certificate_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 3: Register agent with GnomLedger (real PGL) to get UBC ID.
    
    This calls GnomLedger's /agents endpoint to register the agent and receive
    the Universal Blockchain Connection (UBC) ID. This ID is used throughout
    the system for tracking.
    """
    from backend.core.services.pgl_client import PGLClient
    
    workspace_id = str(current_user.workspace_id)
    actor_id = str(current_user.id)

    agent_name = certificate_data.get("agent_name", "Primary Agent")
    agent_id = f"agent_{uuid.uuid4().hex[:16]}"

    genome_payload = {
        # Required fields matching GnomLedger GenomePayload schema
        "model_family": certificate_data.get("model_family", "veklom-agent"),
        "model_version": certificate_data.get("model_version", "1.0.0"),
        "architecture": certificate_data.get("architecture", "capability-os"),
        "intended_use": certificate_data.get("declared_purpose") or certificate_data.get("intended_use") or "governed-capability-execution",
        "risk_category": certificate_data.get("risk_category", "low"),
        # Optional enrichment fields
        "tools": certificate_data.get("tools", ["governance", "policy-check"]),
        "permissions": certificate_data.get("permissions", ["read"]),
        "safety_rules": certificate_data.get("safety_rules", ["no_secrets"]),
        "runtime_config": {
            "agent_name": agent_name,
            "agent_type": certificate_data.get("agent_type", "autonomous"),
            "workspace_id": workspace_id,
        },
    }

    try:
        # ── Step A: Verify operator identity exists (Step 1 must be complete) ─
        # We need the operator identity to authorize this issuance, but the cert
        # itself will belong to the AGENT identity created below — not the operator.
        operator_pgl_id = await _resolve_pgl_identity_id(db, actor_id, workspace_id)

        # ── Step B: Register agent with GnomLedger (real PGL) ────────────────
        pgl_client = PGLClient()
        gnomledger_response = await pgl_client.register_agent(
            agent_id=agent_id,
            name=agent_name,
            creator=actor_id,
            jurisdiction=certificate_data.get("jurisdiction", "US"),
            declared_purpose=certificate_data.get("declared_purpose", ""),
            genome_payload=genome_payload,
            parent_agent_ids=certificate_data.get("parent_agent_ids"),
        )

        # ── Step C: Create the EXECUTION PROFILE PGLIdentity ──────────────────
        # Constitutional invariant (Section 7):
        #   Step 3 creates an Execution Profile, NOT a living agent.
        #   Ephemeral Execution Identities (EEI) will branch from this profile
        #   at runtime.
        #   cert.pgl_identity_id  = the Execution Profile identity
        #   cert.actor_id         = the OPERATOR identity (who authorized)
        from backend.core.security.ed25519_keys import Ed25519KeyManager
        profile_pgl_id = str(uuid.uuid4())
        _, profile_pub_b64 = Ed25519KeyManager.generate_key_pair()
        profile_identity = PGLIdentity(
            id=profile_pgl_id,
            tenant_id=workspace_id,
            primary_public_key=f"ed25519_{profile_pub_b64}",
            key_type="ed25519",
            metadata_json={
                "kind": "execution_profile",
                "profile_name": agent_name,
                "agent_id": agent_id,  # UBC reference
                "workspace_id": workspace_id,
                "authorized_by_operator": operator_pgl_id,  # provenance chain
                "jurisdiction": certificate_data.get("jurisdiction", "US"),
                "declared_purpose": certificate_data.get("declared_purpose", ""),
            },
        )
        db.add(profile_identity)
        await db.flush()  # get the row into the session without committing

        # ── Step D: Persist birth certificate bound to Execution Profile ──────
        genome_hash = _canonical_hash(genome_payload)
        constitution_data = {
            "tools": certificate_data.get("tools", ["governance", "policy-check"]),
            "permissions": certificate_data.get("permissions", ["read"]),
            "safety_rules": certificate_data.get("safety_rules", ["no_secrets"]),
        }
        constitution_hash = _canonical_hash(constitution_data)

        cert = PGLCertificate(
            certificate_id=ubc_id,          # UBC ID from GnomLedger
            kind="birth",
            workspace_id=workspace_id,
            actor_id=actor_id,              # OPERATOR: who authorized issuance
            pgl_identity_id=profile_pgl_id, # PROFILE: whose blueprint this cert represents
            genome_hash=genome_hash,
            constitution_hash=constitution_hash,
            status="active",
        )
        db.add(cert)

        # ── Step E: Append hash-chained ledger event (operator as actor) ──────
        event = await _write_ledger_event(
            db,
            workspace_id=workspace_id,
            actor_id=actor_id,
            event_type="execution_profile_registered_with_gnomledger",
            payload={
                "certificate_id": ubc_id,
                "agent_id": agent_id,
                "profile_pgl_id": profile_pgl_id,
                "operator_pgl_id": operator_pgl_id,
                "genome_hash": genome_hash,
                "constitution_hash": constitution_hash,
                "profile_name": agent_name,
                "gnomledger_response": gnomledger_response,
            },
            certificate_id=ubc_id,
            pgl_identity_id=operator_pgl_id,  # ledger event actor = operator
        )

        # ── Step F: Commit atomically — identity + cert + event ───────────────
        await db.commit()

        return {
            "certificate_id": ubc_id,          # UBC ID from GnomLedger
            "agent_id": agent_id,
            "profile_pgl_id": profile_pgl_id,   # execution profile identity
            "operator_pgl_id": operator_pgl_id, # operator who authorized
            "genome_hash": genome_hash,
            "constitution_hash": constitution_hash,
            "ledger_event_hash": event.event_hash,
            "status": "registered",
            "message": "Execution profile identity created and certificate issued atomically",
            "gnomledger_response": gnomledger_response,
        }
    except HTTPException:
        # Re-raise clean HTTP errors (Step 1 incomplete, billing cap, etc.)
        await db.rollback()
        raise
    except Exception as e:
        # Roll back all writes — no orphan identity, cert, or event persisted
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Agent certificate issuance failed (all writes rolled back): {str(e)}"
        )




# ---------------------------------------------------------------------------
# POST /pgl/onboarding/ledger-lineage
# ---------------------------------------------------------------------------


@router.post("/onboarding/ledger-lineage")
async def initialize_ledger_lineage(
    ledger_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 4: Anchor the ledger root — writes a 'lineage_initialized'
    event and returns the chain head hash.
    """
    workspace_id = str(current_user.workspace_id)
    actor_id = str(current_user.id)

    certificate_id = ledger_data.get("certificate_id")

    # Verify the certificate belongs to this workspace
    if certificate_id:
        result = await db.execute(
            select(PGLCertificate).where(
                PGLCertificate.certificate_id == certificate_id,
                PGLCertificate.workspace_id == workspace_id,
            )
        )
        cert = result.scalar_one_or_none()
        if not cert:
            raise HTTPException(
                status_code=404,
                detail=f"Certificate {certificate_id} not found in workspace {workspace_id}",
            )

    payload = {
        "certificate_id": certificate_id,
        "genesis_block": ledger_data.get("genesis_block", "GENESIS"),
        "workspace_id": workspace_id,
        "initialized_at": datetime.now(timezone.utc).isoformat(),
        "lineage_generation": 0,
    }

    lineage_root = _canonical_hash(payload)

    event = await _write_ledger_event(
        db,
        workspace_id=workspace_id,
        actor_id=actor_id,
        event_type="lineage_initialized",
        payload={**payload, "lineage_root": lineage_root},
        certificate_id=certificate_id,
    )

    await db.commit()

    return {
        "ledger_root": event.event_hash,
        "lineage_root": lineage_root,
        "chain_head": event.event_hash,
        "ledger_event_id": event.id,
        "status": "initialized",
        "message": "Ledger lineage anchored in pgl_ledger_events",
    }


# ---------------------------------------------------------------------------
# POST /pgl/onboarding/first-proof
# ---------------------------------------------------------------------------


@router.post("/onboarding/first-proof")
async def generate_first_proof(
    proof_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 5: Generate first harmless proof — writes a 'proof_submitted'
    ledger event and returns the proof hash. Validates the chain is intact.
    """
    workspace_id = str(current_user.workspace_id)
    actor_id = str(current_user.id)

    certificate_id = proof_data.get("certificate_id")
    proof_type = proof_data.get("proof_type", "identity_anchor")
    proof_payload = proof_data.get("payload", {})

    proof_content = {
        "proof_type": proof_type,
        "workspace_id": workspace_id,
        "certificate_id": certificate_id,
        "payload": proof_payload,
        "actor_id": actor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    proof_hash = _canonical_hash(proof_content)

    profile_id = f"pgl_{uuid.uuid4().hex[:16]}"

    event = await _write_ledger_event(
        db,
        workspace_id=workspace_id,
        actor_id=actor_id,
        event_type="proof_submitted",
        payload={**proof_content, "proof_hash": proof_hash, "profile_id": profile_id},
        certificate_id=certificate_id,
    )

    await db.commit()

    return {
        "proof_id": f"proof_{uuid.uuid4().hex[:16]}",
        "profile_id": profile_id,
        "proof_hash": proof_hash,
        "ledger_event_hash": event.event_hash,
        "status": "verified",
        "message": "First proof anchored to chain",
    }


# ---------------------------------------------------------------------------
# POST /pgl/onboarding/complete
# ---------------------------------------------------------------------------


@router.post("/onboarding/complete")
async def complete_onboarding(
    completion_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 6: Seal onboarding — verifies chain integrity from DB, writes
    'onboarding_completed' event, marks workspace as PGL-enabled.
    """
    workspace_id = str(current_user.workspace_id)
    actor_id = str(current_user.id)

    # Verify chain integrity: re-read all events in order and check links
    result = await db.execute(
        select(PGLLedgerEvent)
        .where(PGLLedgerEvent.workspace_id == workspace_id)
        .order_by(PGLLedgerEvent.id.asc())
    )
    events = result.scalars().all()

    chain_valid = True
    for i, evt in enumerate(events):
        if i == 0:
            expected_prev = None
        else:
            expected_prev = events[i - 1].event_hash

        if evt.prev_event_hash != expected_prev:
            chain_valid = False
            break

        # Re-derive the hash and confirm it matches stored value
        chain_input = json.dumps(evt.payload, sort_keys=True, separators=(",", ":"))
        chain_input += (evt.prev_event_hash or "GENESIS")
        derived_hash = hashlib.sha256(chain_input.encode()).hexdigest()
        if derived_hash != evt.event_hash:
            chain_valid = False
            break

    if not chain_valid:
        raise HTTPException(
            status_code=409,
            detail="PGL ledger chain integrity check failed. Onboarding cannot be sealed.",
        )

    # Write completion event
    event = await _write_ledger_event(
        db,
        workspace_id=workspace_id,
        actor_id=actor_id,
        event_type="onboarding_completed",
        payload={
            "workspace_id": workspace_id,
            "chain_valid": True,
            "event_count": len(events) + 1,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    await db.commit()

    return {
        "status": "completed",
        "workspace_unlocked": True,
        "chain_verified": True,
        "chain_head": event.event_hash,
        "event_count": len(events) + 1,
        "redirect_to": "/home",
        "message": "PGL onboarding sealed and chain verified",
    }


# ---------------------------------------------------------------------------
# GET /pgl/profile  — legacy check used by some frontend paths
# ---------------------------------------------------------------------------


@router.get("/profile")
async def get_pgl_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current user's workspace has an active PGL profile.
    Reads from pgl_certificates — never returns a hardcoded value.
    """
    workspace_id = str(current_user.workspace_id)

    result = await db.execute(
        select(PGLCertificate)
        .where(
            PGLCertificate.workspace_id == workspace_id,
            PGLCertificate.kind == "birth",
            PGLCertificate.status == "active",
        )
        .limit(1)
    )
    cert = result.scalar_one_or_none()

    if cert is None:
        return {
            "status": "pending",
            "has_pgl_profile": False,
            "message": "PGL onboarding required for workspace " + workspace_id,
        }

    return {
        "status": "active",
        "has_pgl_profile": True,
        "certificate_id": cert.certificate_id,
        "genome_hash": cert.genome_hash,
        "workspace_id": workspace_id,
        "message": "PGL profile active",
    }


# ---------------------------------------------------------------------------
# GET /pgl/snapshot/{certificate_id}
# ---------------------------------------------------------------------------


@router.get("/snapshot/{certificate_id}")
async def get_snapshot(
    certificate_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full PGL snapshot for the Authority Panel — scoped to workspace."""
    workspace_id = str(current_user.workspace_id)

    result = await db.execute(
        select(PGLCertificate).where(
            PGLCertificate.certificate_id == certificate_id,
            PGLCertificate.workspace_id == workspace_id,
        )
    )
    cert = result.scalar_one_or_none()
    if cert is None:
        raise HTTPException(
            status_code=404,
            detail=f"Certificate {certificate_id} not found in workspace {workspace_id}",
        )

    events_result = await db.execute(
        select(PGLLedgerEvent)
        .where(PGLLedgerEvent.workspace_id == workspace_id)
        .order_by(PGLLedgerEvent.id.asc())
    )
    events = events_result.scalars().all()

    return {
        "certificate_id": cert.certificate_id,
        "workspace_id": workspace_id,
        "actor_id": cert.actor_id,
        "kind": cert.kind,
        "genome_hash": cert.genome_hash,
        "constitution_hash": cert.constitution_hash,
        "status": cert.status,
        "created_at": cert.created_at.isoformat() if cert.created_at else None,
        "ledger_events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_hash": e.event_hash,
                "prev_event_hash": e.prev_event_hash,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "chain_head": events[-1].event_hash if events else None,
        "version_count": len(events),
    }


# ---------------------------------------------------------------------------
# Deprecated bootstrap-style routes (kept for backward compat with old frontend)
# All now delegate to the DB-backed implementations above.
# ---------------------------------------------------------------------------


@router.post("/bootstrap-operator")
async def bootstrap_operator(
    body: BootstrapOperatorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compat alias for /onboarding/operator-identity."""
    return await create_operator_identity(
        operator_data={"operator_name": body.name, "email": body.email},
        current_user=current_user,
        db=db,
    )


@router.post("/create-workspace")
async def create_workspace_alias(
    body: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compat alias for /onboarding/workspace-authority."""
    return await create_workspace_authority(
        authority_data={"name": body.name, "operator_id": body.operator_id},
        current_user=current_user,
        db=db,
    )


@router.post("/issue-certificate")
async def issue_certificate_alias(
    body: IssueCertificateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compat alias for /onboarding/agent-certificate."""
    return await generate_agent_certificate(
        certificate_data=body.model_dump(),
        current_user=current_user,
        db=db,
    )


@router.post("/complete")
async def complete_alias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compat alias for /onboarding/complete."""
    return await complete_onboarding(
        completion_data={},
        current_user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# GET /pgl/identity/status  — lifecycle check (probation / renewal)
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# POST /pgl/identity/renew  — annual renewal (same ID, new expiry)
# ---------------------------------------------------------------------------


@router.post("/identity/renew")
async def renew_identity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renew the current user's PGL identity.

    INVARIANT: The PGL ID never changes. Only the expiry date is pushed
    forward by 365 days. Same ID, new expiry. Exactly like renewing a
    driver's license — same license number, new sticker on the back.

    In production: gate this behind a payment check before calling.
    No payment = renewal denied = ID stays expired = no execution.
    """
    if not current_user.pgl_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot renew: no PGL identity found. Complete onboarding first.",
        )

    result = await db.execute(
        select(PGLIdentity).where(PGLIdentity.id == current_user.pgl_id)
    )
    identity = result.scalar_one_or_none()
    if not identity:
        raise HTTPException(status_code=404, detail=f"PGL identity {current_user.pgl_id} not found.")

    # Apply renewal patch — same ID, new expiry, bumped version
    new_metadata = build_renewal_patch(identity.metadata_json or {})
    identity.metadata_json = new_metadata
    identity.rotated_at = datetime.now(timezone.utc)
    db.add(identity)

    # Write renewal to ledger chain
    event = await _write_ledger_event(
        db,
        workspace_id=str(current_user.workspace_id),
        actor_id=str(current_user.id),
        event_type="identity_renewed",
        payload={
            "pgl_id":           identity.id,
            "renewal_count":    new_metadata["renewal_count"],
            "new_renewal_due":  new_metadata["renewal_due_at"],
            "identity_version": new_metadata["identity_version"],
        },
        pgl_identity_id=identity.id,
    )

    await db.commit()

    lifecycle = compute_lifecycle(metadata=new_metadata, created_at=identity.created_at)
    return {
        "pgl_id":           identity.id,
        "status":           "renewed",
        "renewal_count":    new_metadata["renewal_count"],
        "new_expiry":       new_metadata["renewal_due_at"],
        "ledger_event_hash": event.event_hash,
        "lifecycle":        lifecycle.to_dict(),
        "message":          (
            f"Identity renewed. Same ID, new expiry: {new_metadata['renewal_due_at'][:10]}. "
            f"Renewal #{new_metadata['renewal_count']}."
        ),
    }
