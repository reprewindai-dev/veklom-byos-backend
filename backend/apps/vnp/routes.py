from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from backend.apps.vnp.schemas import StakeRequest, StakeResponse, SlashRequest, SlashResponse, YieldResponse
from backend.apps.vnp.vnp_service import VNPService
from backend.core.security.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/v1/vnp", tags=["VNP Staking"])

@router.post("/stake", response_model=StakeResponse)
async def create_stake(request: StakeRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Deposit a new performance bond for an operator."""
    # VNP rules require writing to logs off the hot-path
    # The service layer handles this logging logic.
    return await VNPService.register_stake(request)

@router.get("/yield", response_model=YieldResponse)
async def get_yield(stake_id: str, user=Depends(get_current_user)):
    """Get the accumulated yield for a specific stake."""
    try:
        return await VNPService.calculate_yield(stake_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/slash", response_model=SlashResponse)
async def slash_stake(request: SlashRequest, background_tasks: BackgroundTasks, user=Depends(get_current_admin)):
    """Slash an operator's stake. Requires governance/admin rights."""
    try:
        return await VNPService.execute_slash(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
