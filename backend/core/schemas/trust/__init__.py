"""
Veklom Unified Trust Connection — Canonical Schema Surface
==========================================================
Import everything trust-related from here. Do not import from sub-modules
directly in application code — this surface is stable and versioned.

Lifecycle:
  Create  → TrustConnection + ConnectionRequirements
  Govern  → PGLReceipt + SourceAttestation
  Prove   → ExecutionAuthorization (EAT) + ConnectionContext
  Replay  → ReplayPacket + TrustCloudEvent
"""

from .connection import (
    TrustConnection,
    ConnectionRequirements,
    ConnectionStatus,
    TransportMode,
)
from .context import (
    ConnectionContext,
    W3CTraceContext,
    AmphotericTransportContext,
)
from .identity import (
    ExecutionIdentity,
    IdentityKind,
    SPIFFEIdentity,
)
from .authorization import (
    ExecutionAuthorization,
    AuthorizationScope,
    SideEffectClass,
)
from .pgl import (
    PGLReceipt,
    PGLReceiptStatus,
    DSSEEnvelope,
)
from .replay import (
    ReplayPacket,
    ReplayPacketStatus,
    ToolCallRecord,
)
from .attestation import (
    SourceAttestation,
    SLSALevel,
    RepoGateVerdict,
)
from .events import (
    TrustCloudEvent,
    ReplayIngestionEvent,
    RevocationEvent,
)

__all__ = [
    # Connection
    "TrustConnection", "ConnectionRequirements", "ConnectionStatus", "TransportMode",
    # Context
    "ConnectionContext", "W3CTraceContext", "AmphotericTransportContext",
    # Identity
    "ExecutionIdentity", "IdentityKind", "SPIFFEIdentity",
    # Authorization
    "ExecutionAuthorization", "AuthorizationScope", "SideEffectClass",
    # PGL
    "PGLReceipt", "PGLReceiptStatus", "DSSEEnvelope",
    # Replay
    "ReplayPacket", "ReplayPacketStatus", "ToolCallRecord",
    # Attestation
    "SourceAttestation", "SLSALevel", "RepoGateVerdict",
    # Events
    "TrustCloudEvent", "ReplayIngestionEvent", "RevocationEvent",
]
