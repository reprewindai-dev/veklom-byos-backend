from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid
import logging

from backend.apps.vnp.schemas import StakeRequest, StakeResponse, SlashRequest, SlashResponse, YieldResponse

logger = logging.getLogger(__name__)

# In-memory mock storage since DB is decoupled/mocked in tests
_mock_vnp_stakes: Dict[str, dict] = {}
_mock_vnp_yields: Dict[str, float] = {}

class VNPService:
    @staticmethod
    async def register_stake(request: StakeRequest) -> StakeResponse:
        """Register a new micro-stake for a capability operator."""
        stake_id = f"vnp_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        
        stake_record = {
            "stake_id": stake_id,
            "operator_id": request.operator_id,
            "asset": request.asset,
            "amount": request.amount,
            "capability_id": request.capability_id,
            "status": "ACTIVE",
            "created_at": now.isoformat()
        }
        
        # Simulating writing to vnp_stake_logs off the hot-path
        logger.info(f"[VNP_LOG] Recorded stake {stake_id} off hot-path.")
        _mock_vnp_stakes[stake_id] = stake_record
        _mock_vnp_yields[stake_id] = 0.0
        
        return StakeResponse(
            stake_id=stake_id,
            operator_id=request.operator_id,
            amount=request.amount,
            status="ACTIVE",
            created_at=now
        )

    @staticmethod
    async def calculate_yield(stake_id: str) -> YieldResponse:
        """Calculate and return accumulated yield for a stake."""
        if stake_id not in _mock_vnp_stakes:
            raise ValueError("Stake not found")
            
        now = datetime.now(timezone.utc)
        # Mock yield generation logic based on time
        current_yield = _mock_vnp_yields.get(stake_id, 0.0)
        # Increment slightly for demonstration
        new_yield = current_yield + 0.005
        _mock_vnp_yields[stake_id] = new_yield
        
        return YieldResponse(
            stake_id=stake_id,
            accumulated_yield=new_yield,
            last_updated=now
        )

    @staticmethod
    async def execute_slash(request: SlashRequest) -> SlashResponse:
        """Slash a stake due to SLA violation."""
        if request.stake_id not in _mock_vnp_stakes:
            raise ValueError("Stake not found")
            
        stake = _mock_vnp_stakes[request.stake_id]
        current_amount = stake["amount"]
        
        if request.amount_to_slash > current_amount:
            raise ValueError("Cannot slash more than current stake amount")
            
        remaining = current_amount - request.amount_to_slash
        stake["amount"] = remaining
        
        if remaining <= 0:
            stake["status"] = "SLASHED_EMPTY"
        else:
            stake["status"] = "SLASHED_PARTIAL"
            
        now = datetime.now(timezone.utc)
        logger.warning(f"[VNP_LOG] Slashed {request.amount_to_slash} from {request.stake_id} off hot-path.")
        
        return SlashResponse(
            stake_id=request.stake_id,
            slashed_amount=request.amount_to_slash,
            remaining_stake=remaining,
            status=stake["status"],
            timestamp=now
        )

    @staticmethod
    def get_all_active_stakes() -> List[dict]:
        """Used by Source of Truth snapshot to aggregate stakes."""
        return [s for s in _mock_vnp_stakes.values() if "SLASHED_EMPTY" not in s["status"]]
