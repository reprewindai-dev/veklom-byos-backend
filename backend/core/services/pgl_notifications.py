"""PGL Notification Engine — Transparent, Helpful, Never Blocking Without Explanation.

Every time the PGL system blocks, warns, or milestones an agent,
this module builds the user-facing notification.

DESIGN PRINCIPLES:
  1. No block is silent. Every block tells the user:
     - What happened (plain English, not error codes)
     - Why it happened
     - Exactly what to do (the API call, the URL, the step)
     - How long they have before it gets worse
  2. Reminders escalate in tone — friendly → urgent → critical
  3. Grace period = 14 days of aggressive daily reminders before hard block
  4. Every response carries structured machine-readable + human-readable fields
  5. Users should feel like a co-pilot, not a hostage

USED BY:
  - pgl_identity_gate.py       (on every require() call)
  - pgl_onboarding.py          (on status/renew endpoints)
  - agents_router.py (cappo)   (on lifecycle/renew endpoints)
  - Any future middleware       (subscribe to the same schema)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


# ── Grace period constants ────────────────────────────────────────────────────
GRACE_PERIOD_DAYS      = 14    # 14 days after expiry before hard block
REMINDER_INTERVAL_DAYS = 1     # Daily reminders during grace period
# ─────────────────────────────────────────────────────────────────────────────


class NotificationLevel(str, Enum):
    INFO     = "INFO"      # Milestone — something good happened
    TIP      = "TIP"       # Helpful guidance
    WARNING  = "WARNING"   # Action needed soon (30 days)
    URGENT   = "URGENT"    # Action needed now (grace period days 1-7)
    CRITICAL = "CRITICAL"  # Action needed TODAY (grace period days 8-14)
    BLOCKED  = "BLOCKED"   # Hard block — cannot execute until resolved


class PGLNotification:
    """A transparent, actionable notification for any PGL lifecycle event.

    Every field is designed to answer a specific user question:
    - level:            How serious is this?
    - title:            What's happening in one sentence?
    - message:          Why? Full human-readable explanation.
    - action:           What do I do RIGHT NOW?
    - endpoint:         Which specific API endpoint?
    - days_remaining:   How long do I have?
    - can_execute:      Can my agent still run?
    - renewal_url:      Where do I go to fix it?
    - reminder_number:  Which reminder is this? (1-14 for grace period)
    """

    def __init__(
        self,
        level:          NotificationLevel,
        title:          str,
        message:        str,
        action:         str,
        endpoint:       str | None      = None,
        days_remaining: int | None      = None,
        can_execute:    bool            = True,
        renewal_url:    str | None      = None,
        reminder_number: int | None     = None,
        metadata:       dict[str, Any]  = None,
    ) -> None:
        self.level           = level
        self.title           = title
        self.message         = message
        self.action          = action
        self.endpoint        = endpoint
        self.days_remaining  = days_remaining
        self.can_execute     = can_execute
        self.renewal_url     = renewal_url
        self.reminder_number = reminder_number
        self.metadata        = metadata or {}
        self.generated_at    = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "notification": {
                "level":           self.level.value,
                "title":           self.title,
                "message":         self.message,
                "action":          self.action,
                "endpoint":        self.endpoint,
                "renewal_url":     self.renewal_url,
                "days_remaining":  self.days_remaining,
                "reminder_number": self.reminder_number,
                "can_execute":     self.can_execute,
                "generated_at":    self.generated_at,
            },
            "metadata": self.metadata,
        }


# ── Notification builders — one per lifecycle state ───────────────────────────

def notify_onboarding_complete(pgl_id: str, workspace_id: str, probation_ends: str) -> PGLNotification:
    """Fired once when a human operator completes PGL onboarding."""
    return PGLNotification(
        level=NotificationLevel.INFO,
        title="🎉 PGL Identity Issued — You're on the board.",
        message=(
            f"Your PGL identity (ID: {pgl_id}) has been issued and locked to your account. "
            f"This ID is permanent — it doesn't change, ever. "
            f"You are currently in a 90-day probationary period (ends {probation_ends[:10]}). "
            f"During probation, your identity can be reviewed without cause. "
            f"After 90 days, you earn full trust status. Your ID renews annually — "
            f"same ID, new expiry. Think of it like a driver's license."
        ),
        action="No action required. Start registering your agents.",
        endpoint="POST /api/v1/pgl/onboarding/operator-identity (idempotent)",
        can_execute=True,
        metadata={"pgl_id": pgl_id, "workspace_id": workspace_id, "probation_ends": probation_ends},
    )


def notify_already_onboarded(pgl_id: str, trust_level: str) -> PGLNotification:
    """Fired when a user tries to re-onboard but already has an ID."""
    return PGLNotification(
        level=NotificationLevel.TIP,
        title="✅ You already have a PGL identity.",
        message=(
            f"Your existing PGL ID ({pgl_id}) is active with trust level: {trust_level}. "
            f"You don't need to re-onboard. An identity is issued once and kept for life. "
            f"Check your current status or renew if due."
        ),
        action="Check your identity status at GET /api/v1/pgl/identity/status",
        endpoint="GET /api/v1/pgl/identity/status",
        can_execute=True,
        renewal_url="/api/v1/pgl/identity/renew",
        metadata={"pgl_id": pgl_id, "trust_level": trust_level},
    )


def notify_probationary(pgl_id: str, days_remaining: int, probation_ends: str) -> PGLNotification:
    """Fired during probation (days 0-90)."""
    return PGLNotification(
        level=NotificationLevel.TIP,
        title=f"🔵 Probationary — {days_remaining} days until full trust.",
        message=(
            f"Your PGL identity is active and your agents can run. "
            f"You're in the 90-day probationary period (ends {probation_ends[:10]}). "
            f"This is normal — all new identities start here. "
            f"During probation, execution can be reviewed or paused without cause. "
            f"After {days_remaining} more days, you automatically earn ACTIVE (full trust) status. "
            f"Keep your agents running clean and you'll sail through."
        ),
        action="No action required. Keep running your agents.",
        endpoint=None,
        days_remaining=days_remaining,
        can_execute=True,
        metadata={"pgl_id": pgl_id, "probation_ends": probation_ends},
    )


def notify_active(pgl_id: str, renewal_due: str, days_until_renewal: int) -> PGLNotification:
    """Fired when identity is fully ACTIVE — informational."""
    return PGLNotification(
        level=NotificationLevel.INFO,
        title="✅ Active — Full trust. Keep running.",
        message=(
            f"Your PGL identity is in good standing. Full trust status achieved. "
            f"Next renewal due: {renewal_due[:10]} ({days_until_renewal} days away). "
            f"You'll get a reminder 30 days before renewal is due."
        ),
        action="No action required.",
        endpoint=None,
        days_remaining=days_until_renewal,
        can_execute=True,
        metadata={"pgl_id": pgl_id, "renewal_due": renewal_due},
    )


def notify_renewal_due(pgl_id: str, days_remaining: int, renewal_due: str) -> PGLNotification:
    """Fired 30 days before renewal deadline (RENEWAL_DUE state)."""
    return PGLNotification(
        level=NotificationLevel.WARNING,
        title=f"⏰ Renewal Due in {days_remaining} Days — Action Needed Soon.",
        message=(
            f"Your PGL identity renewal is coming up in {days_remaining} days "
            f"(deadline: {renewal_due[:10]}). "
            f"Your agents can still run right now — this is an early warning. "
            f"Don't wait until the deadline. Renewing early keeps your agents running "
            f"without any interruption. Same ID, new expiry — takes 30 seconds."
        ),
        action=f"Renew now at POST /api/v1/pgl/identity/renew — 30 seconds, same ID.",
        endpoint="POST /api/v1/pgl/identity/renew",
        days_remaining=days_remaining,
        can_execute=True,
        renewal_url="/api/v1/pgl/identity/renew",
        metadata={"pgl_id": pgl_id, "renewal_due": renewal_due},
    )


def notify_grace_period(
    pgl_id:         str,
    grace_day:      int,    # Which day of grace period (1-14)
    days_remaining: int,    # Days until hard block
    hard_block_date: str,
) -> PGLNotification:
    """Fired during 14-day grace period. Escalates tone based on day."""
    if grace_day <= 3:
        level = NotificationLevel.WARNING
        emoji = "⚠️"
        urgency = "soon"
    elif grace_day <= 7:
        level = NotificationLevel.URGENT
        emoji = "🔴"
        urgency = "urgently"
    else:
        level = NotificationLevel.CRITICAL
        emoji = f"🚨 DAY {grace_day} OF 14"
        urgency = "RIGHT NOW"

    return PGLNotification(
        level=level,
        title=f"{emoji} GRACE PERIOD — Day {grace_day} of 14. Renew {urgency}.",
        message=(
            f"Your PGL identity renewal was due but you're still in the grace period. "
            f"Your agents are STILL RUNNING — this is your runway to renew without disruption. "
            f"You have {days_remaining} day{'s' if days_remaining != 1 else ''} left "
            f"(hard block on {hard_block_date[:10]}). "
            f"After {hard_block_date[:10]}, ALL agent execution stops until renewed. "
            f"Renewing now takes 30 seconds and costs the same as regular renewal. "
            f"Don't let life interrupt your agents — renew before the grace period ends."
        ),
        action=f"POST /api/v1/pgl/identity/renew — Do it now. Same ID, new expiry.",
        endpoint="POST /api/v1/pgl/identity/renew",
        days_remaining=days_remaining,
        can_execute=True,   # Grace period: still runs!
        renewal_url="/api/v1/pgl/identity/renew",
        reminder_number=grace_day,
        metadata={
            "pgl_id":          pgl_id,
            "grace_day":       grace_day,
            "days_remaining":  days_remaining,
            "hard_block_date": hard_block_date,
        },
    )


def notify_hard_expired(pgl_id: str, expired_since: str) -> PGLNotification:
    """Fired when grace period is over — hard block."""
    return PGLNotification(
        level=NotificationLevel.BLOCKED,
        title="🚫 BLOCKED — PGL Identity Expired. Renew to Resume.",
        message=(
            f"Your 14-day grace period has ended. Your PGL identity expired on {expired_since[:10]}. "
            f"Your agents cannot run until you renew. "
            f"IMPORTANT: Your ID number is the same — it doesn't change. "
            f"Renewal restores execution immediately. It takes 30 seconds. "
            f"No data is lost. No agents need to re-register. Just renew."
        ),
        action="POST /api/v1/pgl/identity/renew — Restores execution immediately.",
        endpoint="POST /api/v1/pgl/identity/renew",
        days_remaining=0,
        can_execute=False,
        renewal_url="/api/v1/pgl/identity/renew",
        metadata={"pgl_id": pgl_id, "expired_since": expired_since},
    )


def notify_agent_registered(
    agent_id:     str,
    cert_id:      str,
    probation_ends: str,
    renewal_due:  str,
) -> PGLNotification:
    """Fired when an agent gets its birth certificate (cappo)."""
    return PGLNotification(
        level=NotificationLevel.INFO,
        title="🤖 Agent Registered — Birth Certificate Issued.",
        message=(
            f"Agent {agent_id} has been registered with PGL. "
            f"Certificate ID: {cert_id} — this is permanent, it never changes. "
            f"Your agent is in 90-day probation (ends {probation_ends[:10]}). "
            f"Annual renewal required by {renewal_due[:10]}. "
            f"Same cert ID, new expiry at renewal — like a license plate renewal."
        ),
        action="Check agent lifecycle at GET /api/v1/agents/{agent_id}/lifecycle",
        endpoint=f"GET /api/v1/agents/{agent_id}/lifecycle",
        can_execute=True,
        renewal_url=f"/api/v1/agents/{agent_id}/renew",
        metadata={
            "agent_id": agent_id,
            "cert_id":  cert_id,
            "probation_ends": probation_ends,
            "renewal_due": renewal_due,
        },
    )


def notify_quarantined(actor_id: str, reason: str) -> PGLNotification:
    """Fired when an identity is quarantined."""
    return PGLNotification(
        level=NotificationLevel.BLOCKED,
        title="🔒 Quarantined — Execution Suspended Pending Review.",
        message=(
            f"Agent '{actor_id}' has been placed in quarantine. "
            f"Reason: {reason} "
            f"ALL execution is suspended until the quarantine is lifted by an admin. "
            f"This is NOT permanent. Contact support to initiate the review process. "
            f"Your identity and all agent data are preserved."
        ),
        action="Contact support or POST /api/v1/pgl/{actor_id}/quarantine to request review.",
        endpoint=f"POST /api/v1/pgl/{actor_id}/quarantine",
        can_execute=False,
        metadata={"actor_id": actor_id, "reason": reason},
    )


def notify_renewal_success(
    pgl_id:        str,
    renewal_count: int,
    new_expiry:    str,
) -> PGLNotification:
    """Fired immediately after a successful renewal."""
    return PGLNotification(
        level=NotificationLevel.INFO,
        title=f"✅ Renewed — Renewal #{renewal_count} Complete. Good for another year.",
        message=(
            f"Your PGL identity has been renewed. "
            f"Same ID: {pgl_id} — it never changes. "
            f"New expiry: {new_expiry[:10]}. "
            f"All agents are running normally. Next renewal reminder in ~11 months. "
            f"Total renewals: {renewal_count}."
        ),
        action="Nothing to do. Your agents are running.",
        endpoint=None,
        can_execute=True,
        metadata={
            "pgl_id":        pgl_id,
            "renewal_count": renewal_count,
            "new_expiry":    new_expiry,
        },
    )
