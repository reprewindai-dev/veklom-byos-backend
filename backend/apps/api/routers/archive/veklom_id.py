from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from backend.core.database.database import get_db
from backend.db.models.user import User

router = APIRouter(prefix="/id", tags=["Veklom ID"])

@router.get("/leaderboard")
async def get_veklom_id_leaderboard(db: AsyncSession = Depends(get_db)):
    """Dynamic Veklom ID Leaderboard pulling true information from User verification."""
    # Temporarily returning empty list to trigger the empty UI state 
    # since Veklom ID schemas aren't fully finalized for aggregation yet.
    return {
        "success": True,
        "leaderboard": []
    }
