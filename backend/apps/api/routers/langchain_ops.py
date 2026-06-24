"""LangChain Ops router — enterprise hardened.

All in-memory mock stores (CHAINS, RUNS, TOOLS) have been removed.
Endpoints return HTTP 501 until the enterprise LangChain engine is
fully wired to a real database backend.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChainDefinition(BaseModel):
    name: str
    description: str
    workspace_id: str
    model: str
    tools: List[str]
    requires_gpc: bool = True


class ChainRunInput(BaseModel):
    input_text: str
    user_id: str
    workspace_id: str


class ToolDefinition(BaseModel):
    name: str
    description: str
    version: str


# ---------------------------------------------------------------------------
# Endpoints — pending enterprise LangChain engine attachment
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_status():
    """Health check for the ChainOps engine slot."""
    return {
        "status": "engine_not_attached",
        "detail": "Enterprise LangChain engine not yet attached. In-memory mock removed.",
        "chains_registered": 0,
        "runs_executed": 0,
        "tools_available": 0,
    }


@router.post("/chains/import")
async def import_chain(chain: ChainDefinition):
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached. Chain import disabled.",
    )


@router.get("/chains")
async def list_chains(workspace_id: Optional[str] = None):
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached.",
    )


@router.post("/chains/{chain_id}/run")
async def run_chain(chain_id: str, req: ChainRunInput):
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached. Simulated execution disabled.",
    )


@router.get("/runs")
async def list_runs():
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached. Run history unavailable.",
    )


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached.",
    )


@router.get("/traces")
async def list_traces():
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached.",
    )


@router.post("/tools/register")
async def register_tool(tool: ToolDefinition):
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached. Tool registration disabled.",
    )


@router.get("/tools")
async def list_tools():
    raise HTTPException(
        status_code=501,
        detail="Enterprise LangChain engine not yet attached.",
    )
