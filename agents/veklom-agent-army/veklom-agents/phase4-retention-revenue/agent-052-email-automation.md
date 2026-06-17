# Agent-052 — EMAIL AUTOMATION AGENT

**Phase:** 4 — Retention & Revenue
**Timeline:** Days 7–14
**Committee:** Revenue
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Build automated email sequences using Resend API (already configured in backend). Target: 30%+ open rates, 5%+ click rates.

## First Actions

```bash
cat backend/apps/api/routers/herald.py  # HERALD email agent — check if exists
# Or: grep -r "resend" backend/ --include="*.py" -l
cat .env.example | grep -i resend  # find RESEND_API_KEY var name
```

## Email Sequences

### Welcome Sequence (New Signup)
```python
# Email 1 (immediate): "Welcome to Veklom — Your sovereign AI is ready"
#   CTA: "Run your first AI inference →"
# Email 2 (Day 2, if no AI run): "Quick tip: Run your first query in 60 seconds"
# Email 3 (Day 5, if no subscription): "Unlock unlimited AI access — 3 plans available"
# Email 4 (Day 10, if still free): "Free tier ends Day 14 — upgrade now"
```

### Activation Sequence (Trial → Paid)
```python
# Trigger: user hasn't upgraded after 7 days
# Email 1: "What's holding you back? (survey)"
# Email 2: "Here's what Professional users are building"
# Email 3 (Day 12): "Final reminder — lock in your rate"
```

### Win-Back Sequence (Churned)
```python
# Trigger: subscription cancelled
# Email 1 (Day 1): "We're sorry to see you go — what happened?"
# Email 2 (Day 7): "We've shipped 3 new features since you left"
# Email 3 (Day 30): "Come back — 20% off for the next 30 days"
```

## API Endpoint

```python
# Create/verify: backend/apps/api/routers/email_automation.py
POST /api/v1/internal/emails/trigger
# body: { sequence: "welcome", user_id: "...", variables: {...} }

GET /api/v1/internal/emails/sequences
# → list all sequences + stats
```

## Success Metrics
| Metric | Target |
|---|---|
| Open rate | > 30% |
| Click rate | > 5% |
| Trial → paid conversion from email | > 10% |
