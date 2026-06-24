from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid
import time
import hashlib

router = APIRouter()

# --- Schemas ---

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

class ChainRunRecord(BaseModel):
    chain_run_id: str
    chain_id: str
    workspace_id: str
    user_id: str
    input_hash: str
    output_hash: Optional[str] = None
    model: str
    tools_used: List[str]
    tokens_used: int
    cost_cents: float
    status: str
    error: Optional[str] = None
    started_at: float
    finished_at: Optional[float] = None
    audit_hash: Optional[str] = None

class ToolDefinition(BaseModel):
    name: str
    description: str
    version: str

# --- In-Memory Mock Database ---
CHAINS = {}
RUNS = {}
TOOLS = {}

# --- Endpoints ---

@router.get("/status")
async def get_status():
    """Health and stats for the ChainOps engine."""
    return {
        "status": "operational",
        "chains_registered": len(CHAINS),
        "runs_executed": len(RUNS),
        "tools_available": len(TOOLS),
    }

@router.post("/chains/import")
async def import_chain(chain: ChainDefinition):
    """Register a config-driven chain."""
    chain_id = f"ch_{uuid.uuid4().hex[:8]}"
    CHAINS[chain_id] = chain.dict()
    return {"status": "imported", "chain_id": chain_id, "chain": CHAINS[chain_id]}

@router.get("/chains")
async def list_chains(workspace_id: Optional[str] = None):
    """List all chains, optionally filtered by workspace."""
    if workspace_id:
        filtered = {k: v for k, v in CHAINS.items() if v.get("workspace_id") == workspace_id}
        return {"chains": filtered}
    return {"chains": CHAINS}

@router.post("/chains/{chain_id}/run")
async def run_chain(chain_id: str, req: ChainRunInput):
    """Execute a chain (GPC gate -> execute -> capture trace -> SHA-256 audit hash)."""
    if chain_id not in CHAINS:
        raise HTTPException(status_code=404, detail="Chain not found.")
    
    chain = CHAINS[chain_id]
    
    # 1. GPC Policy Check (Simulated)
    if chain.get("requires_gpc"):
        # Real GPC integration pending
        pass

    raise HTTPException(
        status_code=501, 
        detail="Enterprise LangChain engine not yet attached. Simulated execution has been disabled per enterprise hardening."
    )

@router.get("/runs")
async def list_runs():
    """All runs with cost totals, token totals, fail count — powers Command Center."""
    total_cost = sum(run.get("cost_cents", 0) for run in RUNS.values())
    total_tokens = sum(run.get("tokens_used", 0) for run in RUNS.values())
    failed = sum(1 for run in RUNS.values() if run.get("status") == "failed")
    
    return {
        "total_runs": len(RUNS),
        "total_cost_cents": total_cost,
        "total_tokens": total_tokens,
        "failed_runs": failed,
        "runs": RUNS
    }

@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Full trace + immutable audit record for one run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found.")
    return RUNS[run_id]

@router.get("/traces")
async def list_traces():
    """Evidence artifact feed sorted by recency."""
    sorted_runs = sorted(RUNS.values(), key=lambda r: r["started_at"], reverse=True)
    return {"traces": sorted_runs}

@router.post("/tools/register")
async def register_tool(tool: ToolDefinition):
    """Register marketplace tools as LangChain-compatible tools."""
    tool_id = f"tool_{uuid.uuid4().hex[:8]}"
    TOOLS[tool_id] = tool.dict()
    return {"status": "registered", "tool_id": tool_id, "tool": TOOLS[tool_id]}

@router.get("/tools")
async def list_tools():
    """List all ChainOps tools."""
    return {"tools": TOOLS}
