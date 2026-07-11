"""PGL Identity Lifecycle — Probation, Trust Levels, and Annual Renewal.

The lifecycle mirrors real-world identity systems (driver's license model):

- Every new identity starts PROBATIONARY for 90 days
  → Can be terminated without cause during this period
- After 90 days clean: transitions to ACTIVE (trusted employee)
  → Requires formal reason + evidence to terminate
- Every 365 days: renewal is due — same ID, new expiry
  → Hard-blocked if not renewed (ID expires like a real license)
  → Warning issued 30 days before deadline
- Renewal is a PAID operation — this entire module could be sold as
  a standalone service independent of Veklom

INVARIANT: The identity ID never changes. Ever.
Re-onboarding the same actor is a no-op — existing ID is returned.
Renewal pushes the expiry date forward. That's it.

This module is pure functions only — no DB I/O.
Both backends import from here.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum

logger = logging.getLogger(__name__)

# ── Lifecycle constants ───────────────────────────────────────────────────────
PROBATION_DAYS        = 90    # 3 months before full trust
RENEWAL_INTERVAL_DAYS = 365   # Annual renewal window
RENEWAL_WARNING_DAYS  = 30    # Warn this many days before expiry
GRACE_PERIOD_DAYS     = 14    # 14-day grace period after expiry — agents still run
# ─────────────────────────────────────────────────────────────────────────────


class TrustLevel(str, Enum):
    """
    Where in the trust lifecycle is this identity?

    Modelled after real-world employment and professional licensing:
    - PROBATIONARY = new hire, first 90 days, no benefits, can be let go freely
    - ACTIVE       = passed probation, full trust, needs cause to terminate
    - RENEWAL_DUE  = ID expiring soon — warn, still allow execution
    - GRACE_PERIOD = 1-14 days past deadline — daily reminders, still runs
    - HARD_EXPIRED = > 14 days past deadline — hard block until renewed
    """
    PROBATIONARY = "PROBATIONARY"
    ACTIVE       = "ACTIVE"
    RENEWAL_DUE  = "RENEWAL_DUE"
    GRACE_PERIOD = "GRACE_PERIOD"
    HARD_EXPIRED = "HARD_EXPIRED"


class LifecycleStatus:
    """Computed lifecycle snapshot for a PGL identity at a point in time."""

    def __init__(
        self,
        trust_level:        TrustLevel,
        probation_ends_at:  datetime,
        renewal_due_at:     datetime,
        days_in_service:    int,
        days_until_renewal: int,
        can_execute:        bool,
        warning:            str | None = None,
        grace_day:          int | None = None,
        hard_block_date:    datetime | None = None,
    ) -> None:
        self.trust_level        = trust_level
        self.probation_ends_at  = probation_ends_at
        self.renewal_due_at     = renewal_due_at
        self.days_in_service    = days_in_service
        self.days_until_renewal = days_until_renewal
        self.can_execute        = can_execute
        self.warning            = warning
        self.grace_day          = grace_day
        self.hard_block_date    = hard_block_date

    def to_dict(self) -> dict:
        return {
            "trust_level":        self.trust_level.value,
            "probation_ends_at":  self.probation_ends_at.isoformat(),
            "renewal_due_at":     self.renewal_due_at.isoformat(),
            "days_in_service":    self.days_in_service,
            "days_until_renewal": self.days_until_renewal,
            "can_execute":        self.can_execute,
            "warning":            self.warning,
            "grace_day":          self.grace_day,
            "hard_block_date":    self.hard_block_date.isoformat() if self.hard_block_date else None,
        }


def compute_lifecycle(
    metadata: dict,
    created_at: datetime,
    active_attestations: int = 0,
    active_rollbacks: int = 0,
) -> LifecycleStatus:
    """
    Compute current lifecycle status from stored metadata + creation date + behavioral telemetry.

    Pure function — takes what's in the DB, returns current status.
    Call this any time you need to know: can this identity execute right now?

    Args:
        metadata:            metadata_json from PGLIdentity (or provenance_json from cert)
        created_at:          When the identity was originally issued
        active_attestations: Successful attestation count for the identity
        active_rollbacks:    Count of rollback/failure events for the identity

    Returns:
        LifecycleStatus — check .can_execute before allowing the action
    """
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    days_in_service   = (now - created_at).days
    probation_ends_at = created_at + timedelta(days=PROBATION_DAYS)

    # Renewal clock starts from last renewal (or creation if never renewed)
    last_renewed_raw = metadata.get("last_renewed_at")
    if last_renewed_raw:
        try:
            last_renewed = datetime.fromisoformat(last_renewed_raw)
            if last_renewed.tzinfo is None:
                last_renewed = last_renewed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            last_renewed = created_at
    else:
        last_renewed = created_at

    renewal_due_at     = last_renewed + timedelta(days=RENEWAL_INTERVAL_DAYS)
    days_until_renewal = (renewal_due_at - now).days
    hard_block_date    = renewal_due_at + timedelta(days=GRACE_PERIOD_DAYS)

    # Trust level resolution — precedence: HARD_EXPIRED > GRACE_PERIOD > RENEWAL_DUE > PROBATIONARY > ACTIVE
    if now > hard_block_date:
        return LifecycleStatus(
            trust_level=TrustLevel.HARD_EXPIRED,
            probation_ends_at=probation_ends_at,
            renewal_due_at=renewal_due_at,
            days_in_service=days_in_service,
            days_until_renewal=days_until_renewal,
            can_execute=False,
            hard_block_date=hard_block_date,
            warning=(
                f"PGL identity HARD EXPIRED on {hard_block_date.date()}. "
                f"14-day grace period has ended. "
                f"POST /api/v1/pgl/identity/renew to restore execution immediately. "
                f"Same ID, new expiry — no re-registration needed."
            ),
        )

    if now > renewal_due_at:
        grace_day = (now - renewal_due_at).days + 1
        days_remaining = (hard_block_date - now).days
        return LifecycleStatus(
            trust_level=TrustLevel.GRACE_PERIOD,
            probation_ends_at=probation_ends_at,
            renewal_due_at=renewal_due_at,
            days_in_service=days_in_service,
            days_until_renewal=days_until_renewal,
            can_execute=True,
            grace_day=grace_day,
            hard_block_date=hard_block_date,
            warning=(
                f"GRACE PERIOD — Day {grace_day} of {GRACE_PERIOD_DAYS}. "
                f"{days_remaining} day{'s' if days_remaining != 1 else ''} until hard block "
                f"({hard_block_date.date()}). "
                f"Renew NOW at POST /api/v1/pgl/identity/renew. "
                f"Your agents are still running."
            ),
        )

    if days_until_renewal <= RENEWAL_WARNING_DAYS:
        return LifecycleStatus(
            trust_level=TrustLevel.RENEWAL_DUE,
            probation_ends_at=probation_ends_at,
            renewal_due_at=renewal_due_at,
            days_in_service=days_in_service,
            days_until_renewal=days_until_renewal,
            can_execute=True,
            warning=(
                f"PGL identity renewal due in {days_until_renewal} days "
                f"({renewal_due_at.date()}). Renew at POST /api/v1/pgl/identity/renew "
                f"before the deadline or execution will be blocked."
            ),
        )

    # Behavioral promotion check: promotion from PROBATIONARY to ACTIVE requires:
    # 1. 90 days elapsed
    # 2. At least 5 successful attestations
    # 3. Exactly 0 rollbacks/failures
    has_elapsed_time = now >= probation_ends_at
    has_min_attestations = active_attestations >= 5
    has_zero_failures = active_rollbacks == 0

    if not (has_elapsed_time and has_min_attestations and has_zero_failures):
        # Still probationary or returned to probationary if behavior lapses/needs review
        days_left = max(0, (probation_ends_at - now).days)
        reasons = []
        if not has_elapsed_time:
            reasons.append(f"{days_left} days remaining")
        if not has_min_attestations:
            reasons.append(f"needs {5 - active_attestations} more successful attestations (got {active_attestations})")
        if not has_zero_failures:
            reasons.append(f"has {active_rollbacks} unresolved failures/rollbacks")
            
        return LifecycleStatus(
            trust_level=TrustLevel.PROBATIONARY,
            probation_ends_at=probation_ends_at,
            renewal_due_at=renewal_due_at,
            days_in_service=days_in_service,
            days_until_renewal=days_until_renewal,
            can_execute=True,
            warning=(
                f"PROBATIONARY — Identity is not yet promoted to ACTIVE. "
                f"Pending requirements: {', '.join(reasons)}. "
                f"During probation, this identity can be terminated without cause."
            ),
        )

    return LifecycleStatus(
        trust_level=TrustLevel.ACTIVE,
        probation_ends_at=probation_ends_at,
        renewal_due_at=renewal_due_at,
        days_in_service=days_in_service,
        days_until_renewal=days_until_renewal,
        can_execute=True,
        warning=None,
    )


def stamp_new_human_identity(
    human_id:     str,   # User.id from DB — NEVER from request body
    human_email:  str,
    workspace_id: str,
) -> dict:
    """
    Build initial metadata for a brand-new human operator PGL identity.

    human_id MUST come from the authenticated User object, not from the
    request payload. This is what locks the PGL identity to the actual
    authenticated human. Agents are then chained to this via owner_pgl_id.

    Called exactly once per human — subsequent onboarding calls are no-ops
    that return the existing identity.
    """
    now               = datetime.now(timezone.utc)
    probation_ends_at = now + timedelta(days=PROBATION_DAYS)
    renewal_due_at    = now + timedelta(days=RENEWAL_INTERVAL_DAYS)

    return {
        # Human anchor — the chain root
        "human_id":          human_id,
        "human_email":       human_email,
        "workspace_id":      workspace_id,
        "kind":              "HUMAN_OPERATOR",

        # Lifecycle stamps
        "trust_level":       TrustLevel.PROBATIONARY.value,
        "status":            "ACTIVE",
        "probation_ends_at": probation_ends_at.isoformat(),
        "renewal_due_at":    renewal_due_at.isoformat(),
        "last_renewed_at":   None,
        "renewal_count":     0,

        # Audit
        "created_at":        now.isoformat(),
        "onboarded_at":      now.isoformat(),
        "identity_version":  1,
        "source":            "pgl_onboarding",
    }


def stamp_new_agent_identity(
    agent_id:     str,
    agent_name:   str,
    owner_pgl_id: str,   # Human operator's PGLIdentity.id
    workspace_id: str,
) -> dict:
    """
    Build initial metadata for an agent identity.

    owner_pgl_id is the PGLIdentity.id of the human who owns this agent.
    This is the chain: human PGL ID → agent PGL ID → all agent actions.
    Every agent is traceable back to a human. Always.

    Agents start PROBATIONARY same as humans — 90 days, then ACTIVE.
    """
    now               = datetime.now(timezone.utc)
    probation_ends_at = now + timedelta(days=PROBATION_DAYS)
    renewal_due_at    = now + timedelta(days=RENEWAL_INTERVAL_DAYS)

    return {
        "agent_id":          agent_id,
        "agent_name":        agent_name,
        "owner_pgl_id":      owner_pgl_id,
        "workspace_id":      workspace_id,
        "kind":              "AGENT",

        "trust_level":       TrustLevel.PROBATIONARY.value,
        "status":            "ACTIVE",
        "probation_ends_at": probation_ends_at.isoformat(),
        "renewal_due_at":    renewal_due_at.isoformat(),
        "last_renewed_at":   None,
        "renewal_count":     0,

        "created_at":        now.isoformat(),
        "registered_at":     now.isoformat(),
        "identity_version":  1,
        "source":            "agent_registration",
    }


def build_renewal_patch(current_metadata: dict) -> dict:
    """
    Build the metadata update dict for a renewal event.

    INVARIANT: The identity ID never changes. Only the renewal_due_at
    is pushed forward. Same ID, new expiry. Exactly like a driver's license.

    This patch should be applied as:
        identity.metadata_json = build_renewal_patch(identity.metadata_json)

    In a real billing integration, you'd gate this behind a payment check
    before calling this function — no payment, no renewal, ID stays expired.
    """
    now           = datetime.now(timezone.utc)
    renewal_count = current_metadata.get("renewal_count", 0) + 1
    new_due       = now + timedelta(days=RENEWAL_INTERVAL_DAYS)

    return {
        **current_metadata,
        "last_renewed_at":  now.isoformat(),
        "renewal_due_at":   new_due.isoformat(),
        "renewal_count":    renewal_count,
        "identity_version": current_metadata.get("identity_version", 1) + 1,
        # Everything else is preserved — human_id, owner_pgl_id, probation stamps, etc.
    }
