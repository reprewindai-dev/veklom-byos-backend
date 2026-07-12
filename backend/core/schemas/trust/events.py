"""
Trust CloudEvent schemas — the unified Replay ingestion contract.

All trust-bearing events flowing into Replay are wrapped in the
TrustCloudEvent envelope, which aligns with the CloudEvents spec v1.0
(https://cloudevents.io/).

Ingestion rule (from the Unified Doctrine):
  CAPPO, BYOS, PGL, and x402 do NOT write to Replay storage directly.
  They emit TrustCloudEvents. Replay's ingestion contract
  (backend/core/replay/ingestion.py, Phase 6) is the only writer.

This design solves two problems at once:
  1. Replay schema integrity: only one writer, one schema, one version.
  2. M2M event loss: every service-to-service trust event is a
     structured, versioned, traceable record. Nothing is fire-and-forget.

Event types defined here:
  veklom.trust.replay.tool_call       — a ToolCallRecord to ingest
  veklom.trust.replay.connection      — connection lifecycle transition
  veklom.trust.pgl.revoked            — workspace revocation (push-based)
  veklom.trust.cappo.decision         — CAPPO policy decision record
  veklom.trust.x402.payment           — x402 payment receipt
  veklom.trust.repogate.attestation   — source attestation event
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class TrustCloudEvent(BaseModel):
    """
    CloudEvents v1.0 envelope for all Veklom trust events.

    Required CloudEvents attributes:
      specversion, id, source, type, time

    Veklom extensions (all prefixed 'veklom'):
      veklomconnectionid — TrustConnection.connection_id
      veklomworkspaceid  — PGL workspace_id
      veklomtraceparent  — W3C traceparent for cross-event trace correlation
    """
    specversion: Literal["1.0"] = "1.0"
    id: str = Field(
        default_factory=lambda: f"ce_{uuid.uuid4().hex}",
        description="Unique CloudEvent identifier.",
    )
    source: str = Field(
        description="URI identifying the event source service, "
                    "e.g. '/byos/cappo', '/byos/pgl', '/byos/x402'.",
    )
    type: str = Field(
        description="CloudEvent type, e.g. 'veklom.trust.replay.tool_call'.",
    )
    datacontenttype: str = Field(
        default="application/json",
    )
    time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    # Veklom extensions
    veklomconnectionid: str | None = Field(
        default=None,
        description="TrustConnection.connection_id this event belongs to.",
    )
    veklomworkspaceid: str | None = Field(
        default=None,
        description="PGL workspace_id this event belongs to.",
    )
    veklomtraceparent: str | None = Field(
        default=None,
        description="W3C traceparent for cross-event distributed tracing.",
    )
    data: dict[str, Any] = Field(
        description="The event payload. Schema depends on event type.",
    )

    @classmethod
    def from_tool_call(
        cls,
        tool_call: Any,  # ToolCallRecord — avoid circular import
        workspace_id: str,
        traceparent: str | None = None,
    ) -> "TrustCloudEvent":
        """Convenience factory for ToolCallRecord ingestion events."""
        return cls(
            source="/byos/replay",
            type="veklom.trust.replay.tool_call",
            veklomconnectionid=tool_call.connection_id,
            veklomworkspaceid=workspace_id,
            veklomtraceparent=traceparent,
            data=tool_call.model_dump(),
        )


class ReplayIngestionEvent(TrustCloudEvent):
    """
    Specialization of TrustCloudEvent for Replay ingestion.
    The ingestion contract at backend/core/replay/ingestion.py
    accepts ReplayIngestionEvent objects from all services.
    """
    type: str = Field(default="veklom.trust.replay.ingest")
    packet_id: str = Field(
        description="Target ReplayPacket.packet_id (provisional or content-addressed).",
    )


class RevocationEvent(TrustCloudEvent):
    """
    PGL push-revocation event.
    Published to Redis channel: pgl_revoke:{workspace_id}
    Consumed by RevocationManager in backend/core/security/governance.py
    to aggressively flush in-memory PGL receipt caches.
    """
    type: str = Field(default="veklom.trust.pgl.revoked")
    revoked_workspace_id: str = Field(
        description="The workspace_id being revoked.",
    )
    revoked_by: str = Field(
        description="identity_id or operator_id that triggered the revocation.",
    )
    reason: str | None = Field(
        default=None,
        description="Optional human-readable revocation reason for audit.",
    )
    effective_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Revocation is effective immediately. "
                    "Any cached PGL receipt must be invalidated on receipt of this event.",
    )
