"""Evidence models for Veklom Evidence Pack System."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.database import Base
from backend.db.models.user import _utcnow, _uuid


class EvidencePack(Base):
    """Immutable evidence pack containing hash-chained audit artifacts and verification metadata."""
    
    __tablename__ = "evidence_packs"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    evidence_pack_id = Column(String(128), unique=True, nullable=False, index=True)
    authority_run_id = Column(String(36), ForeignKey("authority_runs.id"), nullable=False, index=True)
    workspace_id = Column(String(36), nullable=False, index=True)
    agent_id = Column(String(36), nullable=False, index=True)
    creator_id = Column(String(36), nullable=False, index=True)
    
    # Artifacts referenced in this pack
    artifacts = Column(JSON, default=dict)  # birth_certificate_id, authority_bundle_id, etc.
    
    # Hash chain for integrity verification
    hashes = Column(JSON, default=dict)  # input_hash, output_hash, audit_hash, ledger_hash, artifacts_hash
    
    # Verification metadata
    verification = Column(JSON, default=dict)  # verified, failures, checked_at, verification_method
    
    # Pack metadata
    pack_version = Column(String(32), default="1.0")
    pack_type = Column(String(64), default="authority_run")  # authority_run, agent_session, compliance_audit
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    
    # Immutable audit fields
    hash_chain = Column(String(128), default="")
    prev_hash = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    authority_run = relationship("AuthorityRun", backref="evidence_packs")
    browser_actions = relationship("BrowserAction", backref="evidence_pack")
    memory_entries = relationship("MemoryEntry", backref="evidence_pack")


class BrowserAction(Base):
    """Browser automation action records for evidence tracking."""
    
    __tablename__ = "browser_actions"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    browser_action_id = Column(String(128), unique=True, nullable=False, index=True)
    agent_id = Column(String(36), nullable=False, index=True)
    authority_run_id = Column(String(36), ForeignKey("authority_runs.id"), nullable=False, index=True)
    evidence_pack_id = Column(String(36), ForeignKey("evidence_packs.id"), nullable=True, index=True)
    workspace_id = Column(String(36), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(64), nullable=False)  # navigate, click, fill_form, extract, screenshot
    target_url = Column(String(1024), default="")
    selector = Column(String(512), default="")
    parameters = Column(JSON, default=dict)
    
    # Execution results
    success = Column(Boolean, default=True)
    error = Column(Text, default="")
    execution_time_ms = Column(Integer, default=0)
    
    # Evidence captured
    evidence = Column(JSON, default=dict)  # screenshot_path, extracted_data, page_title, etc.
    
    # Timing
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    hash_chain = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class MemoryEntry(Base):
    """Memory service entries for evidence tracking."""
    
    __tablename__ = "memory_entries"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    memory_entry_id = Column(String(128), unique=True, nullable=False, index=True)
    agent_id = Column(String(36), nullable=False, index=True)
    authority_run_id = Column(String(36), ForeignKey("authority_runs.id"), nullable=True, index=True)
    evidence_pack_id = Column(String(36), ForeignKey("evidence_packs.id"), nullable=True, index=True)
    workspace_id = Column(String(36), nullable=False, index=True)
    
    # Memory content
    entry_type = Column(String(64), nullable=False)  # context, handoff, learning, state
    content = Column(Text, nullable=False)
    entry_metadata = Column(JSON, default=dict)
    
    # Vector embedding for similarity search
    embedding = Column(JSON, default=list)  # Vector representation
    
    # Memory management
    ttl_seconds = Column(Integer, default=86400)  # 24 hours default
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    hash_chain = Column(String(128), default="")
    created_by = Column(String(36), default="")


class KnowledgeChunk(Base):
    """Knowledge service chunks for RAG agents."""
    
    __tablename__ = "knowledge_chunks"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    chunk_id = Column(String(128), unique=True, nullable=False, index=True)
    source_id = Column(String(36), nullable=False, index=True)
    source_path = Column(String(1024), nullable=False)
    source_type = Column(String(64), nullable=False)  # mission_file, backend_doc, support_ticket, listing
    
    # Chunk content
    chunk_text = Column(Text, nullable=False)
    chunk_meta = Column(JSON, default=dict)  # section, heading, position
    template_id = Column(String(36), nullable=False)
    
    # Vector embedding for similarity search
    embedding = Column(JSON, default=list)
    
    # Indexing metadata
    indexed_by = Column(String(36), nullable=False, index=True)
    indexed_at = Column(DateTime(timezone=True), default=_utcnow)
    
    # Audit fields
    hash_chain = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class KnowledgeSource(Base):
    """Knowledge source tracking for RAG agents."""
    
    __tablename__ = "knowledge_sources"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    source_id = Column(String(128), unique=True, nullable=False, index=True)
    source_path = Column(String(1024), nullable=False)
    source_type = Column(String(64), nullable=False)
    workspace_id = Column(String(36), nullable=False, index=True)
    
    # Source metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    
    # Indexing status
    is_indexed = Column(Boolean, default=False)
    last_indexed = Column(DateTime(timezone=True), nullable=True)
    chunk_count = Column(Integer, default=0)
    
    # Access control
    allowed_agents = Column(JSON, default=list)  # Agent IDs that can access this source
    
    # Audit fields
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class KnowledgeTemplate(Base):
    """Knowledge chunking templates."""
    
    __tablename__ = "knowledge_templates"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    template_id = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    workspace_id = Column(String(36), nullable=False, index=True)
    
    # Template configuration
    chunking_strategy = Column(String(64), nullable=False)  # by_heading, by_size, by_semantic, by_code
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=100)
    
    # Strategy-specific parameters
    parameters = Column(JSON, default=dict)  # Heading levels, semantic boundaries, etc.
    
    # Template metadata
    description = Column(Text, default="")
    is_default = Column(Boolean, default=False)
    
    # Audit fields
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


from sqlalchemy import DDL, event

# Enforce PostgreSQL Row-Level Security (RLS) for tenant isolation
_RLS_TABLES = [
    "evidence_packs", 
    "browser_actions", 
    "memory_entries", 
    "knowledge_sources", 
    "knowledge_templates"
]

for _table in _RLS_TABLES:
    event.listen(
        EvidencePack.__table__,  # Bind to table events or Base.metadata
        "after_create",
        DDL(f"""
        ALTER TABLE {_table} ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation_policy ON {_table}
            AS RESTRICTIVE
            FOR ALL
            USING (workspace_id = current_setting('app.current_tenant_id', true));
        """)
    )
