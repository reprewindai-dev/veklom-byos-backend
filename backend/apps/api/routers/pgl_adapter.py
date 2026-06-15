"""PGL Adapter/Proxy endpoints for agent management."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
import uuid
import hashlib
import json

router = APIRouter(prefix="/pgl", tags=["PGL Adapter"])


@router.get("/profile", response_model=Dict[str, Any])
async def get_pgl_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current PGL profile status and details."""
    
    try:
        # Check if user has PGL profile
        # For demo, return pending status initially
        return {
            "status": "pending",
            "message": "PGL onboarding required",
            "operator_identity": None,
            "workspace_authority": None,
            "agent_certificates": [],
            "ledger_root": None,
            "lineage_root": None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get PGL profile: {str(e)}"
        )


@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all agents under PGL authority."""
    
    try:
        # Return mock agents for demo
        return [
            {
                "id": "agent_001",
                "name": "Primary Agent",
                "type": "autonomous",
                "status": "active",
                "certificate_id": "cert_abc123",
                "genome_hash": "sha256:abc123...",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "capabilities": ["web_search", "data_analysis", "automation"],
                "safety_rules": ["no_external_payments", "data_privacy"]
            }
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.post("/agents", response_model=Dict[str, Any])
async def create_agent(
    agent_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent under PGL authority."""
    
    try:
        required_fields = ["name", "type", "capabilities"]
        for field in required_fields:
            if field not in agent_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        certificate_id = f"cert_{uuid.uuid4().hex[:8]}"
        
        # Generate genome hash
        genome_data = {
            "name": agent_data["name"],
            "type": agent_data["type"],
            "capabilities": agent_data["capabilities"],
            "safety_rules": agent_data.get("safety_rules", []),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        genome_hash = hashlib.sha256(
            json.dumps(genome_data, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            "agent_id": agent_id,
            "certificate_id": certificate_id,
            "genome_hash": genome_hash,
            "name": agent_data["name"],
            "type": agent_data["type"],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.get("/agents/{agent_id}/certificate", response_model=Dict[str, Any])
async def get_agent_certificate(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent certificate details."""
    
    try:
        # Return mock certificate for demo
        return {
            "certificate_id": f"cert_{agent_id}",
            "agent_id": agent_id,
            "genome_hash": "sha256:abc123...",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,
            "status": "active",
            "capabilities": ["web_search", "data_analysis", "automation"],
            "safety_rules": ["no_external_payments", "data_privacy"],
            "issuer": "veklom_pgl"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent certificate: {str(e)}"
        )


@router.get("/ledger", response_model=Dict[str, Any])
async def get_ledger_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get PGL ledger status and recent entries."""
    
    try:
        return {
            "root_hash": "sha256:ledger_root_abc123...",
            "total_entries": 42,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "recent_entries": [
                {
                    "hash": "sha256:entry_001",
                    "type": "agent_created",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {"agent_id": "agent_001"}
                }
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ledger status: {str(e)}"
        )


@router.get("/lineage", response_model=Dict[str, Any])
async def get_lineage_tree(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent lineage tree."""
    
    try:
        return {
            "root_hash": "sha256:lineage_root_def456...",
            "total_agents": 3,
            "generations": 2,
            "tree": {
                "generation_0": ["agent_001"],
                "generation_1": ["agent_002", "agent_003"],
                "relationships": [
                    {"parent": "agent_001", "child": "agent_002", "type": "fork"},
                    {"parent": "agent_001", "child": "agent_003", "type": "fork"}
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get lineage tree: {str(e)}"
        )


@router.post("/agents/{agent_id}/execute", response_model=Dict[str, Any])
async def execute_agent_action(
    agent_id: str,
    action_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute action through PGL authority with policy enforcement."""
    
    try:
        required_fields = ["action", "parameters"]
        for field in required_fields:
            if field not in action_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Check policy compliance (mock)
        if action_data["action"] == "external_payment":
            raise HTTPException(
                status_code=403,
                detail="Action blocked by safety rule: no_external_payments"
            )
        
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        return {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "action": action_data["action"],
            "status": "completed",
            "result": {
                "message": "Action executed successfully",
                "data": action_data["parameters"]
            },
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "policy_compliance": "passed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute agent action: {str(e)}"
        )


@router.post("/onboarding/bootstrap", response_model=Dict[str, Any])
async def bootstrap_operator(
    operator_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bootstrap operator identity for PGL onboarding."""
    
    required_fields = ["name", "email"]
    for field in required_fields:
        if field not in operator_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    operator_id = f"operator_{uuid.uuid4().hex[:8]}"
    
    # In a real implementation, this would create PGL records
    # For now, return a mock response
    return {
        "operator_id": operator_id,
        "name": operator_data["name"],
        "email": operator_data["email"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }


@router.post("/onboarding/workspace-authority", response_model=Dict[str, Any])
async def create_workspace_authority(
    workspace_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create workspace authority configuration."""
    
    required_fields = ["name", "authority_level", "operator_id"]
    for field in required_fields:
        if field not in workspace_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    workspace_id = f"workspace_{uuid.uuid4().hex[:8]}"
    
    return {
        "workspace_id": workspace_id,
        "name": workspace_data["name"],
        "authority_level": workspace_data["authority_level"],
        "compliance_frameworks": workspace_data.get("compliance_frameworks", []),
        "operator_id": workspace_data["operator_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }


@router.post("/onboarding/agent-certificate", response_model=Dict[str, Any])
async def issue_agent_certificate(
    certificate_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Issue agent birth certificate."""
    
    required_fields = ["agent_name", "operator_id", "workspace_id", "jurisdiction"]
    for field in required_fields:
        if field not in certificate_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    certificate_id = f"cert_{uuid.uuid4().hex[:8]}"
    
    # Create genome hash
    genome_data = {
        "agent_name": certificate_data["agent_name"],
        "jurisdiction": certificate_data["jurisdiction"],
        "declared_purpose": certificate_data.get("declared_purpose", ""),
        "intended_use": certificate_data.get("intended_use", ""),
        "risk_category": certificate_data.get("risk_category", "low"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    genome_hash = hashlib.sha256(
        json.dumps(genome_data, sort_keys=True).encode()
    ).hexdigest()
    
    return {
        "certificate_id": certificate_id,
        "agent_id": agent_id,
        "agent_name": certificate_data["agent_name"],
        "operator_id": certificate_data["operator_id"],
        "workspace_id": certificate_data["workspace_id"],
        "jurisdiction": certificate_data["jurisdiction"],
        "declared_purpose": certificate_data.get("declared_purpose", ""),
        "intended_use": certificate_data.get("intended_use", ""),
        "risk_category": certificate_data.get("risk_category", "low"),
        "genome_version": "1.0.0",
        "genome_hash": genome_hash,
        "status": "active",
        "issued_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/onboarding/genome", response_model=Dict[str, Any])
async def create_genome(
    genome_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create agent genome configuration."""
    
    required_fields = ["tools", "permissions", "safety_rules", "agent_id", "workspace_id"]
    for field in required_fields:
        if field not in genome_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    genome_snapshot = {
        "genome_version": "1.0.0",
        "tools": genome_data["tools"],
        "permissions": genome_data["permissions"],
        "safety_rules": genome_data["safety_rules"],
        "agent_id": genome_data["agent_id"],
        "workspace_id": genome_data["workspace_id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    genome_hash = hashlib.sha256(
        json.dumps(genome_snapshot, sort_keys=True).encode()
    ).hexdigest()
    
    return {
        "genome_id": f"genome_{uuid.uuid4().hex[:8]}",
        "genome_hash": genome_hash,
        "genome_snapshot": genome_snapshot,
        "lineage_root": f"lineage://{genome_data['workspace_id']}/{genome_data['agent_id']}/root",
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/onboarding/ledger", response_model=Dict[str, Any])
async def initialize_ledger(
    ledger_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize tamper-evident ledger."""
    
    required_fields = ["workspace_id", "agent_id"]
    for field in required_fields:
        if field not in ledger_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    ledger_root = f"ledger://{ledger_data['workspace_id']}/root"
    ledger_id = f"ledger_{uuid.uuid4().hex[:8]}"
    
    # Create initial ledger entry
    initial_entry = {
        "ledger_id": ledger_id,
        "entry_type": "root",
        "workspace_id": ledger_data["workspace_id"],
        "agent_id": ledger_data["agent_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "previous_hash": None,
        "data": "PGL Ledger Initialization"
    }
    
    entry_hash = hashlib.sha256(
        json.dumps(initial_entry, sort_keys=True).encode()
    ).hexdigest()
    
    return {
        "ledger_id": ledger_id,
        "ledger_root": ledger_root,
        "initial_entry": {
            **initial_entry,
            "hash": entry_hash
        },
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/onboarding/payment-binding", response_model=Dict[str, Any])
async def bind_payment(
    payment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bind payment methods to workspace (optional)."""
    
    workspace_id = payment_data.get("workspace_id")
    if not workspace_id:
        raise HTTPException(
            status_code=400,
            detail="workspace_id is required"
        )
    
    return {
        "payment_binding_id": f"payment_{uuid.uuid4().hex[:8]}",
        "workspace_id": workspace_id,
        "wallet_address": payment_data.get("wallet_address"),
        "payment_methods": payment_data.get("payment_methods", []),
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/onboarding/first-proof", response_model=Dict[str, Any])
async def create_first_proof(
    proof_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create first proof to complete onboarding."""
    
    profile_id = proof_data.get("profile_id")
    if not profile_id:
        raise HTTPException(
            status_code=400,
            detail="profile_id is required"
        )
    
    proof_id = f"proof_{uuid.uuid4().hex[:8]}"
    
    # Create harmless proof
    proof_content = {
        "proof_id": proof_id,
        "proof_type": "onboarding_completion",
        "profile_id": profile_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verification": "PGL chain integrity verified",
        "status": "complete"
    }
    
    proof_hash = hashlib.sha256(
        json.dumps(proof_content, sort_keys=True).encode()
    ).hexdigest()
    
    return {
        "proof_id": proof_id,
        "proof_type": "onboarding_completion",
        "proof_hash": proof_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "message": "PGL onboarding completed successfully"
    }


@router.post("/onboarding/complete", response_model=Dict[str, Any])
async def complete_onboarding(
    completion_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete PGL onboarding and unlock workspace."""
    
    return {
        "status": "completed",
        "message": "PGL onboarding completed. Workspace access unlocked.",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all agents for the current workspace."""
    
    # Mock response - in real implementation, query PGL database
    return [
        {
            "agent_id": "agent_12345678",
            "agent_name": "Research Assistant",
            "certificate_id": "cert_87654321",
            "genome_hash": "sha256:a1b2c3d4e5f6...",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
    ]


@router.get("/agents/{agent_id}/snapshot", response_model=Dict[str, Any])
async def get_agent_snapshot(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent genome snapshot."""
    
    # Mock response - in real implementation, query PGL database
    return {
        "agent_id": agent_id,
        "genome_version": "1.0.0",
        "genome_hash": "sha256:a1b2c3d4e5f6...",
        "tools": ["web_search", "file_access", "api_calls"],
        "permissions": ["read", "write"],
        "safety_rules": ["no_sensitive_data", "human_approval_required"],
        "lineage_root": f"lineage://workspace_{agent_id}/root",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/agents/{agent_id}/certificate", response_model=Dict[str, Any])
async def get_agent_certificate(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent birth certificate."""
    
    # Mock response - in real implementation, query PGL database
    return {
        "certificate_id": "cert_87654321",
        "agent_id": agent_id,
        "agent_name": "Research Assistant",
        "operator_id": "operator_12345678",
        "workspace_id": "workspace_87654321",
        "jurisdiction": "US",
        "declared_purpose": "Research assistance and data analysis",
        "intended_use": "Production",
        "risk_category": "low",
        "genome_version": "1.0.0",
        "genome_hash": "sha256:a1b2c3d4e5f6...",
        "status": "active",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None
    }


@router.get("/agents/{agent_id}/lineage", response_model=Dict[str, Any])
async def get_agent_lineage(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent lineage tracking."""
    
    # Mock response - in real implementation, query PGL database
    return {
        "agent_id": agent_id,
        "lineage_root": f"lineage://workspace_{agent_id}/root",
        "parent_agents": [],
        "child_agents": [],
        "version_count": 1,
        "lineage_events": [
            {
                "event_id": "event_12345678",
                "event_type": "creation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "description": "Agent created via PGL onboarding"
            }
        ],
        "chain_verification": "valid"
    }


@router.get("/agents/{agent_id}/ledger", response_model=Dict[str, Any])
async def get_agent_ledger(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent ledger entries."""
    
    # Mock response - in real implementation, query PGL database
    return {
        "agent_id": agent_id,
        "ledger_id": "ledger_12345678",
        "ledger_root": f"ledger://workspace_{agent_id}/root",
        "entries": [
            {
                "entry_id": "entry_12345678",
                "entry_type": "creation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hash": "sha256:entry_hash_12345678",
                "previous_hash": None,
                "data": "Agent creation event"
            }
        ],
        "total_entries": 1,
        "last_entry_hash": "sha256:entry_hash_12345678"
    }


@router.get("/agents/{agent_id}/verify", response_model=Dict[str, Any])
async def verify_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify agent certificate and genome integrity."""
    
    # Mock verification - in real implementation, perform actual verification
    return {
        "agent_id": agent_id,
        "verification_status": "valid",
        "certificate_valid": True,
        "genome_integrity": "valid",
        "ledger_chain": "valid",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "trust_score": 0.95,
        "warnings": [],
        "errors": []
    }


@router.get("/status", response_model=Dict[str, Any])
async def get_pgl_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get PGL status for current user/workspace."""
    
    # Mock response - in real implementation, check actual PGL status
    return {
        "mode": "local-dev",
        "mode_display": "Local Development",
        "has_pgl_profile": False,  # Will be True after onboarding
        "requires_onboarding": True,
        "profile": None  # Will contain profile data after onboarding
    }
