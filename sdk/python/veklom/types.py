from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class CompletionResponse(BaseModel):
    id: str
    model: str
    text: str
    audit_log_id: Optional[str] = Field(default=None, alias="audit_log_id")
    provider: str
    tokens_used: int
    cost_usd: float
    content_safety_score: float
    raw_response: Dict[str, Any]
