from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PaymentRequest(BaseModel):
    tenant_id: str
    amount: float
    asset: str = Field(default="USDC")
    capability_id: str
    execution_hash: str

class PaymentReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    amount: float
    evidence_hash: str
    status: str
    timestamp: datetime

class LedgerProofResponse(BaseModel):
    receipt_id: str
    merkle_root: str
    inclusion_proof: List[str]
    is_valid: bool
