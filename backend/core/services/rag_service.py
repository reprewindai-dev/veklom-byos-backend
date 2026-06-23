from typing import Any, Dict, List, Optional
import uuid
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from backend.db.models.rag import AgentMemoryStore, DocumentChunk
from backend.core.services.seked_service import seked_service

class RAGService:
    @staticmethod
    def _compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    async def index_document(
        db: AsyncSession,
        tenant_id: str,
        workspace_id: str,
        source_document_id: str,
        source_type: str,
        chunks: List[str],
        embeddings: List[List[float]],
        classification: str = "internal",
        access_tags: List[str] = None,
        created_by_agent_id: Optional[str] = None
    ) -> List[str]:
        """
        Ingest, classify, and securely index a document.
        (Note: Redaction and chunking are assumed to happen before calling this core ingestion).
        """
        chunk_ids = []
        for i, (content, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"chk_{uuid.uuid4().hex[:12]}"
            doc_chunk = DocumentChunk(
                id=chunk_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                source_document_id=source_document_id,
                source_type=source_type,
                chunk_index=i,
                content=content,
                content_hash=RAGService._compute_hash(content),
                embedding=embedding,
                document_classification=classification,
                access_tags=access_tags or [],
                created_by_agent_id=created_by_agent_id
            )
            db.add(doc_chunk)
            chunk_ids.append(chunk_id)
        
        await db.commit()
        return chunk_ids

    @staticmethod
    async def semantic_search(
        db: AsyncSession,
        agent_id: str,
        tenant_id: str,
        workspace_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        required_classification: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Enforce tenant filtering FIRST, then perform semantic search.
        """
        # Gate 2: SEKED Privilege Check
        is_active = await seked_service.check_agent_privilege(db, agent_id)
        if not is_active:
            raise PermissionError(f"Agent {agent_id} has revoked privileges. Search denied.")

        # Gate 3: Scope Gate (Tenant, Workspace, Classification)
        stmt = select(DocumentChunk).where(DocumentChunk.tenant_id == tenant_id)
        if workspace_id:
            stmt = stmt.where(DocumentChunk.workspace_id == workspace_id)
        if required_classification:
            stmt = stmt.where(DocumentChunk.document_classification == required_classification)
            
        # Semantic similarity within the authorized slice
        stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_embedding)).limit(top_k)
        
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        return [
            {
                "id": c.id,
                "content": c.content,
                "source_document_id": c.source_document_id,
                "classification": c.document_classification,
                "score": 0.0 # Placeholder for actual distance calculation if needed
            } for c in chunks
        ]

    @staticmethod
    async def store_memory(
        db: AsyncSession,
        agent_id: str,
        tenant_id: str,
        workspace_id: str,
        content: str,
        embedding: List[float],
        memory_type: str = "episodic",
        importance_score: float = 1.0,
        source_run_id: Optional[str] = None,
        ttl_expires_at: Optional[datetime] = None
    ) -> str:
        """
        Write curated memory, enforcing strict privilege gates.
        """
        # Privilege gate for writes is critical
        is_active = await seked_service.check_agent_privilege(db, agent_id)
        if not is_active:
            raise PermissionError(f"Agent {agent_id} has revoked privileges. Memory write denied.")

        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        mem = AgentMemoryStore(
            id=memory_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            memory_type=memory_type,
            importance_score=importance_score,
            content=content,
            content_hash=RAGService._compute_hash(content),
            embedding=embedding,
            source_run_id=source_run_id,
            ttl_expires_at=ttl_expires_at
        )
        db.add(mem)
        await db.commit()
        return memory_id

    @staticmethod
    async def retrieve_memory(
        db: AsyncSession,
        agent_id: str,
        tenant_id: str,
        query_embedding: List[float],
        memory_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memory distinct from document retrieval.
        """
        # Privilege gate
        is_active = await seked_service.check_agent_privilege(db, agent_id)
        if not is_active:
            raise PermissionError(f"Agent {agent_id} has revoked privileges. Memory read denied.")

        stmt = select(AgentMemoryStore).where(
            AgentMemoryStore.agent_id == agent_id,
            AgentMemoryStore.tenant_id == tenant_id
        )
        if memory_type:
            stmt = stmt.where(AgentMemoryStore.memory_type == memory_type)
            
        stmt = stmt.order_by(AgentMemoryStore.embedding.cosine_distance(query_embedding)).limit(top_k)
        
        result = await db.execute(stmt)
        memories = result.scalars().all()
        
        return [
            {
                "id": m.id,
                "content": m.content,
                "memory_type": m.memory_type,
                "importance_score": m.importance_score,
                "timestamp": m.event_timestamp.isoformat() if m.event_timestamp else None
            } for m in memories
        ]

rag_service = RAGService()
