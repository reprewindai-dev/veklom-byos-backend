from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class StakeRequest(BaseModel):
    operator_id: str
    asset: str = Field(default="USDC")
    amount: float
    capability_id: str

class StakeResponse(BaseModel):
    stake_id: str
    operator_id: str
    amount: float
    status: str
    created_at: datetime

class SlashRequest(BaseModel):
    stake_id: str
    reason: str
    amount_to_slash: float

class SlashResponse(BaseModel):
    stake_id: str
    slashed_amount: float
    remaining_stake: float
    status: str
    timestamp: datetime

class YieldResponse(BaseModel):
    stake_id: str
    accumulated_yield: float
    last_updated: datetime
