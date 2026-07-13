"""
ConnectionContext — the carry-forward context envelope.

This is the object that travels with a TrustConnection through every
service hop. It encodes:
  - W3C Trace Context (traceparent / tracestate) for distributed tracing
  - Amphoteric transport state (post-SPIFFE validation)
  - Resolved identity reference
  - EAT reference (jti of the single-use authorization token)
  - CAPPO decision cache (so services don't re-evaluate the same policy)

M2M context loss is solved here. Instead of each service re-deriving
transport, identity, and policy state from scratch, the ConnectionContext
is built ONCE at the connection boundary (Interlink-CAPI lane entry),
signed into the TrustConnection, and forwarded verbatim. Services READ
this context; they do not rebuild it.

The only legitimate mutation of a ConnectionContext after creation is:
  1. Appending a new hop to trace_hops (observability only).
  2. Stamping cappo_decision_cached=True after Edge CAPPO evaluates.
  3. Setting eat_consumed=True after the EAT JTI is burned.

All other fields are immutable after the context is sealed at lane entry.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


class W3CTraceContext(BaseModel):
    """
    W3C Trace Context Level 1 (https://www.w3.org/TR/trace-context/).
    Propagated as traceparent / tracestate headers across all service calls.
    """
    traceparent: str = Field(
        description="W3C traceparent header value. Format: 00-{trace_id}-{span_id}-{flags}",
    )
    tracestate: str = Field(
        default="",
        description="W3C tracestate header value. Vendor-specific trace metadata.",
    )

    @field_validator("traceparent")
    @classmethod
    def validate_traceparent_format(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) != 4 or parts[0] != "00":
            raise ValueError(
                f"traceparent must follow W3C format '00-{{trace_id}}-{{span_id}}-{{flags}}', got: {v!r}"
            )
        if len(parts[1]) != 32 or len(parts[2]) != 16 or len(parts[3]) != 2:
            raise ValueError(
                "traceparent field lengths must be: trace_id=32, span_id=16, flags=2 hex chars"
            )
        return v


class AmphotericTransportContext(BaseModel):
    """
    Transport state as evaluated by the Amphoteric shared library.

    Critical invariant: spiffe_verified=True is the gate that permits
    transport_mode to be anything other than UNKNOWN. If SPIFFE SVID
    validation failed or was not performed, transport_mode MUST be UNKNOWN
    and the connection MUST fail closed for any MCP or machine-trust path.

    A spoofed X-Transport: mcp header with spiffe_verified=False is
    treated as UNKNOWN transport, not as a degraded MCP connection.
    """
    transport_mode: str = Field(
        description="Verified transport mode string (matches TransportMode enum).",
    )
    spiffe_verified: bool = Field(
        default=False,
        description="True only if a valid SPIFFE X.509 SVID was present and verified via mTLS.",
    )
    spiffe_id: str | None = Field(
        default=None,
        description="Authenticated SPIFFE ID, e.g. spiffe://veklom.io/ns/byos/svc/capi. "
                    "Only populated when spiffe_verified=True.",
    )
    raw_transport_header: str | None = Field(
        default=None,
        description="Original X-Transport header value, preserved for audit. "
                    "Never used for authorization — only spiffe_id is authoritative.",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @field_validator("spiffe_id")
    @classmethod
    def spiffe_id_must_match_scheme(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("spiffe://"):
            raise ValueError(f"spiffe_id must start with 'spiffe://', got: {v!r}")
        return v


class ConnectionContext(BaseModel):
    """
    The full carry-forward context for a TrustConnection.

    Sealed at lane entry by Interlink-CAPI. Read-only at every downstream
    service. Mutations are restricted to the three cases documented in
    the module docstring above.
    """
    connection_id: str = Field(
        description="Foreign key to TrustConnection.connection_id.",
    )
    trace: W3CTraceContext
    transport: AmphotericTransportContext
    identity_id: str = Field(
        description="Foreign key to ExecutionIdentity.identity_id.",
    )
    eat_jti: str | None = Field(
        default=None,
        description="JTI of the ExecutionAuthorization Token bound to this context. "
                    "None means no EAT has been issued yet — do not execute side-effect ops.",
    )
    eat_consumed: bool = Field(
        default=False,
        description="True after the EAT JTI has been burned via jti_guard. "
                    "Prevents double-execution of side-effect operations.",
    )
    cappo_policy_id: str | None = Field(
        default=None,
        description="The CAPPO policy evaluated for this context.",
    )
    cappo_decision_cached: bool = Field(
        default=False,
        description="True after Edge CAPPO has evaluated and cached the ALLOW decision. "
                    "Inside CAPPO still evaluates independently for mid-flight re-auth.",
    )
    cappo_decision_expires_at: datetime | None = Field(
        default=None,
        description="Expiry of the cached CAPPO ALLOW decision. "
                    "After this timestamp, Inside CAPPO must re-evaluate.",
    )
    pgl_receipt_id: str | None = Field(
        default=None,
        description="Foreign key to PGLReceipt.receipt_id for the workspace authorizing this context.",
    )
    trace_hops: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only log of service hops for distributed tracing. "
                    "Each entry: {service, timestamp, span_id}.",
    )
    sealed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when this context was sealed at lane entry. Immutable after creation.",
    )
