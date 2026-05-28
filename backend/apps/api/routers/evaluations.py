"""Evaluation bootstrap routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.apps.api.routers.auth import create_eval_session
from backend.core.database.database import get_db

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post("/start")
async def start_evaluation(body: dict = None, db: AsyncSession = Depends(get_db)):
    """
    Compatibility alias for evaluation bootstrap used by smoke/user onboarding flows.
    """
    return await create_eval_session(body=body or {}, db=db)

