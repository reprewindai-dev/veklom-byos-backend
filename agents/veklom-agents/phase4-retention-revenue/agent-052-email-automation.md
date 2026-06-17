# Agent-052 — EMAIL AUTOMATION AGENT

**Phase:** 4 — Retention & Revenue
**Timeline:** Days 7–14
**Committee:** Revenue
**Priority:** HIGH

---

## Mission

Build automated email sequences using Resend API (already configured). Create welcome, activation, upgrade nudge, and win-back sequences. Target: 30%+ email open rates, 5%+ click rates.

## Current State

- Resend API key configured in `.env` — ✅
- No email sequences built
- No email templates
- No automated triggers

## Tasks

1. **Welcome Sequence** (triggered on signup):
   - Email 1 (immediate): Welcome + getting started guide
   - Email 2 (Day 1): "Complete your profile in 2 minutes"
   - Email 3 (Day 3): "Explore the marketplace — 3 tools to try"
   - Email 4 (Day 7): "Ready to build? Create your first pipeline"
2. **Activation Sequence** (triggered when user hasn't completed onboarding):
   - Email 1 (Day 2): "You're almost there — finish setup in 2 minutes"
   - Email 2 (Day 5): "Here's what you're missing" (feature showcase)
   - Email 3 (Day 10): "Last chance — exclusive offer for early adopters"
3. **Upgrade Nudge Sequence** (triggered for free users with usage):
   - Email 1 (Day 14): "You've used 80% of your free tier"
   - Email 2 (Day 21): "Unlock Pro features — special founding member price"
   - Email 3 (Day 30): "Limited time: 20% off your first year"
4. **Win-Back Sequence** (triggered on inactivity > 14 days):
   - Email 1 (Day 14): "We miss you — here's what's new"
   - Email 2 (Day 21): "Your pipelines are waiting"
   - Email 3 (Day 30): "Exclusive comeback offer"
5. **Transactional Emails**:
   - Password reset
   - Invoice/receipt
   - Payout notification (for vendors)
   - Referral reward notification

## Implementation

```python
# Using Resend Python SDK
import resend
resend.api_key = os.environ["RESEND_API_KEY"]

# Trigger-based: celery tasks or cron jobs
# Templates: HTML email templates in backend/templates/email/
# Tracking: UTM params + Resend analytics
```

## Success Metrics

| Metric | Target |
|---|---|
| Email sequences live | 4 |
| Open rate | > 30% |
| Click rate | > 5% |
| Unsubscribe rate | < 1% |
| Email-driven upgrades | 20+ |

## Daily Checklist

- [ ] Monitor email delivery rates and bounces
- [ ] Check open/click rates per sequence
- [ ] A/B test subject lines
- [ ] Review unsubscribe reasons
- [ ] Report email metrics to PROGRESS.md

## Dependencies

- Agent-005 (onboarding triggers for welcome sequence)
- Agent-050 (pricing for upgrade nudge links)
- Agent-051 (referral emails)

## Key Files

- `.env` — `RESEND_API_KEY` configured
- Backend: new `backend/apps/api/routers/emails.py` or celery tasks
- Templates: `backend/templates/email/`
