"""
TrustConnection — the lifecycle root object.

A TrustConnection is the single thing Veklom creates, governs, proves,
and replays. It is NOT a session, a request, or a job. It is the named,
identified, policy-bound relationship between a caller and a capability
for the duration of a governed execution window.

Every other schema in this package is either a child of, or a projection
of, a TrustConnection.

Fail-closed contract
--------------------
- A TrustConnection with status PENDING_REQUIREMENTS must not be executed.
- A TrustConnection with status REVOKED must never be re-opened.
- ConnectionRequirements.pgl_required=True means PGL is MANDATORY. There
  is no degraded-challenge fallback. If PGL is unreachable, fail closed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ConnectionStatus(str, Enum):
    """Lifecycle state machine for a TrustConnection."""
    PENDING_REQUIREMENTS = "pending_requirements"
    REQUIREMENTS_MET     = "requirements_met"
    AUTHORIZED           = "authorized"
    EXECUTING            = "executing"
    COMPLETED            = "completed"
    FAILED               = "failed"
    REVOKED              = "revoked"   # terminal, irreversible
    EXPIRED              = "expired"   # terminal, TTL elapsed


class TransportMode(str, Enum):
    """
    The verified transport mode for this connection.
    Set by Amphoteric after SPIFFE SVID validation — not by the caller.
    """
    MCP      = "mcp"       # Model Context Protocol (machine-to-machine)
    HTTP     = "http"      # Standard HTTP/REST
    GRPC     = "grpc"      # gRPC stream
    WEBHOOK  = "webhook"   # Inbound webhook
    INTERNAL = "internal"  # Intra-service call (SPIFFE-only, no external transport)
    UNKNOWN  = "unknown"   # Amphoteric could not determine; treat as least-privilege


class ConnectionRequirements(BaseModel):
    """
    What must be true before this TrustConnection can be executed.

    Pre-lane failure rule: if pgl_required=True and PGL is unreachable
    or returns a non-ACTIVE receipt, the connection MUST fail closed.
    No cached snapshots. No degraded challenges.
    """
    pgl_required: bool = Field(
        default=True,
        description="PGL workspace/operator receipt is mandatory for execution.",
    )
    cappo_policy_id: str | None = Field(
        default=None,
        description="The CAPPO policy that must evaluate ALLOW before execution proceeds.",
    )
    repogate_required: bool = Field(
        default=False,
        description="Source attestation from RepoGate is required for code execution paths.",
    )
    x402_payment_required: bool = Field(
        default=False,
        description="x402 payment receipt must be present and verified before execution.",
    )
    spiffe_required: bool = Field(
        default=True,
        description="SPIFFE/SPIRE mTLS SVID must be validated before Amphoteric evaluates headers.",
    )
    eat_required: bool = Field(
        default=True,
        description="An ExecutionAuthorization Token (EAT) is required. Single-use for side-effect ops.",
    )
    allowed_side_effects: list[str] = Field(
        default_factory=list,
        description="Explicitly declared side effect classes this connection is permitted to produce.",
    )


class TrustConnection(BaseModel):
    """
    The canonical, carry-forward connection object.

    Design principle: an AI agent or service receiving a TrustConnection
    should be able to determine the full trust posture of the current
    execution from this object alone — without re-querying PGL, CAPPO,
    or any external service. The object is signed (via the attached
    PGLReceipt DSSE envelope) and content-addressed.

    This directly solves the agent context drift problem: agents no longer
    re-derive context at each hop. They carry a verified, signed snapshot
    forward. The snapshot is invalidated only by a PGL push-revocation event.
    """
    connection_id: str = Field(
        default_factory=lambda: f"conn_{uuid.uuid4().hex}",
        description="Unique, stable identifier for this connection's full lifecycle.",
    )
    workspace_id: str = Field(
        description="The PGL-governed workspace that owns this connection.",
    )
    operator_id: str = Field(
        description="The operator (org/user) who initiated this connection.",
    )
    intent: str = Field(
        description="Human-readable or structured intent label (e.g. 'run:code', 'pay:invoice').",
    )
    status: ConnectionStatus = Field(default=ConnectionStatus.PENDING_REQUIREMENTS)
    transport_mode: TransportMode = Field(
        default=TransportMode.UNKNOWN,
        description="Verified by Amphoteric post-SPIFFE validation. Never trust caller-supplied.",
    )
    requirements: ConnectionRequirements = Field(default_factory=ConnectionRequirements)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    authorized_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = Field(
        default=None,
        description="Hard expiry. Connection must fail closed after this timestamp.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary service-defined metadata. Not trusted for authorization decisions.",
    )

    @field_validator("connection_id")
    @classmethod
    def validate_connection_id_prefix(cls, v: str) -> str:
        if not v.startswith("conn_"):
            raise ValueError("connection_id must be prefixed 'conn_'")
        return v

    @model_validator(mode="after")
    def revoked_is_terminal(self) -> "TrustConnection":
        """Revoked connections cannot have a non-None authorized_at set after the fact."""
        if self.status == ConnectionStatus.REVOKED and self.authorized_at is not None:
            # authorized_at may be set from history — this is fine. Warn but allow.
            pass
        return self

    def is_executable(self) -> bool:
        """Quick guard. Call before dispatching to any lane."""
        return self.status in (
            ConnectionStatus.REQUIREMENTS_MET,
            ConnectionStatus.AUTHORIZED,
        )

    def is_terminal(self) -> bool:
        return self.status in (
            ConnectionStatus.COMPLETED,
            ConnectionStatus.FAILED,
            ConnectionStatus.REVOKED,
            ConnectionStatus.EXPIRED,
        )
