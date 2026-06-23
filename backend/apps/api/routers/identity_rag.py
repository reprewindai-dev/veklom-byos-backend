from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_rls_db
from backend.schemas.identity_rag import IdentityRAGResolveRequest, GoldenRecordResponse
from backend.db.repositories.identity_rag_repo import resolve_identity_golden_record
from backend.core.security.payment_proof import require_payment_proof

router = APIRouter(prefix="/api/v1/pgl/identity-rag", tags=["identity-rag"])

IDENTITY_RAG_FEE_MINOR = 1_000_000


@router.post("/resolve", response_model=GoldenRecordResponse)
async def resolve_identity_rag(
    payload: IdentityRAGResolveRequest,
    db: AsyncSession = Depends(get_rls_db),
    payment=Depends(require_payment_proof),
) -> GoldenRecordResponse:
    record = await resolve_identity_golden_record(
        db=db,
        agent_id=payload.agent_id,
        public_key=payload.public_key,
        requester_provider_id=payload.requester_provider_id,
        resolution_fee_minor=IDENTITY_RAG_FEE_MINOR,
        payment_proof=payment,
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PGL identity not found")
    return record
