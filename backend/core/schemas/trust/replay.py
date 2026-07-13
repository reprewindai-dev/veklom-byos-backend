"""
ReplayPacket v1 — content-addressed execution evidence.

A ReplayPacket is the tamper-evident record of a TrustConnection's
full execution lifecycle. It is the product of the "Prove" and "Replay"
phases of the Veklom doctrine.

Content addressing:
  Every ReplayPacket has a packet_id formatted as sha256:{hex_digest}
  computed from the canonical JSON of the packet body (excluding the
  packet_id field itself). This allows auditors to:
    1. Pull a specific packet by content hash without hydrating a full session
    2. Verify the packet has not been tampered with post-storage
    3. Reference packets in attestations and evidence chains by hash

Decision locked: internal SHA-256 as the lookup key (not IPFS CID).
Storage: Postgres (content_hash indexed column) + Redis cache.
Future: CID export for decentralized audit.

Ingestion contract:
  CAPPO, BYOS, PGL, and x402 do NOT write to ReplayPacket storage directly.
  They emit TrustCloudEvents to the unified ingestion contract at
  backend/core/replay/ingestion.py (Phase 6). Replay owns the schema.
  Replay owns the write path. Everything else is a CloudEvent emitter.

Random access:
  Segments (individual ToolCallRecords) are independently retrievable
  by their own tool_call_id. An auditor requesting evidence for a specific
  tool call does not need to hydrate the full ReplayPacket.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ReplayPacketStatus(str, Enum):
    OPEN       = "open"       # Connection still executing; packet is growing
    FINALIZED  = "finalized"  # Connection completed; packet is sealed and hashed
    FAILED     = "failed"     # Connection failed; partial packet preserved
    CORRUPTED  = "corrupted"  # Content hash mismatch detected post-storage


class ToolCallRecord(BaseModel):
    """
    A single tool call event within a ReplayPacket.
    Independently retrievable by tool_call_id.

    This is the M2M information unit. Every time an agent calls a tool,
    a ToolCallRecord is emitted. The record carries enough context that
    any downstream service — or a future auditor — can reconstruct
    exactly what happened, why it was authorized, and what resulted.
    """
    tool_call_id: str = Field(
        default_factory=lambda: f"tc_{uuid.uuid4().hex}",
        description="Unique identifier for this tool call. Used for random access.",
    )
    connection_id: str = Field(
        description="Parent TrustConnection.connection_id.",
    )
    tool_name: str = Field(
        description="The name of the tool called, e.g. 'execute_code', 'send_payment'.",
    )
    tool_version: str = Field(
        default="unknown",
        description="Semver of the tool implementation. For auditability.",
    )
    called_by: str = Field(
        description="ExecutionIdentity.identity_id of the caller.",
    )
    eat_jti: str | None = Field(
        default=None,
        description="JTI of the EAT that authorized this specific tool call, if side-effect bearing.",
    )
    input_hash: str = Field(
        description="SHA-256 of the canonical JSON-encoded tool input. "
                    "The raw input is NOT stored here — only its hash. "
                    "Prevents sensitive data leakage into the replay log.",
    )
    output_hash: str | None = Field(
        default=None,
        description="SHA-256 of the canonical JSON-encoded tool output. "
                    "Populated after the tool call completes.",
    )
    side_effects_produced: list[str] = Field(
        default_factory=list,
        description="SideEffectClass values produced by this tool call.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: datetime | None = None
    duration_ms: int | None = Field(
        default=None,
        description="Wall-clock duration in milliseconds.",
    )
    success: bool | None = Field(
        default=None,
        description="True if the tool call completed without error.",
    )
    error_code: str | None = None
    traceparent: str | None = Field(
        default=None,
        description="W3C traceparent at the moment of this tool call for trace correlation.",
    )


class ReplayPacket(BaseModel):
    """
    The full content-addressed execution evidence packet.

    packet_id is computed as sha256:{hex_digest} of the packet body.
    It is set by the finalize() method — not at construction time.
    During OPEN status, packet_id is a provisional ID prefixed 'pkt_'.
    """
    packet_id: str = Field(
        default_factory=lambda: f"pkt_{uuid.uuid4().hex}",
        description="Provisional ID during OPEN status. "
                    "Replaced with 'sha256:{hex}' by finalize().",
    )
    connection_id: str = Field(
        description="The TrustConnection this packet records.",
    )
    workspace_id: str = Field(
        description="Workspace that owned the connection.",
    )
    identity_id: str = Field(
        description="ExecutionIdentity.identity_id of the primary principal.",
    )
    pgl_receipt_id: str | None = Field(
        default=None,
        description="PGLReceipt.receipt_id that was active during execution.",
    )
    status: ReplayPacketStatus = Field(default=ReplayPacketStatus.OPEN)
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list,
        description="Ordered list of tool call records. Append-only during OPEN status.",
    )
    traceparent: str | None = Field(
        default=None,
        description="W3C traceparent of the root span for this connection.",
    )
    opened_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    finalized_at: datetime | None = None
    schema_version: str = Field(
        default="1.0",
        description="ReplayPacket schema version. Increment on breaking changes.",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Service-defined extra fields for extensibility. Not used for verification.",
    )

    def _compute_hash(self) -> str:
        """Compute SHA-256 of the canonical packet body (excluding packet_id)."""
        body = self.model_dump(exclude={"packet_id", "finalized_at"})
        canonical = json.dumps(body, sort_keys=True, default=str, ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def finalize(self) -> "ReplayPacket":
        """
        Seal this packet. Sets packet_id to the content hash,
        status to FINALIZED, and finalized_at to now.

        Returns self for chaining. The ReplayPacket is now immutable
        by convention — no tool_calls should be appended after finalize().
        """
        content_hash = self._compute_hash()
        self.packet_id = f"sha256:{content_hash}"
        self.status = ReplayPacketStatus.FINALIZED
        self.finalized_at = datetime.now(timezone.utc)
        return self

    def verify_integrity(self) -> bool:
        """
        Re-compute the content hash and verify it matches the stored packet_id.
        Returns True if the packet has not been tampered with.
        """
        if not self.packet_id.startswith("sha256:"):
            return False  # Not yet finalized
        stored_hash = self.packet_id.removeprefix("sha256:")
        recomputed = self._compute_hash()
        return recomputed == stored_hash
