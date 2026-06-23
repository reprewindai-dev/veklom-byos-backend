from sqlalchemy import Column, String, DateTime, JSON, Float, Integer
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from backend.core.database.database import Base

class AgentMemoryStore(Base):
    """
    Stateful memory for autonomous agents (Agent-112).
    Governed by PGL Identity (tenant_id, agent_id).
    """
    __tablename__ = "rag_agent_memory"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=True)
    
    memory_type = Column(String, default="episodic")  # 'episodic', 'semantic', 'scratchpad', 'summary'
    importance_score = Column(Float, default=0.0)
    event_timestamp = Column(DateTime(timezone=True), default=func.now())
    ttl_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    content = Column(String, nullable=False)
    content_hash = Column(String, nullable=True)
    embedding = Column(Vector(1536))  # 1536 for OpenAI embeddings
    embedding_model = Column(String, default="text-embedding-3-small")
    
    source_run_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentChunk(Base):
    """
    Platform knowledge indexing for semantic search (Agent-109, Agent-110).
    """
    __tablename__ = "rag_document_chunks"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    workspace_id = Column(String, index=True, nullable=True)
    
    source_document_id = Column(String, index=True, nullable=False)
    source_type = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    content = Column(String, nullable=False)
    content_hash = Column(String, nullable=True)
    embedding = Column(Vector(1536))
    embedding_model = Column(String, default="text-embedding-3-small")
    
    document_classification = Column(String, default="internal") # 'public', 'internal', 'confidential', 'phi'
    access_tags = Column(JSON, default=list)
    created_by_agent_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
