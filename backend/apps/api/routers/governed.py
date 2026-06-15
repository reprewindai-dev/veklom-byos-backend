"""Governed AI execution and protected write routes."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
from backend.db.models.genome import GenomeVersion
from backend.core.services.genome_service import GenomeService
from backend.core.services.governance_engine import GovernanceEngine
from backend.core.services.certificate_service import CertificateService
from backend.core.services.memory_fabric_service import MemoryFabricService

router = APIRouter(prefix="/governed", tags=["PGL Governance Engine"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class GovernedExecuteRequest(BaseModel):
    agent_id: int
    prompt: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    task_type: Optional[str] = None
    org_id: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ConstitutionalWriteRequest(BaseModel):
    agent_id: int
    action: str
    write_payload: Dict[str, Any]
    org_id: Optional[str] = None
    trace_id: Optional[str] = None
    override_requested: bool = False
    override_reason: Optional[str] = None


class FeedbackSubmitRequest(BaseModel):
    trace_id: str
    accepted: bool
    user_rating: Optional[int] = None
    feedback_text: Optional[str] = None
    actual_outcome: Optional[Dict[str, Any]] = None
    predicted_outcome: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/execute", response_model=Dict[str, Any])
async def governed_execute(
    body: GovernedExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a governed completion with risk tiering, watchtowers, and certification."""
    try:
        # Prepare parameters for completion
        payload = body.dict(exclude_unset=True)
        payload["user_id"] = current_user.id
        payload["role"] = current_user.role
        
        result = await GovernanceEngine.runGovernedExecution(
            db=db,
            agent_id=body.agent_id,
            request_body=payload
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger_err = f"Execution error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(logger_err)
        raise HTTPException(
            status_code=500,
            detail=f"Governed execution failed: {str(e)}"
        )


@router.post("/write", response_model=Dict[str, Any])
async def governed_write(
    body: ConstitutionalWriteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a protected constitutional write with authorization and overrides validation."""
    try:
        result = await GovernanceEngine.commitConstitutionalWrite(
            db=db,
            agent_id=body.agent_id,
            action=body.action,
            write_payload=body.write_payload,
            user_id=current_user.id,
            org_id=body.org_id or "default_org",
            role=current_user.role,
            trace_id=body.trace_id,
            override_requested=body.override_requested,
            override_reason=body.override_reason
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Constitutional write failed: {str(e)}"
        )


@router.get("/genome/{merkle_root}", response_model=Dict[str, Any])
async def get_genome(
    merkle_root: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Look up a versioned genome configuration by its cryptographic Merkle root."""
    query = select(GenomeVersion).where(GenomeVersion.merkle_root == merkle_root)
    result = await db.execute(query)
    genome = result.scalar_one_or_none()
    
    if not genome:
        raise HTTPException(status_code=404, detail=f"Genome with Merkle root {merkle_root} not found")
        
    return {
        "id": genome.id,
        "agent_id": genome.agent_id,
        "version": genome.version,
        "payload": genome.payload,
        "merkle_root": genome.merkle_root,
        "note": genome.note,
        "created_at": genome.created_at.isoformat() if genome.created_at else None,
        "layers": {
            "model_layer_hash": genome.model_layer_hash,
            "prompt_layer_hash": genome.prompt_layer_hash,
            "policy_layer_hash": genome.policy_layer_hash,
            "watchtower_layer_hash": genome.watchtower_layer_hash,
            "task_profile_hash": genome.task_profile_hash
        }
    }


@router.get("/genome/diff/{hash_a}/{hash_b}", response_model=Dict[str, Any])
async def diff_genomes(
    hash_a: str,
    hash_b: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compare two genomes leaf by leaf and return the specific changes."""
    query_a = select(GenomeVersion).where(GenomeVersion.merkle_root == hash_a)
    query_b = select(GenomeVersion).where(GenomeVersion.merkle_root == hash_b)
    
    res_a = await db.execute(query_a)
    res_b = await db.execute(query_b)
    
    genome_a = res_a.scalar_one_or_none()
    genome_b = res_b.scalar_one_or_none()
    
    if not genome_a or not genome_b:
        raise HTTPException(status_code=404, detail="One or both genome configurations not found")
        
    return GenomeService.diff_genomes(genome_a, genome_b)


@router.get("/certificate/{trace_id}", response_model=Dict[str, Any])
async def verify_certificate(
    trace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve and verify the signed compact execution certificate for a trace."""
    try:
        result = await CertificateService.verify_certificate_by_trace(db, trace_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Certificate verification failed: {str(e)}")


@router.post("/feedback", response_model=Dict[str, Any])
async def submit_feedback(
    body: FeedbackSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register performance/outcome feedback for trace observability."""
    try:
        feedback = await MemoryFabricService.submit_feedback(
            db=db,
            trace_id=body.trace_id,
            accepted=body.accepted,
            user_rating=body.user_rating,
            feedback_text=body.feedback_text,
            actual_outcome=body.actual_outcome,
            predicted_outcome=body.predicted_outcome
        )
        return {
            "status": "success",
            "feedback_id": feedback.id,
            "trace_id": feedback.trace_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )
