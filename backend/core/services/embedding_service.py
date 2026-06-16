"""Real Vector Embedding Service - Production Implementation"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

import asyncpg

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    _EMBEDDINGS_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    SentenceTransformer = None  # type: ignore
    _EMBEDDINGS_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "sentence_transformers not installed — VectorEmbeddingService will be unavailable. "
        "Add sentence-transformers to requirements.txt to enable vector search."
    )

logger = logging.getLogger(__name__)


class VectorEmbeddingService:
    """Production-ready vector embedding service with pgvector"""
    
    def __init__(self):
        self.model = None
        self.db_pool = None
        self._initialized = False
    
    async def initialize(self, database_url: str):
        """Initialize the embedding service with database connection"""
        if not _EMBEDDINGS_AVAILABLE:
            logger.warning(
                "sentence_transformers is not installed. "
                "VectorEmbeddingService.initialize() is a no-op. "
                "Install sentence-transformers to enable this feature."
            )
            return
        try:
            # Load the sentence transformer model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
            
            # Create database connection pool
            self.db_pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # Ensure pgvector extension is installed
            await self._ensure_pgvector_extension()
            
            # Create embedding table if not exists
            await self._create_embedding_table()
            
            self._initialized = True
            logger.info("Vector embedding service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {str(e)}")
            raise
    
    async def _ensure_pgvector_extension(self):
        """Ensure pgvector extension is installed"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('CREATE EXTENSION IF NOT EXISTS vector;')
            logger.info("pgvector extension ensured")
    
    async def _create_embedding_table(self):
        """Create the embeddings table with vector support"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS vector_embeddings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    agent_id VARCHAR(255) NOT NULL,
                    memory_id VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(384),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    INDEX (agent_id),
                    INDEX (memory_id),
                    UNIQUE (agent_id, memory_id)
                );
            ''')
            
            # Create index for vector similarity search
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS embedding_vector_idx 
                ON vector_embeddings 
                USING ivfflat (embedding vector_cosine_ops);
            ''')
            
            logger.info("Embedding table created successfully")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    async def store_embedding(
        self, 
        agent_id: str, 
        memory_id: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store embedding in database"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            # Generate embedding
            embedding = await self.generate_embedding(content)
            
            # Store in database
            async with self.db_pool.acquire() as conn:
                result = await conn.execute('''
                    INSERT INTO vector_embeddings (agent_id, memory_id, content, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (agent_id, memory_id) 
                    DO UPDATE SET 
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        created_at = NOW()
                    RETURNING id;
                ''', agent_id, memory_id, content, embedding, json.dumps(metadata or {}))
                
                embedding_id = result[0][0]
                logger.info(f"Stored embedding {embedding_id} for agent {agent_id}")
                return str(embedding_id)
                
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            raise
    
    async def search_similar(
        self, 
        agent_id: str, 
        query: str, 
        limit: int = 10, 
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings using vector similarity"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            # Search for similar embeddings
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT 
                        id,
                        memory_id,
                        content,
                        metadata,
                        created_at,
                        1 - (embedding <=> $1) as similarity
                    FROM vector_embeddings
                    WHERE agent_id = $2
                    AND 1 - (embedding <=> $1) > $3
                    ORDER BY embedding <=> $1
                    LIMIT $4;
                ''', query_embedding, agent_id, threshold, limit)
                
                results = []
                for row in rows:
                    results.append({
                        "embedding_id": str(row["id"]),
                        "memory_id": row["memory_id"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "similarity": float(row["similarity"]),
                        "created_at": row["created_at"].isoformat()
                    })
                
                logger.info(f"Found {len(results)} similar embeddings for agent {agent_id}")
                return results
                
        except Exception as e:
            logger.error(f"Failed to search similar embeddings: {str(e)}")
            raise
    
    async def get_embedding(self, agent_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get specific embedding by agent and memory ID"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT id, content, embedding, metadata, created_at
                    FROM vector_embeddings
                    WHERE agent_id = $1 AND memory_id = $2;
                ''', agent_id, memory_id)
                
                if row:
                    return {
                        "embedding_id": str(row["id"]),
                        "content": row["content"],
                        "embedding": list(row["embedding"]),
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "created_at": row["created_at"].isoformat()
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}")
            raise
    
    async def delete_embedding(self, agent_id: str, memory_id: str) -> bool:
        """Delete specific embedding"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM vector_embeddings
                    WHERE agent_id = $1 AND memory_id = $2;
                ''', agent_id, memory_id)
                
                deleted = result == "DELETE 1"
                if deleted:
                    logger.info(f"Deleted embedding for agent {agent_id}, memory {memory_id}")
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete embedding: {str(e)}")
            raise
    
    async def cleanup_old_embeddings(self, agent_id: str, days_old: int = 30) -> int:
        """Clean up old embeddings for an agent"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM vector_embeddings
                    WHERE agent_id = $1
                    AND created_at < NOW() - INTERVAL '$2 days';
                ''', agent_id, days_old)
                
                # Parse result to get count
                deleted_count = int(result.split()[-1]) if result else 0
                logger.info(f"Cleaned up {deleted_count} old embeddings for agent {agent_id}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old embeddings: {str(e)}")
            raise
    
    async def get_embedding_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics about embeddings for an agent"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_embeddings,
                        MIN(created_at) as oldest_embedding,
                        MAX(created_at) as newest_embedding,
                        AVG(LENGTH(content)) as avg_content_length
                    FROM vector_embeddings
                    WHERE agent_id = $1;
                ''', agent_id)
                
                return {
                    "total_embeddings": row["total_embeddings"],
                    "oldest_embedding": row["oldest_embedding"].isoformat() if row["oldest_embedding"] else None,
                    "newest_embedding": row["newest_embedding"].isoformat() if row["newest_embedding"] else None,
                    "avg_content_length": float(row["avg_content_length"]) if row["avg_content_length"] else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {str(e)}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Embedding service closed")


# Global instance
embedding_service = VectorEmbeddingService()


async def get_embedding_service() -> VectorEmbeddingService:
    """Get the global embedding service instance"""
    if not embedding_service._initialized:
        raise RuntimeError("Embedding service not initialized. Call initialize() first.")
    return embedding_service
