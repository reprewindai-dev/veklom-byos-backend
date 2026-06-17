"""
Veklom Agent Memory Backend
Integrates mem0 with the existing PostgreSQL and pgvector setup.
Drop this file into: backend/apps/api/services/agent_memory.py
"""
import os
from mem0 import Memory
from typing import Optional

# Singleton — initialized once
_memory_instance: Optional[Memory] = None

def get_memory() -> Memory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = Memory.from_config({
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": os.getenv("POSTGRES_HOST", "llwfyzhnft87bz6brddiax1z"),
                    "port": int(os.getenv("POSTGRES_PORT", "5432")),
                    "database": os.getenv("POSTGRES_DB", "veklom"),
                    "user": os.getenv("POSTGRES_USER", "postgres"),
                    "password": os.getenv("POSTGRES_PASSWORD"),
                    "collection_name": "agent_memories",
                    "embedding_model_dims": 1536  # OpenAI text-embedding-3-small
                }
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4.1-mini",
                    "api_key": os.getenv("OPENAI_API_KEY")
                }
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": os.getenv("OPENAI_API_KEY")
                }
            }
        })
    return _memory_instance


class AgentMemory:
    """Per-agent memory interface. Each agent gets its own memory namespace."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memory = get_memory()

    def remember(self, content: str, category: str = "learning", task: str = None, **kwargs) -> dict:
        """Store a memory from this agent session."""
        metadata = {
            "agent_id": self.agent_id,
            "category": category,  # learning|decision|blocker|pattern|handoff
            **kwargs
        }
        if task:
            metadata["task"] = task

        return self.memory.add(
            content,
            user_id=f"agent_{self.agent_id}",
            metadata=metadata
        )

    def recall(self, query: str, top_k: int = 10) -> list[str]:
        """Retrieve relevant memories for current task."""
        results = self.memory.search(
            query=query,
            user_id=f"agent_{self.agent_id}",
            top_k=top_k
        )
        return [r["memory"] for r in results.get("results", [])]

    def handoff(self, completed: str, next_steps: str, blockers: str = "none"):
        """Store end-of-session handoff for next agent session."""
        content = (
            f"SESSION HANDOFF: completed={completed} | "
            f"next_session_should={next_steps} | "
            f"blockers={blockers}"
        )
        return self.remember(content, category="handoff")

    def start_session(self) -> list[str]:
        """Retrieve context at the start of a session."""
        return self.recall("recent progress blockers next steps session handoff")

    @staticmethod
    def workforce_recall(query: str, top_k: int = 5) -> list[str]:
        """Retrieve shared institutional memories across all agents."""
        memory = get_memory()
        results = memory.search(
            query=query,
            user_id="veklom_workforce",
            top_k=top_k
        )
        return [r["memory"] for r in results.get("results", [])]

    @staticmethod
    def workforce_remember(content: str, category: str = "pattern"):
        """Store a memory shared by all agents."""
        memory = get_memory()
        return memory.add(
            content,
            user_id="veklom_workforce",
            metadata={"category": category, "scope": "global"}
        )


# FastAPI router for agent memory API
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/agent-memory", tags=["agent-memory"])

class MemoryRequest(BaseModel):
    content: str
    category: str = "learning"
    task: str = None

class RecallRequest(BaseModel):
    query: str
    top_k: int = 10

@router.post("/{agent_id}/remember")
async def store_memory(
    agent_id: str,
    request: MemoryRequest,
    current_user=Depends(get_current_user)
):
    """Store a memory for an agent. Admin only."""
    am = AgentMemory(agent_id)
    result = am.remember(request.content, request.category, request.task)
    return {"status": "stored", "result": result}

@router.post("/{agent_id}/recall")
async def recall_memory(
    agent_id: str,
    request: RecallRequest,
    current_user=Depends(get_current_user)
):
    """Retrieve memories for an agent."""
    am = AgentMemory(agent_id)
    memories = am.recall(request.query, request.top_k)
    return {"agent_id": agent_id, "memories": memories}

@router.get("/{agent_id}/session-start")
async def session_start_context(
    agent_id: str,
    current_user=Depends(get_current_user)
):
    """Get context for a new agent session — call at session start."""
    am = AgentMemory(agent_id)
    memories = am.start_session()
    return {"agent_id": agent_id, "context": memories}
