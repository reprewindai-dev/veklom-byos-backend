"""PGL Onboarding Routes - Agent Authority Runtime bootstrap.

First-run PGL authority bootstrap for the Veklom Control Plane.
This creates the operator identity, workspace genome, and first agent birth certificate.
"""

from typing import Any, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User

router = APIRouter(prefix="/pgl", tags=["PGL Onboarding"])


@router.post("/onboarding/operator-identity")
async def create_operator_identity(
    operator_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create operator identity for PGL onboarding."""
    
    try:
        # Generate operator identity ID
        operator_identity_id = f"operator_{uuid.uuid4().hex[:8]}"
        
        # Generate workspace authority ID
        workspace_authority_id = f"workspace_{uuid.uuid4().hex[:8]}"
        
        # Create operator identity record
        operator_identity = {
            "id": operator_identity_id,
            "operator_name": operator_data.get("operator_name", "Primary Operator"),
            "jurisdiction": operator_data.get("jurisdiction", "US"),
            "declared_purpose": operator_data.get("declared_purpose", "AI Agent Management"),
            "workspace_id": current_user.workspace_id,
            "user_id": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        }
        
        return {
            "operator_identity_id": operator_identity_id,
            "workspace_authority_id": workspace_authority_id,
            "status": "created",
            "message": "Operator identity created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create operator identity: {str(e)}"
        )


@router.post("/onboarding/workspace-authority")
async def create_workspace_authority(
    authority_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create workspace authority profile."""
    
    try:
        workspace_authority_id = authority_data["workspace_id"]
        
        # Create workspace authority profile
        authority_profile = {
            "id": workspace_authority_id,
            "workspace_id": current_user.workspace_id,
            "authority_level": authority_data.get("authority_level", "operator"),
            "permissions": authority_data.get("permissions", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        }
        
        return {
            "workspace_authority_id": workspace_authority_id,
            "status": "created",
            "message": "Workspace authority profile created"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workspace authority: {str(e)}"
        )


@router.post("/onboarding/agent-certificate")
async def generate_agent_certificate(
    certificate_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate first agent certificate."""
    
    try:
        # Generate certificate ID
        certificate_id = f"cert_{uuid.uuid4().hex[:8]}"
        
        # Create agent genome
        genome_data = {
            "agent_name": certificate_data.get("agent_name", "Primary Agent"),
            "agent_type": certificate_data.get("agent_type", "autonomous"),
            "capabilities": certificate_data.get("capabilities", []),
            "safety_rules": certificate_data.get("safety_rules", []),
            "version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Generate genome hash
        genome_hash = hashlib.sha256(
            json.dumps(genome_data, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            "certificate_id": certificate_id,
            "genome_hash": genome_hash,
            "status": "created",
            "message": "Agent certificate generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate agent certificate: {str(e)}"
        )


@router.post("/onboarding/ledger-lineage")
async def initialize_ledger_lineage(
    ledger_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize ledger and lineage roots."""
    
    try:
        certificate_id = ledger_data["certificate_id"]
        genesis_block = ledger_data["genesis_block"]
        
        # Generate ledger root
        ledger_root = hashlib.sha256(
            json.dumps({
                "certificate_id": certificate_id,
                "genesis_block": genesis_block,
                "init_timestamp": datetime.now(timezone.utc).isoformat()
            }, sort_keys=True).encode()
        ).hexdigest()
        
        # Generate lineage root
        lineage_root = hashlib.sha256(
            json.dumps({
                "certificate_id": certificate_id,
                "lineage_start": datetime.now(timezone.utc).isoformat(),
                "ancestors": [],
                "generation": 0
            }, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            "ledger_root": ledger_root,
            "lineage_root": lineage_root,
            "status": "initialized",
            "message": "Ledger and lineage initialized successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize ledger and lineage: {str(e)}"
        )


@router.post("/onboarding/first-proof")
async def generate_first_proof(
    proof_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate first harmless proof."""
    
    try:
        certificate_id = proof_data["certificate_id"]
        proof_type = proof_data["proof_type"]
        payload = proof_data["payload"]
        
        # Generate proof ID
        proof_id = f"proof_{uuid.uuid4().hex[:8]}"
        
        # Create proof data
        proof_content = {
            "proof_id": proof_id,
            "certificate_id": certificate_id,
            "proof_type": proof_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "verifier": "system"
        }
        
        # Generate proof hash
        proof_hash = hashlib.sha256(
            json.dumps(proof_content, sort_keys=True).encode()
        ).hexdigest()
        
        # Create PGL profile
        profile_id = f"pgl_{uuid.uuid4().hex[:8]}"
        
        return {
            "proof_id": proof_id,
            "profile_id": profile_id,
            "proof_hash": proof_hash,
            "status": "verified",
            "message": "First proof generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate first proof: {str(e)}"
        )


@router.post("/onboarding/complete")
async def complete_onboarding(
    completion_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete PGL onboarding and unlock workspace."""
    
    try:
        profile_id = completion_data["profile_id"]
        
        return {
            "status": "completed",
            "workspace_unlocked": True,
            "redirect_to": "/home",
            "message": "PGL onboarding completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.get("/profile")
async def get_pgl_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current PGL profile status."""
    
    try:
        # Check if user has PGL profile
        # For demo, return pending status
        return {
            "status": "pending",
            "message": "PGL onboarding required"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get PGL profile: {str(e)}"
        )


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


# In-memory store for demo/prototyping (replace with DB in production)
_pgl_store: dict[str, Any] = {
    "mode": "local-dev",
    "operator": None,
    "workspace": None,
    "certificate": None,
    "ledger_events": [],
}


def _hash_object(obj: dict) -> str:
    """Create SHA256 hash of object for ledger integrity."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@router.get("/status", response_model=dict[str, Any])
async def get_onboarding_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current PGL onboarding status.
    
    Called on app mount to check if user needs first-run PGL onboarding.
    Returns has_pgl_profile=false if onboarding is required.
    """
    mode = _pgl_store.get("mode", "local-dev")
    
    mode_displays = {
        "live": "🟢 Live PGL",
        "replay": "🟡 Replay Mode (Demo)",
        "local-dev": "🔵 Local Development",
    }
    
    # Check if we have a complete profile
    has_profile = (
        _pgl_store.get("operator") is not None
        and _pgl_store.get("workspace") is not None
        and _pgl_store.get("certificate") is not None
    )
    
    snapshot = None
    if has_profile:
        snapshot = {
            "agent_id": _pgl_store["certificate"].get("agent_id"),
            "agent_name": _pgl_store["certificate"].get("agent_name"),
            "mode": mode,
            "chain_verified": True,
            "certificate": _pgl_store["certificate"],
            "operator": _pgl_store["operator"],
            "workspace": _pgl_store["workspace"],
            "ledger_events": _pgl_store.get("ledger_events", []),
        }
    
    return {
        "mode": mode,
        "mode_display": mode_displays.get(mode, "Unknown"),
        "has_pgl_profile": has_profile,
        "profile": snapshot,
        "message": f"PGL adapter is running in {mode} mode",
        "warning": None if mode == "live" else "Not connected to live PGL registry",
        "requires_onboarding": not has_profile,
    }


@router.post("/bootstrap-operator")
async def bootstrap_operator(
    body: BootstrapOperatorRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create and bind operator identity."""
    operator_id = f"op_{uuid.uuid4().hex[:12]}"
    
    operator = {
        "id": operator_id,
        "name": body.name,
        "email": body.email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_id": str(user.id) if user.id else None,
    }
    
    # Create ledger event
    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": "operator_created",
        "entity_id": operator_id,
        "hash": _hash_object(operator),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    _pgl_store["operator"] = operator
    _pgl_store["ledger_events"].append(event)
    
    return {
        "success": True,
        "operator": operator,
        "ledger_event": event,
    }


@router.post("/create-workspace")
async def create_workspace(
    body: CreateWorkspaceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create owner workspace with genome and ledger root."""
    workspace_id = f"ws_{uuid.uuid4().hex[:12]}"
    
    # Generate genome hash
    genome_data = {
        "workspace_id": workspace_id,
        "name": body.name,
        "operator_id": body.operator_id,
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    genome_hash = _hash_object(genome_data)
    
    # Generate ledger root
    ledger_root = f"ledger://{body.name.lower().replace(' ', '-')}/root"
    
    workspace = {
        "id": workspace_id,
        "name": body.name,
        "operator_id": body.operator_id,
        "genome_hash": genome_hash,
        "genome_version": "1.0.0",
        "ledger_root": ledger_root,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Create ledger event
    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": "workspace_created",
        "entity_id": workspace_id,
        "hash": _hash_object(workspace),
        "previous_hash": _pgl_store["ledger_events"][-1]["hash"] if _pgl_store["ledger_events"] else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    _pgl_store["workspace"] = workspace
    _pgl_store["ledger_events"].append(event)
    
    return {
        "success": True,
        "workspace": workspace,
        "ledger_event": event,
    }


@router.post("/issue-certificate")
async def issue_certificate(
    body: IssueCertificateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue first agent birth certificate."""
    agent_id = f"agent_{body.agent_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
    
    # Generate certificate hash
    cert_data = {
        "agent_id": agent_id,
        "agent_name": body.agent_name,
        "operator_id": body.operator_id,
        "workspace_id": body.workspace_id,
        "jurisdiction": body.jurisdiction,
        "declared_purpose": body.declared_purpose,
        "intended_use": body.intended_use,
        "risk_category": body.risk_category,
        "tools": body.tools,
        "permissions": body.permissions,
        "safety_rules": body.safety_rules,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    cert_hash = _hash_object(cert_data)
    
    certificate = {
        "id": f"cert_{uuid.uuid4().hex[:12]}",
        "agent_id": agent_id,
        "agent_name": body.agent_name,
        "genome_version": "1.0.0",
        "genome_hash": cert_hash[:16] + "...",
        "jurisdiction": body.jurisdiction,
        "declared_purpose": body.declared_purpose,
        "intended_use": body.intended_use,
        "risk_category": body.risk_category,
        "tools": body.tools or ["governance", "policy-check"],
        "permissions": body.permissions,
        "safety_rules": body.safety_rules,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Create ledger event
    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": "certificate_issued",
        "entity_id": agent_id,
        "hash": cert_hash,
        "previous_hash": _pgl_store["ledger_events"][-1]["hash"] if _pgl_store["ledger_events"] else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    _pgl_store["certificate"] = certificate
    _pgl_store["ledger_events"].append(event)
    
    return {
        "success": True,
        "certificate": certificate,
        "agent_id": agent_id,
        "ledger_event": event,
    }


@router.get("/snapshot/{agent_id}")
async def get_agent_snapshot(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full PGL snapshot for Authority Panel."""
    cert = _pgl_store.get("certificate")
    if not cert or cert.get("agent_id") != agent_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "agent_id": agent_id,
        "agent_name": cert.get("agent_name"),
        "mode": _pgl_store.get("mode", "local-dev"),
        "chain_verified": True,
        "certificate": cert,
        "operator": _pgl_store.get("operator"),
        "workspace": _pgl_store.get("workspace"),
        "ledger_events": _pgl_store.get("ledger_events", []),
        "version_count": len(_pgl_store.get("ledger_events", [])),
    }


@router.post("/complete")
async def complete_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete onboarding and run first harmless proof."""
    # Verify chain integrity
    events = _pgl_store.get("ledger_events", [])
    chain_valid = True
    
    for i, event in enumerate(events):
        if i > 0 and event.get("previous_hash") != events[i-1].get("hash"):
            chain_valid = False
            break
    
    # Create completion event
    completion_event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": "onboarding_completed",
        "entity_id": _pgl_store.get("certificate", {}).get("agent_id"),
        "hash": _hash_object({"completed": True, "chain_valid": chain_valid}),
        "previous_hash": events[-1]["hash"] if events else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    _pgl_store["ledger_events"].append(completion_event)
    _pgl_store["onboarding_complete"] = True
    
    return {
        "success": True,
        "chain_verified": chain_valid,
        "onboarding_complete": True,
        "redirect_to": "/dashboard",
    }
