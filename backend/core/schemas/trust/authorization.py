"""
ExecutionAuthorization (EAT) — the single-use execution token.

An EAT is a short-lived, single-use authorization token that gates
execution of any operation with declared side effects (payment, deletion,
deployment, agent-to-agent delegation).

Alignment: RFC 9068 (JWT Access Tokens for OAuth 2.0 Workload Identity).

The single-use invariant is absolute:
  - Any EAT bound to a side-effect operation can only be consumed ONCE.
  - Consumption is recorded in jti_guard (Redis NX set, confirmed by today's
    SafeRedisClient nx fix: commit fceec71).
  - A second attempt to consume the same JTI fails closed — the operation
    does NOT proceed.
  - This applies even if the first execution result is unknown (network error).
    The caller must obtain a new EAT for a retry, creating an explicit audit
    trail of the retry intent.

Why this solves the M2M bottleneck:
  Without EATs, agents operating across service boundaries have no way to
  signal "I have been authorized for THIS specific action, ONCE, and the
  authorization expires in 30 seconds." They either re-auth on every hop
  (expensive, slow) or carry a long-lived token that can be replayed (unsafe).
  The EAT is the narrow, expiring, scoped credential that makes M2M trust
  both fast and safe.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SideEffectClass(str, Enum):
    """
    Declared classes of irreversible side effects.
    Any operation producing one of these MUST use a single-use EAT.
    """
    PAYMENT       = "payment"       # x402 or on-chain payment
    DELETION      = "deletion"      # permanent data deletion
    DEPLOYMENT    = "deployment"    # infrastructure or code deployment
    DELEGATION    = "delegation"    # agent-to-agent authority delegation
    SIGNING       = "signing"       # cryptographic signing on behalf of workspace
    DATA_EXPORT   = "data_export"   # exporting data outside the trust boundary


class AuthorizationScope(BaseModel):
    """The narrowly-scoped capability this EAT authorizes."""
    resource: str = Field(
        description="The resource being authorized, e.g. 'workspace:ws_abc/execute'.",
    )
    action: str = Field(
        description="The specific action, e.g. 'run', 'pay', 'delete', 'deploy'.",
    )
    side_effects: list[SideEffectClass] = Field(
        default_factory=list,
        description="Declared side effect classes. If non-empty, this EAT is strictly single-use.",
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional constraints, e.g. {'max_amount_usdc': '10.00', 'target_env': 'prod'}.",
    )


class ExecutionAuthorization(BaseModel):
    """
    Execution Authorization Token (EAT).

    RFC 9068 alignment:
      - jti     → globally unique token identifier (UUID4 hex)
      - sub     → subject (identity_id of the authorized principal)
      - iss     → issuer (veklom PGL authority URI)
      - aud     → audience (the service/resource that will consume this EAT)
      - iat     → issued-at (UTC)
      - exp     → expiry (UTC, hard limit)
      - scope   → AuthorizationScope (what is authorized)

    The eat_id field is the stable object ID. The jti is the one-time-use
    token identifier tracked by jti_guard for single-use enforcement.
    """
    eat_id: str = Field(
        default_factory=lambda: f"eat_{uuid.uuid4().hex}",
        description="Stable EAT object identifier. Survives across retry EAT issuances.",
    )
    jti: str = Field(
        default_factory=lambda: uuid.uuid4().hex,
        description="Single-use JWT ID. Burned by jti_guard on first consumption.",
    )
    sub: str = Field(
        description="Subject: ExecutionIdentity.identity_id of the authorized principal.",
    )
    iss: str = Field(
        default="https://pgl.veklom.io",
        description="Issuer: PGL authority URI.",
    )
    aud: str = Field(
        description="Audience: the service that will consume and burn this EAT.",
    )
    connection_id: str = Field(
        description="The TrustConnection this EAT is bound to. EATs cannot be transferred.",
    )
    scope: AuthorizationScope
    iat: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    exp: datetime = Field(
        description="Hard expiry. After this time, the EAT is invalid regardless of JTI state.",
    )
    consumed: bool = Field(
        default=False,
        description="Set to True after jti_guard.consume() succeeds. "
                    "Application state mirror of the Redis JTI record.",
    )
    consumed_at: datetime | None = None

    @field_validator("eat_id")
    @classmethod
    def validate_eat_prefix(cls, v: str) -> str:
        if not v.startswith("eat_"):
            raise ValueError("eat_id must be prefixed 'eat_'")
        return v

    @model_validator(mode="after")
    def exp_must_be_future_of_iat(self) -> "ExecutionAuthorization":
        if self.exp <= self.iat:
            raise ValueError("EAT exp must be strictly after iat")
        if (self.exp - self.iat) > timedelta(hours=1):
            raise ValueError(
                "EAT lifetime exceeds 1 hour maximum. "
                "Issue shorter-lived EATs for tighter execution windows."
            )
        return self

    @property
    def is_side_effect_bearing(self) -> bool:
        """True if this EAT authorizes any irreversible side effect."""
        return len(self.scope.side_effects) > 0

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.exp

    def is_consumable(self) -> bool:
        """Returns True only if this EAT can still be used."""
        return not self.consumed and not self.is_expired

    @classmethod
    def for_connection(
        cls,
        connection_id: str,
        identity_id: str,
        resource: str,
        action: str,
        audience: str,
        side_effects: list[SideEffectClass] | None = None,
        ttl_seconds: int = 300,
        constraints: dict[str, Any] | None = None,
    ) -> "ExecutionAuthorization":
        """Factory method — the preferred way to mint a new EAT."""
        now = datetime.now(timezone.utc)
        return cls(
            sub=identity_id,
            aud=audience,
            connection_id=connection_id,
            iat=now,
            exp=now + timedelta(seconds=ttl_seconds),
            scope=AuthorizationScope(
                resource=resource,
                action=action,
                side_effects=side_effects or [],
                constraints=constraints or {},
            ),
        )
