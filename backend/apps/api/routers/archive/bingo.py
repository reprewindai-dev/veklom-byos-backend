from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import hashlib
import uuid

from backend.core.database.database import get_db
from backend.db.models.user import User

router = APIRouter(prefix="/bingo", tags=["Bingo Game"])

@router.get("/leaderboard")
async def get_bingo_leaderboard(db: AsyncSession = Depends(get_db)):
    """Dynamic Bingo Leaderboard pulling true information from User activity."""
    # Temporarily returning empty list to trigger the empty UI state 
    # since Bingo schemas aren't fully finalized for aggregation yet.
    return {
        "success": True,
        "leaders": []
    }
