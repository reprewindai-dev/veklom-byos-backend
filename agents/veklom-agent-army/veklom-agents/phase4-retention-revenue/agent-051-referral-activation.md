# Agent-051 — REFERRAL ACTIVATION AGENT

**Phase:** 4 — Retention & Revenue
**Timeline:** Days 7–14
**Committee:** Revenue
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Activate the referral system built by Agent-002. Drive referral usage through in-app prompts, email campaigns, and milestone rewards. Target: 200+ referral signups by Day 14.

## First Actions

```bash
# Verify Agent-002's work is merged:
curl -s https://veklom.com/api/v1/referrals/my-link \
  -H "Authorization: Bearer $TOKEN"
# If 404 → Agent-002 hasn't merged yet — block and report to Agent-000
```

## Tasks

### Task 1: In-App Referral Prompts
```python
# Add referral nudge to API response headers on key actions:
# After first successful AI run → X-Referral-Nudge: "true"
# After subscription upgrade → X-Referral-Nudge: "true"
# After 7-day milestone → X-Referral-Nudge: "true"
```

### Task 2: Referral Email Sequence (via Resend)
```python
# Trigger via POST /api/v1/internal/emails/send (check if exists)
# Email 1 (Day 1 after signup): "Earn $10 — invite a colleague"
# Email 2 (Day 7 if no referrals): "Your referral link is waiting"
# Email 3 (On conversion): "Your referral earned you $10 credits!"
```

### Task 3: Milestone Rewards
```python
# 1 referral converted  → Bonus: extra 10K tokens
# 5 referrals converted → Badge: "Connector" + $25 credits
# 10 referrals          → Badge: "Evangelist" + 1 month free Professional
```

### Task 4: Referral Leaderboard
```python
GET /api/v1/referrals/leaderboard
# → Top 10 referrers this month (public usernames only)
```

## Success Metrics
| Metric | Target |
|---|---|
| Referral link activation rate | > 40% of users |
| Referral conversion rate | > 20% of clicks |
| Referral-driven signups | 200+ by Day 14 |
