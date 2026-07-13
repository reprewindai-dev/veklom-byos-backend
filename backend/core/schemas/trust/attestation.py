"""
SourceAttestation — RepoGate source integrity record.

A SourceAttestation is RepoGate's signed claim about the provenance
and integrity of source code or artifacts before they are executed.

Standards alignment:
  - in-toto:  Attestation is structured as an in-toto Statement
              (https://in-toto.io/Statement/v1)
  - SLSA:     slsa_level declares the SLSA Provenance Level
              (https://slsa.dev/spec/v1.0/levels)
  - DSSE:     The attestation body is wrapped in a DSSE envelope
              (same pattern as PGLReceipt)

SLSA Level mapping for Veklom:
  LEVEL_0: No provenance. Source is unverified. RepoGate blocks execution.
  LEVEL_1: Provenance documented. Build script exists. Execution allowed with warning.
  LEVEL_2: Hosted build service. Coolify pipeline is the canonical builder.
           Gate: Coolify confirmed as build authority (Phase 6 prerequisite).
  LEVEL_3: Hardened build. Build is isolated, reproducible. Future target.

Fail-closed rule:
  If requirements.repogate_required=True and no valid SourceAttestation
  is present, execution is BLOCKED. LEVEL_0 is not a valid attestation
  for execution — it is a record of a failed attestation attempt.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field

from .pgl import DSSEEnvelope


class SLSALevel(IntEnum):
    LEVEL_0 = 0  # No provenance
    LEVEL_1 = 1  # Provenance documented
    LEVEL_2 = 2  # Hosted build service (Coolify pipeline)
    LEVEL_3 = 3  # Hardened build (future)


class RepoGateVerdict(str):
    """RepoGate evaluation verdict constants."""
    ALLOW   = "allow"
    BLOCK   = "block"
    WARN    = "warn"   # Allow with logged warning (LEVEL_1 only)


class SourceAttestation(BaseModel):
    """
    RepoGate source attestation — in-toto Statement, DSSE-wrapped, SLSA-leveled.

    The envelope field carries the full DSSE-signed payload.
    The other fields are the decoded, verified claims extracted from the
    envelope payload for fast policy evaluation without re-parsing the envelope.

    Services evaluating source integrity read slsa_level and verdict.
    The full envelope is preserved for audit and downstream re-verification.
    """
    attestation_id: str = Field(
        default_factory=lambda: f"att_{uuid.uuid4().hex}",
        description="Unique identifier for this attestation.",
    )
    connection_id: str = Field(
        description="The TrustConnection this attestation covers.",
    )
    subject_uri: str = Field(
        description="URI of the subject being attested (repo URL, artifact digest, etc.).",
    )
    subject_digest: str = Field(
        description="SHA-256 or git commit SHA of the attested subject.",
    )
    slsa_level: SLSALevel = Field(
        description="SLSA provenance level for this attestation.",
    )
    verdict: str = Field(
        description="RepoGate verdict: 'allow', 'block', or 'warn'.",
    )
    build_platform: str | None = Field(
        default=None,
        description="Build platform identifier, e.g. 'coolify/hetzner-cx22'.",
    )
    build_trigger: str | None = Field(
        default=None,
        description="What triggered this build: 'push', 'manual', 'scheduled'.",
    )
    envelope: DSSEEnvelope = Field(
        description="The full DSSE-signed attestation envelope for audit and re-verification.",
    )
    intoto_statement_type: str = Field(
        default="https://in-toto.io/Statement/v1",
        description="in-toto Statement type URI.",
    )
    predicate_type: str = Field(
        default="https://slsa.dev/provenance/v1",
        description="SLSA provenance predicate type URI.",
    )
    extra_predicates: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional predicate fields for extensibility.",
    )
    attested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    attester_id: str = Field(
        description="Identity of the RepoGate instance that produced this attestation.",
    )

    @property
    def is_execution_safe(self) -> bool:
        """True if this attestation permits execution."""
        return self.verdict in (RepoGateVerdict.ALLOW, RepoGateVerdict.WARN)
