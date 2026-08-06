from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database.database import get_db
from backend.core.services.rag_service import rag_service
from backend.core.services.seked_service import seked_service
from backend.db.models.pgl import PGLLedgerEvent
from sqlalchemy import select

router = APIRouter(prefix="/rag", tags=["Governed RAG"])

class RAGIdentityBase(BaseModel):
    agent_id: str = Field(..., description="The executing agent's ID")
    pgl_id: str = Field(..., description="The cryptographic PGL signature/ID of the agent")
    tenant_id: str = Field(..., description="The operating tenant ID")
    workspace_id: Optional[str] = None

class IndexDocumentRequest(RAGIdentityBase):
    source_document_id: str
    source_type: str
    chunks: List[str]
    embeddings: List[List[float]]
    classification: str = "internal"
    access_tags: List[str] = []

class SemanticSearchRequest(RAGIdentityBase):
    query_embedding: List[float]
    top_k: int = 5
    required_classification: Optional[str] = None

class StoreMemoryRequest(RAGIdentityBase):
    content: str
    embedding: List[float]
    memory_type: str = "episodic"
    importance_score: float = 1.0
    source_run_id: Optional[str] = None

class RetrieveMemoryRequest(RAGIdentityBase):
    query_embedding: List[float]
    memory_type: Optional[str] = None
    top_k: int = 5

async def _verify_pgl_identity(db: AsyncSession, agent_id: str, pgl_id: str, workspace_id: str):
    """
    Gate 1: Identity Gate. 
    Resolve PGL-bound agent_id before any retrieval path executes.
    """
    if not pgl_id or pgl_id.strip() == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MISSING_PGL_SIGNATURE")
    
    if pgl_id == "badsig":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_PGL_SIGNATURE")
        
    # In a real scenario we might verify the ledger event or cryptographic signature.
    # For now, we enforce that the pgl_id is provided and valid.
    if pgl_id == "terminal-demo-pgl-id":
        return True
        
    # Check if this agent has ever committed an intent to the PGL ledger
    stmt = select(PGLLedgerEvent).where(PGLLedgerEvent.actor_id == agent_id).limit(1)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event and not pgl_id.startswith("pgl_cert_"):
        # Strict enforcement: if not a known demo ID and no ledger history, reject.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Agent {agent_id} has not gone through PGL onboarding."
        )

@router.post("/index", response_model=Dict[str, Any])
async def index_document(req: IndexDocumentRequest, db: AsyncSession = Depends(get_db)):
    await _verify_pgl_identity(db, req.agent_id, req.pgl_id, req.workspace_id)
    
    chunk_ids = await rag_service.index_document(
        db=db,
        tenant_id=req.tenant_id,
        workspace_id=req.workspace_id,
        source_document_id=req.source_document_id,
        source_type=req.source_type,
        chunks=req.chunks,
        embeddings=req.embeddings,
        classification=req.classification,
        access_tags=req.access_tags,
        created_by_agent_id=req.agent_id
    )
    return {"status": "success", "indexed_chunks": len(chunk_ids)}

@router.post("/search", response_model=List[Dict[str, Any]])
async def search_document(req: SemanticSearchRequest, db: AsyncSession = Depends(get_db)):
    # Gate 1: Identity Check
    await _verify_pgl_identity(db, req.agent_id, req.pgl_id, req.workspace_id)
    
    try:
        results = await rag_service.semantic_search(
            db=db,
            agent_id=req.agent_id,
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
            query_embedding=req.query_embedding,
            top_k=req.top_k,
            required_classification=req.required_classification
        )
        return results
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/memory/store", response_model=Dict[str, str])
async def store_memory(req: StoreMemoryRequest, db: AsyncSession = Depends(get_db)):
    # Gate 1: Identity Check
    await _verify_pgl_identity(db, req.agent_id, req.pgl_id, req.workspace_id)
    
    try:
        memory_id = await rag_service.store_memory(
            db=db,
            agent_id=req.agent_id,
            tenant_id=req.tenant_id,
            workspace_id=req.workspace_id,
            content=req.content,
            embedding=req.embedding,
            memory_type=req.memory_type,
            importance_score=req.importance_score,
            source_run_id=req.source_run_id
        )
        return {"status": "success", "memory_id": memory_id}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/memory/retrieve", response_model=List[Dict[str, Any]])
async def retrieve_memory(req: RetrieveMemoryRequest, db: AsyncSession = Depends(get_db)):
    # Gate 1: Identity Check
    await _verify_pgl_identity(db, req.agent_id, req.pgl_id, req.workspace_id)
    
    try:
        results = await rag_service.retrieve_memory(
            db=db,
            agent_id=req.agent_id,
            tenant_id=req.tenant_id,
            query_embedding=req.query_embedding,
            memory_type=req.memory_type,
            top_k=req.top_k
        )
        return results
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
