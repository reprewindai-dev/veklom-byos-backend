"""Evidence routes for Veklom Evidence Pack System."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
from backend.apps.api.services.evidence import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("/build")
async def build_evidence_pack(
    authority_run_id: str,
    workspace_id: Optional[str] = Query(None, description="Workspace ID (defaults to user's workspace)"),
    agent_id: Optional[str] = Query(None, description="Agent ID (defaults to run's agent)"),
    description: Optional[str] = Query(None, description="Optional description for the evidence pack"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Build an evidence pack for a given authority run.
    
    Creates an immutable, hash-chained evidence pack containing all artifacts
    related to the authority run including birth certificate, authority bundle,
    memory entries, browser actions, tool calls, and ledger events.
    """
    
    # Validate workspace access
    target_workspace_id = workspace_id or current_user.workspace_id
    if target_workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to workspace")
    
    # Create evidence service
    evidence_service = EvidenceService(db)
    
    try:
        # Get the authority run to extract agent_id if not provided
        from backend.db.models.authority import AuthorityRun
        run_result = await db.execute(
            select(AuthorityRun).where(AuthorityRun.id == authority_run_id)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            raise HTTPException(status_code=404, detail="Authority run not found")
        
        # Verify workspace access to the run
        if run.workspace_id != target_workspace_id:
            raise HTTPException(status_code=403, detail="Access denied to authority run")
        
        target_agent_id = agent_id or run.agent_id
        
        # Build the evidence pack
        evidence_pack = await evidence_service.build_evidence_pack(
            authority_run_id=authority_run_id,
            workspace_id=target_workspace_id,
            agent_id=target_agent_id,
            creator_id=current_user.id,
            description=description
        )
        
        return {
            "evidence_pack_id": evidence_pack.evidence_pack_id,
            "authority_run_id": evidence_pack.authority_run_id,
            "workspace_id": evidence_pack.workspace_id,
            "agent_id": evidence_pack.agent_id,
            "pack_version": evidence_pack.pack_version,
            "pack_type": evidence_pack.pack_type,
            "description": evidence_pack.description,
            "artifacts": evidence_pack.artifacts,
            "hashes": evidence_pack.hashes,
            "verification": evidence_pack.verification,
            "created_at": evidence_pack.created_at.isoformat() if evidence_pack.created_at else None,
            "_links": {
                "self": f"/api/v1/evidence/{evidence_pack.evidence_pack_id}",
                "verify": "/api/v1/evidence/verify",
                "protocol": "/protocol.json"
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error building evidence pack: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail="Failed to build evidence pack")


@router.post("/verify")
async def verify_evidence_pack(
    evidence_pack_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify an evidence pack's integrity by recomputing hashes and validating chains.
    
    Returns verification status including any hash mismatches or missing artifacts.
    """
    
    # Create evidence service
    evidence_service = EvidenceService(db)
    
    try:
        # Get the evidence pack to verify workspace access
        pack = await evidence_service.get_evidence_pack(evidence_pack_id)
        
        if not pack:
            raise HTTPException(status_code=404, detail="Evidence pack not found")
        
        # Verify workspace access
        if pack.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Access denied to evidence pack")
        
        # Verify the evidence pack
        verification_result = await evidence_service.verify_evidence_pack(evidence_pack_id)
        
        return verification_result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error verifying evidence pack: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail="Failed to verify evidence pack")


@router.get("/packs")
async def list_evidence_packs(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    authority_run_id: Optional[str] = Query(None, description="Filter by authority run ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List evidence packs accessible to the current user."""
    
    # Validate workspace access
    target_workspace_id = workspace_id or current_user.workspace_id
    if target_workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to workspace")
    
    # Create evidence service
    evidence_service = EvidenceService(db)
    
    try:
        # List evidence packs
        packs = await evidence_service.list_evidence_packs(
            workspace_id=target_workspace_id,
            agent_id=agent_id,
            authority_run_id=authority_run_id,
            limit=limit,
            offset=offset
        )
        
        return [
            {
                "evidence_pack_id": pack.evidence_pack_id,
                "authority_run_id": pack.authority_run_id,
                "workspace_id": pack.workspace_id,
                "agent_id": pack.agent_id,
                "pack_version": pack.pack_version,
                "pack_type": pack.pack_type,
                "description": pack.description,
                "tags": pack.tags,
                "verification": pack.verification,
                "created_at": pack.created_at.isoformat() if pack.created_at else None,
                "updated_at": pack.updated_at.isoformat() if pack.updated_at else None
            }
            for pack in packs
        ]
        
    except Exception as e:
        import traceback
        error_detail = f"Error listing evidence packs: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail="Failed to list evidence packs")


@router.get("/packs/{evidence_pack_id}")
async def get_evidence_pack(
    evidence_pack_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific evidence pack by ID."""
    
    # Create evidence service
    evidence_service = EvidenceService(db)
    
    try:
        # Get the evidence pack
        pack = await evidence_service.get_evidence_pack(evidence_pack_id)
        
        if not pack:
            raise HTTPException(status_code=404, detail="Evidence pack not found")
        
        # Verify workspace access
        if pack.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Access denied to evidence pack")
        
        return {
            "evidence_pack_id": pack.evidence_pack_id,
            "authority_run_id": pack.authority_run_id,
            "workspace_id": pack.workspace_id,
            "agent_id": pack.agent_id,
            "creator_id": pack.creator_id,
            "pack_version": pack.pack_version,
            "pack_type": pack.pack_type,
            "description": pack.description,
            "tags": pack.tags,
            "artifacts": pack.artifacts,
            "hashes": pack.hashes,
            "verification": pack.verification,
            "hash_chain": pack.hash_chain,
            "prev_hash": pack.prev_hash,
            "created_at": pack.created_at.isoformat() if pack.created_at else None,
            "updated_at": pack.updated_at.isoformat() if pack.updated_at else None
        }
        
    except Exception as e:
        import traceback
        error_detail = f"Error getting evidence pack: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail="Failed to get evidence pack")


@router.get("/packs/{evidence_pack_id}/export")
async def export_evidence_pack(
    evidence_pack_id: str,
    format: str = Query("json", pattern="^(json|csv)$", description="Export format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export an evidence pack in the specified format.
    
    Returns the complete evidence pack with all artifacts for external consumption.
    """
    
    # Create evidence service
    evidence_service = EvidenceService(db)
    
    try:
        # Get the evidence pack
        pack = await evidence_service.get_evidence_pack(evidence_pack_id)
        
        if not pack:
            raise HTTPException(status_code=404, detail="Evidence pack not found")
        
        # Verify workspace access
        if pack.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Access denied to evidence pack")
        
        if format == "json":
            return {
                "evidence_pack": {
                    "evidence_pack_id": pack.evidence_pack_id,
                    "authority_run_id": pack.authority_run_id,
                    "workspace_id": pack.workspace_id,
                    "agent_id": pack.agent_id,
                    "creator_id": pack.creator_id,
                    "pack_version": pack.pack_version,
                    "pack_type": pack.pack_type,
                    "description": pack.description,
                    "tags": pack.tags,
                    "artifacts": pack.artifacts,
                    "hashes": pack.hashes,
                    "verification": pack.verification,
                    "hash_chain": pack.hash_chain,
                    "prev_hash": pack.prev_hash,
                    "created_at": pack.created_at.isoformat() if pack.created_at else None,
                    "updated_at": pack.updated_at.isoformat() if pack.updated_at else None,
                    "exported_at": datetime.now(timezone.utc).isoformat()
                }
            }
        else:
            # CSV format would require additional implementation
            raise HTTPException(status_code=400, detail="CSV export not yet implemented")
        
    except Exception as e:
        import traceback
        error_detail = f"Error exporting evidence pack: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail="Failed to export evidence pack")
