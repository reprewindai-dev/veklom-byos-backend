from __future__ import annotations

from datetime import datetime
from typing import Literal, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from backend.contracts.sse_models import SCHEMA_VERSION


class VnpBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["2026-07-01"] = SCHEMA_VERSION
    chain_id: str
    block_index: int = Field(ge=0)
    prev_hash: str
    block_hash: str
    stream_id: str
    run_id: str
    workspace_id: str
    event_id: str
    transition: Literal["yield", "slash"]
    amount_vnp: int
    reason_code: Literal[
        "RUN_SUCCESS",
        "PROMPT_INJECTION_BLOCKED",
        "DEPTH_LIMIT_EXCEEDED",
        "POLICY_DENIED",
        "SYSTEM_ERROR",
    ]
    trace_hash: str
    receipt_hash: Optional[str] = None
    policy_ref: Optional[str] = None
    emitted_at: datetime
    metadata: Dict[str, Union[str, int, float, bool, None]] = Field(default_factory=dict)
