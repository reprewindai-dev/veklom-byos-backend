from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

SCHEMA_VERSION = "2026-07-01"

class SseBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["2026-07-01"] = SCHEMA_VERSION
    stream_id: str
    run_id: str
    workspace_id: str
    event_id: str
    sequence: int = Field(ge=0)
    emitted_at: datetime
    replayable: bool = True


class RunAcceptedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    actor_id: str
    mode: Literal["sync", "stream"]
    policy_bundle: str


class RunPhasePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: Literal[
        "accepted",
        "planning",
        "tooling",
        "policy_check",
        "execution",
        "settlement",
    ]
    message: Optional[str] = None
    progress_pct: Optional[float] = Field(default=None, ge=0, le=100)


class RunTokenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["assistant", "system", "tool"]
    text: str
    token_count: Optional[int] = Field(default=None, ge=0)


class RunArtifactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: Literal["trace_node", "claim", "receipt_ref", "policy_ref"]
    artifact_id: str
    title: str
    content_type: Optional[str] = None
    uri: Optional[str] = None


class RunReceiptPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    receipt_hash: str
    trace_hash: str
    amount_vnp: int = Field(ge=0)
    settlement_status: Literal["yielded"] = "yielded"


class RunErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: Literal[
        "PROMPT_INJECTION_BLOCKED",
        "DEPTH_LIMIT_EXCEEDED",
        "POLICY_DENIED",
        "BACKEND_UNAVAILABLE",
        "SCHEMA_MISMATCH",
        "SYSTEM_ERROR",
    ]
    message: str
    trace_hash: Optional[str] = None
    slash_vnp: Optional[int] = Field(default=None, ge=0)
    retryable: bool = False


class RunHeartbeatPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server_time: datetime
    idle_for_ms: int = Field(ge=0)


class RunDonePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    final_status: Literal["succeeded", "failed", "security_blocked", "cancelled"]
    total_events: int = Field(ge=0)


class RunAcceptedEvent(SseBase):
    event: Literal["run.accepted"] = "run.accepted"
    payload: RunAcceptedPayload


class RunPhaseEvent(SseBase):
    event: Literal["run.phase"] = "run.phase"
    payload: RunPhasePayload


class RunTokenEvent(SseBase):
    event: Literal["run.token"] = "run.token"
    payload: RunTokenPayload


class RunArtifactEvent(SseBase):
    event: Literal["run.artifact"] = "run.artifact"
    payload: RunArtifactPayload


class RunReceiptEvent(SseBase):
    event: Literal["run.receipt"] = "run.receipt"
    payload: RunReceiptPayload


class RunErrorEvent(SseBase):
    event: Literal["run.error"] = "run.error"
    payload: RunErrorPayload


class RunHeartbeatEvent(SseBase):
    event: Literal["run.heartbeat"] = "run.heartbeat"
    payload: RunHeartbeatPayload


class RunDoneEvent(SseBase):
    event: Literal["run.done"] = "run.done"
    payload: RunDonePayload


SseEvent = Annotated[
    Union[
        RunAcceptedEvent,
        RunPhaseEvent,
        RunTokenEvent,
        RunArtifactEvent,
        RunReceiptEvent,
        RunErrorEvent,
        RunHeartbeatEvent,
        RunDoneEvent,
    ],
    Field(discriminator="event"),
]
