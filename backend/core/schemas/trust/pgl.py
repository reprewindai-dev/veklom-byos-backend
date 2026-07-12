"""
PGLReceipt — cryptographic proof of workspace/operator governance.

A PGLReceipt is issued by the PGL authority when a workspace or operator
registers and is verified. It is the trust anchor for every connection
originating from that workspace.

Signature model:
  - Algorithm: Ed25519 (preferred) or ECDSA P-256
  - Envelope:  DSSE (Dead Simple Signing Envelope)
  - Revocation: push-based via Redis pub/sub (pgl_revoke:{workspace_id})

Cache TTL contract (from the Unified Doctrine):
  - max_ttl_seconds: declared maximum cache lifetime
  - stale_while_revalidate_seconds: window during which a stale receipt
    can be used for READ operations only, while a background refresh is
    triggered. NEVER for execution authorization.
  - A receipt that cannot be revalidated within the stale window MUST
    trigger fail-closed for any execution path.

The DSSE envelope schema here is a Python representation of the
DSSE spec (https://github.com/secure-systems-lab/dsse). The full
cryptographic verification happens in backend/core/security/pgl_keys.py
(to be created in Phase 3). This schema carries the envelope structure
so it can be validated, serialized, and forwarded between services.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class PGLReceiptStatus(str, Enum):
    ACTIVE    = "active"     # Receipt is valid and current
    REVOKED   = "revoked"    # Pushed revocation received; do not use
    EXPIRED   = "expired"    # Past max TTL without revalidation
    SUSPENDED = "suspended"  # Temporarily suspended by operator


class DSSEEnvelope(BaseModel):
    """
    DSSE (Dead Simple Signing Envelope) representation.
    https://github.com/secure-systems-lab/dsse/blob/master/envelope.md

    payload_type: URI identifying the payload schema
                  e.g. "application/vnd.veklom.pgl-receipt+json"
    payload:      Base64-encoded payload bytes
    signatures:   List of {keyid, sig} — sig is base64url-encoded
    """
    payload_type: str = Field(
        description="DSSE payload type URI identifying the payload schema.",
    )
    payload: str = Field(
        description="Base64-encoded payload. For PGLReceipt: the canonical JSON of the receipt body.",
    )
    signatures: list[dict[str, str]] = Field(
        description="List of DSSE signatures. Each entry has 'keyid' and 'sig' (base64url).",
        min_length=1,
    )


class PGLReceipt(BaseModel):
    """
    PGL workspace/operator governance receipt.

    Issued once per workspace registration. Reissued on key rotation.
    Invalidated immediately on push-revocation.

    Services that cache PGLReceipts MUST:
      1. Respect max_ttl_seconds
      2. Subscribe to pgl_revoke:{workspace_id} on Redis
      3. Flush the cache immediately on receiving a revocation event
      4. NEVER serve a revoked or expired receipt for execution authorization
    """
    receipt_id: str = Field(
        default_factory=lambda: f"pgl_{uuid.uuid4().hex}",
        description="Unique receipt identifier.",
    )
    workspace_id: str = Field(
        description="The workspace this receipt governs.",
    )
    operator_id: str = Field(
        description="The operator who owns this workspace.",
    )
    status: PGLReceiptStatus = Field(default=PGLReceiptStatus.ACTIVE)
    algorithm: str = Field(
        default="ed25519",
        description="Signing algorithm. 'ed25519' or 'ecdsa-p256'.",
    )
    public_key_id: str = Field(
        description="Key ID of the Ed25519/ECDSA public key that signed this receipt.",
    )
    envelope: DSSEEnvelope = Field(
        description="The DSSE signed envelope containing the receipt payload.",
    )
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    expires_at: datetime = Field(
        description="Hard expiry. Receipt must be reissued before this timestamp.",
    )
    max_ttl_seconds: int = Field(
        default=3600,
        description="Maximum cache lifetime for this receipt. "
                    "Consumers must not cache beyond this TTL.",
    )
    stale_while_revalidate_seconds: int = Field(
        default=300,
        description="Stale-while-revalidate window. "
                    "Receipt can serve READ-ONLY paths during this window while refresh runs. "
                    "NEVER valid for execution authorization.",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="Populated when a push-revocation event is received. "
                    "After this is set, the receipt is permanently invalid.",
    )

    @property
    def is_valid_for_execution(self) -> bool:
        """Returns True only if this receipt can authorize execution."""
        now = datetime.now(timezone.utc)
        return (
            self.status == PGLReceiptStatus.ACTIVE
            and self.revoked_at is None
            and now < self.expires_at
        )
