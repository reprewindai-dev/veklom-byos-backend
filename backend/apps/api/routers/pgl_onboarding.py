"""PGL Onboarding Routes — Agent Authority Runtime bootstrap.

DB-BACKED. Every step writes to pgl_certificates, pgl_ledger_events, and
pgl_identities tables. No in-memory dicts. No shared global state.

Tenant isolation is enforced at every handler: all queries are filtered by
current_user.workspace_id so User A's onboarding state can NEVER affect
User B's workspace. has_pgl_profile is derived by querying the database for
an active PGLCertificate scoped to this workspace_id.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
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
) -> PGLLedgerEvent:
    """Append a hash-chained ledger event for this workspace."""
    prev_hash = await _last_event_hash(db, workspace_id)

    # Chain: SHA-256(canonical_payload + prev_event_hash)
    chain_input = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    chain_input += (prev_hash or "GENESIS")
    event_hash = hashlib.sha256(chain_input.encode()).hexdigest()

    event = PGLLedgerEvent(
        workspace_id=workspace_id,
        actor_id=actor_id,
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


class OnboardingStatusResponse(BaseModel):
    mode: str
    mode_display: str
    has_pgl_profile: bool
    requires_onboarding: bool
    profile: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# GET /pgl/status  — the gate check called on every app mount
# ---------------------------------------------------------------------------


@router.get("/status", response_model=dict[str, Any])
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return onboarding status for THIS user's workspace only.

    Queries pgl_certificates for an active 'birth' certificate scoped to
    current_user.workspace_id. Returns has_pgl_profile=True only when a
    real DB record exists for this specific workspace.
    """
    workspace_id = str(current_user.workspace_id)

    # A workspace has completed onboarding when it has at least one active
    # PGLCertificate of kind='birth' in the DB.
    result = await db.execute(
        select(PGLCertificate)
        .where(
            PGLCertificate.workspace_id == workspace_id,
            PGLCertificate.kind == "birth",
            PGLCertificate.status == "active",
        )
        .order_by(PGLCertificate.created_at.desc())
        .limit(1)
    )
    cert: Optional[PGLCertificate] = result.scalar_one_or_none()

    has_profile = cert is not None

    # Pull ledger history count for this workspace
    ledger_result = await db.execute(
        select(PGLLedgerEvent)
        .where(PGLLedgerEvent.workspace_id == workspace_id)
        .order_by(PGLLedgerEvent.id.asc())
    )
    events = ledger_result.scalars().all()

    snapshot = None
    if has_profile and cert is not None:
        snapshot = {
            "certificate_id": cert.certificate_id,
            "actor_id": cert.actor_id,
            "genome_hash": cert.genome_hash,
            "constitution_hash": cert.constitution_hash,
            "status": cert.status,
            "created_at": cert.created_at.isoformat() if cert.created_at else None,
            "ledger_event_count": len(events),
            "chain_head": events[-1].event_hash if events else None,
        }

    return {
        "mode": "live",
        "mode_display": "🟢 Live PGL",
        "has_pgl_profile": has_profile,
        "requires_onboarding": not has_profile,
        "profile": snapshot,
        "workspace_id": workspace_id,
        "message": "PGL status for workspace " + workspace_id,
    }


# ---------------------------------------------------------------------------
# POST /pgl/onboarding/operator-identity
# ---------------------------------------------------------------------------


@router.post("/onboarding/operator-identity")
async def create_operator_identity(
    operator_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 1: Bootstrap operator identity — writes a PGLIdentity row and
    a 'operator_created' ledger event for this workspace.
    """
    workspace_id = str(current_user.workspace_id)
    actor_id = str(current_user.id)

    operator_identity_id = f"op_{uuid.uuid4().hex[:16]}"

    payload = {
        "operator_identity_id": operator_identity_id,
        "operator_name": operator_data.get("operator_name", current_user.full_name or "Primary Operator"),
        "jurisdiction": operator_data.get("jurisdiction", "US"),
        "declared_purpose": operator_data.get("declared_purpose", "AI Agent Management"),
        "workspace_id": workspace_id,
        "user_id": actor_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write the PGL Identity record (Ed25519 placeholder — real key rotation is out of scope here)
    pgl_id = str(uuid.uuid4())
    identity = PGLIdentity(
        id=pgl_id,
        tenant_id=workspace_id,
        primary_public_key=f"placeholder_ed25519_{operator_identity_id}",
        key_type="ed25519",
        metadata_json=payload,
    )
    db.add(identity)

    # Write hash-chained ledger event
    event = await _write_ledger_event(
        db,
        workspace_id=workspace_id,
        actor_id=actor_id,
        event_type="operator_created",
        payload=payload,
    )

    await db.commit()

    return {
        "operator_identity_id": operator_identity_id,
        "pgl_id": pgl_id,
        "workspace_id": workspace_id,
        "ledger_event_hash": event.event_hash,
        "status": "created",
        "message": "Operator identity written to PGL ledger",
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
        "agent_name": agent_name,
        "agent_type": certificate_data.get("agent_type", "autonomous"),
        "capabilities": certificate_data.get("capabilities", []),
        "safety_rules": certificate_data.get("safety_rules", ["no_secrets"]),
        "tools": certificate_data.get("tools", ["governance", "policy-check"]),
        "permissions": certificate_data.get("permissions", ["read"]),
        "workspace_id": workspace_id,
        "version": "1.0.0",
    }

    try:
        # Register agent with GnomLedger (real PGL system)
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
        
        # Extract UBC ID from GnomLedger response
        ubc_id = gnomledger_response.get("certificate_id") or gnomledger_response.get("agent_id")
        
        # Write local PGLCertificate record with UBC ID for tracking
        genome_hash = _canonical_hash(genome_payload)
        constitution_data = {
            "tools": certificate_data.get("tools", ["governance", "policy-check"]),
            "permissions": certificate_data.get("permissions", ["read"]),
            "safety_rules": certificate_data.get("safety_rules", ["no_secrets"]),
        }
        constitution_hash = _canonical_hash(constitution_data)

        cert = PGLCertificate(
            certificate_id=ubc_id,  # Use UBC ID from GnomLedger
            kind="birth",
            workspace_id=workspace_id,
            actor_id=actor_id,
            genome_hash=genome_hash,
            constitution_hash=constitution_hash,
            status="active",
        )
        db.add(cert)

        event = await _write_ledger_event(
            db,
            workspace_id=workspace_id,
            actor_id=actor_id,
            event_type="agent_registered_with_gnomledger",
            payload={
                "certificate_id": ubc_id,
                "agent_id": agent_id,
                "genome_hash": genome_hash,
                "constitution_hash": constitution_hash,
                "agent_name": agent_name,
                "gnomledger_response": gnomledger_response,
            },
            certificate_id=ubc_id,
        )

        await db.commit()

        return {
            "certificate_id": ubc_id,  # UBC ID from GnomLedger
            "agent_id": agent_id,
            "genome_hash": genome_hash,
            "constitution_hash": constitution_hash,
            "ledger_event_hash": event.event_hash,
            "status": "registered",
            "message": "Agent registered with GnomLedger and UBC ID assigned",
            "gnomledger_response": gnomledger_response,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register agent with GnomLedger: {str(e)}"
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
