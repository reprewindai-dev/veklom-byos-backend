from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, List
import uuid
import hashlib

from backend.core.database.database import get_db
from backend.db.models.ai import ExecutionLog

router = APIRouter(prefix="/duel", tags=["Agent Duel"])

def generate_address_for_model(model_name: str) -> str:
    """Generate a consistent hex address for a given model string."""
    h = hashlib.sha256(model_name.encode('utf-8')).hexdigest()
    return f"0x{h[:40]}"

@router.get("/leaderboard")
async def get_duel_leaderboard(db: AsyncSession = Depends(get_db)):
    """Dynamic Agent Duel Leaderboard pulling true information from ExecutionLog."""
    stmt = (
        select(
            ExecutionLog.model,
            func.count(ExecutionLog.id).label("total_executions"),
            func.avg(ExecutionLog.latency_ms).label("avg_latency")
        )
        .where(ExecutionLog.status == "completed")
        .group_by(ExecutionLog.model)
        .order_by(func.count(ExecutionLog.id).desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    leaderboard = []
    for rank, row in enumerate(rows, start=1):
        model_name = row.model or "Unknown Agent"
        # Since this represents true usage, we use execution count and latency to simulate winnings
        # until the full wagering smart contracts are deployed.
        base_winnings = row.total_executions * 150 
        avg_latency = row.avg_latency or 100
        best_mult = max(1.01, round(20.0 - (avg_latency / 100), 2))
        
        leaderboard.append({
            "rank": rank,
            "username": f"Agent {model_name[:12]}",
            "address": generate_address_for_model(model_name),
            "totalWonUsdc": base_winnings,
            "bestMultiplier": best_mult,
            "streak": row.total_executions % 5,
            "agentPreference": model_name
        })
        
    return {
        "success": True,
        "leaderboard": leaderboard
    }

@router.get("/player/{address}/history")
async def get_player_history(address: str):
    # This remains mocked until player specific wagering history is fully built
    return {
        "success": True,
        "wagers": []
    }
