"""
ExecutionIdentity — who or what is executing.

Veklom's trust model recognizes four first-class identity kinds:
  HUMAN     — a verified human user with a wallet or auth session
  AGENT     — an AI agent operating autonomously or semi-autonomously
  SERVICE   — a backend microservice calling another service
  WORKLOAD  — a container/process attested by SPIFFE/SPIRE

The identity kind determines which trust signals are authoritative:
  HUMAN    → wallet signature or OAuth token
  AGENT    → PGL-governed workspace identity + EAT
  SERVICE  → SPIFFE SVID (mTLS)
  WORKLOAD → SPIFFE SVID (mTLS) + docker workload attestation

This is the schema. Verification logic lives in backend/core/security/.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class IdentityKind(str, Enum):
    HUMAN    = "human"
    AGENT    = "agent"
    SERVICE  = "service"
    WORKLOAD = "workload"


class SPIFFEIdentity(BaseModel):
    """
    A verified SPIFFE workload identity.
    Populated only after SPIRE SVID validation succeeds.
    """
    spiffe_id: str = Field(
        description="Full SPIFFE ID, e.g. spiffe://veklom.io/ns/byos/svc/capi",
    )
    trust_domain: str = Field(
        description="SPIFFE trust domain, e.g. veklom.io",
    )
    service_name: str = Field(
        description="Short service identifier extracted from the SPIFFE path.",
    )
    svid_expires_at: str | None = Field(
        default=None,
        description="ISO-8601 expiry of the X.509 SVID. Agents must not cache past this.",
    )

    @field_validator("spiffe_id")
    @classmethod
    def must_use_spiffe_scheme(cls, v: str) -> str:
        if not v.startswith("spiffe://"):
            raise ValueError(f"SPIFFE ID must start with spiffe://, got: {v!r}")
        return v

    @field_validator("trust_domain")
    @classmethod
    def must_match_veklom_domain(cls, v: str) -> str:
        # Enforce that workloads come from the veklom trust domain.
        # Extend this list when federating with external trust domains.
        allowed_domains = {"veklom.io", "veklom.local", "veklom.test"}
        if v not in allowed_domains:
            raise ValueError(
                f"Untrusted SPIFFE domain: {v!r}. Allowed: {allowed_domains}"
            )
        return v


class ExecutionIdentity(BaseModel):
    """
    The resolved, verified identity of the execution principal.

    An ExecutionIdentity is built once at connection entry and carried
    forward in ConnectionContext.identity_id. Services do not re-resolve
    identity from raw tokens mid-execution — they read this object.

    The dual-identity pattern (human + agent) is first-class here:
    an agentic operation may have both a human_identity_id (the user
    who delegated) and an agent_identity_id (the agent executing).
    Both are recorded for auditability. The agent identity is what
    CAPPO and PGL evaluate for policy; the human identity is what
    Replay records for accountability.
    """
    identity_id: str = Field(
        default_factory=lambda: f"idn_{uuid.uuid4().hex}",
        description="Unique ID for this resolved identity snapshot.",
    )
    kind: IdentityKind
    subject: str = Field(
        description="Primary subject identifier. "
                    "For HUMAN: wallet address or user_id. "
                    "For AGENT: agent_id from PGL workspace. "
                    "For SERVICE/WORKLOAD: SPIFFE ID.",
    )
    workspace_id: str | None = Field(
        default=None,
        description="PGL workspace ID. Required for AGENT kind.",
    )
    operator_id: str | None = Field(
        default=None,
        description="Operator who owns this identity's workspace.",
    )
    spiffe: SPIFFEIdentity | None = Field(
        default=None,
        description="Populated for SERVICE and WORKLOAD kinds after SPIRE validation.",
    )
    delegated_by: str | None = Field(
        default=None,
        description="identity_id of the human principal who delegated to this agent. "
                    "Preserves the human-in-the-loop accountability chain.",
    )
    verified_claims: dict[str, Any] = Field(
        default_factory=dict,
        description="Verified claims from the identity token (JWT, SVID, wallet sig). "
                    "Structure depends on identity kind.",
    )
    trust_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional normalized trust score (0.0–1.0) from the Slash scoring system. "
                    "Used by CAPPO for risk-based policy decisions.",
    )

    @field_validator("identity_id")
    @classmethod
    def validate_identity_id_prefix(cls, v: str) -> str:
        if not v.startswith("idn_"):
            raise ValueError("identity_id must be prefixed 'idn_'")
        return v
