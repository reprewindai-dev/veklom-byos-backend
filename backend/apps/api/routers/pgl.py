"""Truthful, fail-closed BYOS-local PGL registry surfaces.

BYOS stores local identity and onboarding state. It does not independently prove
Gnomledger acceptance, cryptographic verification, containment, or settlement.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_admin, get_current_user
from backend.core.services.pgl_identity_lifecycle import compute_lifecycle
from backend.db.models.pgl import PGLCertificate, PGLIdentity, PGLLedgerEvent
from backend.db.models.user import User

router = APIRouter(prefix="/pgl", tags=["PGL Registry"])

NOT_VERIFIED = "NOT_VERIFIED"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
LOCAL_STATE_PRESENT = "LOCAL_STATE_PRESENT"
LOCAL_STATE_ABSENT = "LOCAL_STATE_ABSENT"


@router.get("/registry")
async def get_pgl_registry(db: AsyncSession = Depends(get_db)):
    """Return BYOS-local identity records without canonical-ledger claims."""
    try:
        result = await db.execute(select(PGLIdentity))
        identities = result.scalars().all()

        registry_data = []
        for identity in identities:
            metadata = identity.metadata_json or {}
            registry_data.append(
                {
                    "id": identity.id,
                    "tenant_id": identity.tenant_id,
                    "primary_public_key": identity.primary_public_key,
                    "key_type": identity.key_type,
                    "created_at": (
                        identity.created_at.isoformat() if identity.created_at else None
                    ),
                    "status": metadata.get("status", NOT_VERIFIED),
                    "verification_status": NOT_VERIFIED,
                    "source": "BYOS_LOCAL_STATE",
                    "containment_reason": metadata.get("containment_reason"),
                    "agent_name": metadata.get(
                        "agent_name", metadata.get("operator_name", "Unknown Agent")
                    ),
                    "_links": {
                        "self": {
                            "href": f"/api/v1/pgl/registry/{identity.id}",
                            "method": "GET",
                        },
                        "evidence": {
                            "href": (
                                f"/api/v1/evidence/packs?agent_id={identity.id}"
                            ),
                            "method": "GET",
                        },
                    },
                }
            )

        return registry_data
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch local PGL registry: {str(exc)}",
        ) from exc


@router.post("/{agent_id}/quarantine", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def quarantine_agent(
    agent_id: str,
    reason: str = "Anomalous behavior detected",
    _operator: User = Depends(get_current_admin),
):
    """Fail closed until a governed containment adapter is implemented.

    Authentication and operator authorization are resolved before this function
    runs. The endpoint intentionally performs no database mutation, evidence
    write, connection rewiring, or settlement activity.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "status": NOT_IMPLEMENTED,
            "verification_status": NOT_VERIFIED,
            "agent_id": agent_id,
            "reason": reason,
            "containment_performed": False,
            "settlement_created": False,
            "message": (
                "No governed containment adapter is configured; "
                "the request produced no side effects."
            ),
        },
    )


@router.get("/{agent_id}/genealogy")
async def get_agent_genealogy(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return an honest empty state until durable lineage proof is available."""
    result = await db.execute(
        select(PGLIdentity).where(PGLIdentity.id == agent_id)
    )
    identity = result.scalar_one_or_none()

    if not identity:
        raise HTTPException(
            status_code=404,
            detail="Agent not found in BYOS local PGL registry.",
        )

    return {
        "status": NOT_IMPLEMENTED,
        "verification_status": NOT_VERIFIED,
        "agent_id": agent_id,
        "lineage": None,
        "proof_inputs": [],
        "message": "Durable Gnomledger lineage evidence is unavailable.",
    }


@router.get("/certificate")
async def get_pgl_certificate(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Describe local identity presence without manufacturing a certificate."""
    result = await db.execute(
        select(PGLIdentity).where(PGLIdentity.tenant_id == user.workspace_id)
    )
    identity = result.scalars().first()

    return {
        "workspace_id": str(user.workspace_id),
        "local_identity_present": identity is not None,
        "pgl_cert_id": None,
        "chain_root": None,
        "verified": False,
        "verification_status": NOT_VERIFIED,
        "evidence": [],
        "source": "BYOS_LOCAL_STATE",
    }


@router.get("/trust/records")
async def get_trust_records(
    user: User = Depends(get_current_user),
):
    """Return no trust records when durable anchoring evidence is unavailable."""
    return {
        "workspace_id": str(user.workspace_id),
        "records": [],
        "verification_status": NOT_VERIFIED,
        "source": "BYOS_LOCAL_STATE",
    }


class OnboardingStatusResponse(BaseModel):
    mode: str
    mode_display: str
    has_pgl_profile: bool
    requires_onboarding: bool
    profile: Optional[dict[str, Any]] = None


@router.get("/status", response_model=dict[str, Any])
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return workspace-scoped local onboarding state, not ledger liveness."""
    workspace_id = str(current_user.workspace_id)

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

    ledger_result = await db.execute(
        select(PGLLedgerEvent)
        .where(PGLLedgerEvent.workspace_id == workspace_id)
        .order_by(PGLLedgerEvent.id.asc())
    )
    events = ledger_result.scalars().all()

    snapshot = None
    if cert is not None:
        snapshot = {
            "local_certificate_id": cert.certificate_id,
            "actor_id": cert.actor_id,
            "status": cert.status,
            "created_at": cert.created_at.isoformat() if cert.created_at else None,
            "local_event_count": len(events),
            "verification_status": NOT_VERIFIED,
            "source": "BYOS_LOCAL_STATE",
        }

    mode = LOCAL_STATE_PRESENT if has_profile else LOCAL_STATE_ABSENT
    return {
        "mode": mode,
        "mode_display": (
            "Local PGL state present"
            if has_profile
            else "No local PGL state present"
        ),
        "events": [
            {
                "hash": e.event_hash[:12] + "..." + e.event_hash[-4:] if e.event_hash else "unknown",
                "event": e.event_type,
                "tenant": e.actor_id,
                "time": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "gnomledger_verification": NOT_VERIFIED,
        "has_pgl_profile": has_profile,
        "requires_onboarding": not has_profile,
        "profile": snapshot,
        "workspace_id": workspace_id,
        "message": f"BYOS-local PGL status for workspace {workspace_id}",
    }


@router.get("/identity/status")
async def get_identity_lifecycle_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return advisory local lifecycle state without granting authority."""
    if not current_user.pgl_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "No local PGL identity found. Complete onboarding at "
                "POST /api/v1/pgl/onboarding/operator-identity."
            ),
        )

    result = await db.execute(
        select(PGLIdentity).where(PGLIdentity.id == current_user.pgl_id)
    )
    identity = result.scalar_one_or_none()
    if not identity:
        raise HTTPException(
            status_code=404,
            detail=(
                f"PGL identity {current_user.pgl_id} not found in "
                "BYOS local registry."
            ),
        )

    lifecycle = compute_lifecycle(
        metadata=identity.metadata_json or {},
        created_at=identity.created_at,
    )

    return {
        "pgl_id": identity.id,
        "workspace_id": str(current_user.workspace_id),
        "human_id": (
            identity.metadata_json.get("human_id")
            if identity.metadata_json
            else None
        ),
        "lifecycle": lifecycle.to_dict(),
        "local_lifecycle_can_execute": lifecycle.can_execute,
        "can_execute": False,
        "canonical_execution_authority": NOT_VERIFIED,
        "verification_status": NOT_VERIFIED,
        "warning": lifecycle.warning,
    }
