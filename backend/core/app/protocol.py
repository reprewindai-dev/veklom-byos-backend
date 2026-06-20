"""Angelic Payment Protocol (APP) - Universal M2M Commerce Protocol"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import hashlib


class APPStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class APPCurrency(str, Enum):
    USDC = "USDC"
    USDT = "USDT"
    ETH = "ETH"


class APPPaymentRequest(BaseModel):
    request_id: str
    amount: float
    currency: APPCurrency = APPCurrency.USDC
    from_address: str
    to_address: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APPPaymentResponse(BaseModel):
    request_id: str
    status: APPStatus
    transaction_id: Optional[str] = None
    amount: float
    fee: float = 0.0


class AngelicPaymentProtocol:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def generate_request_id(self, prefix: str = "APP") -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{prefix}-{timestamp}-{hashlib.sha256(timestamp.encode()).hexdigest()[:8]}"
