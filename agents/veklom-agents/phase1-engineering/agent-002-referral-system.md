# Agent-002 — REFERRAL SYSTEM ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** CRITICAL — Growth Blocking

---

## Mission

Build the complete referral system from scratch. There is currently NO referral infrastructure — no table, no link generation, no tracking, no rewards. This is the viral loop that drives organic growth to 20,000 users.

## Current State

- **No referral table** in database
- **No referral endpoints** in any router
- **No referral UI** in frontend
- **No referral tracking** or attribution

## Tasks

1. Design referral database schema:
   - `referrals` table: `id`, `referrer_user_id`, `referred_email`, `referral_code`, `status` (pending/signed_up/converted/rewarded), `created_at`, `converted_at`
   - `referral_rewards` table: `id`, `referral_id`, `reward_type` (credit/discount/feature), `reward_value`, `granted_at`
2. Create referral API router (`backend/apps/api/routers/referrals.py`):
   - `POST /referrals/generate-link` — create unique referral code for current user
   - `GET /referrals/my-referrals` — list all referrals by current user
   - `GET /referrals/stats` — referral stats (sent, signed up, converted, rewards earned)
   - `POST /referrals/track` — track referral click (public, no auth)
   - `POST /referrals/convert` — mark referral as converted (internal, on signup)
   - `POST /referrals/reward` — grant reward to referrer (internal, on conversion)
3. Mount router in `backend/apps/api/main.py`
4. Create Alembic migration for referral tables
5. Build referral UI components:
   - Referral dashboard page (list referrals, stats, share link)
   - Share modal (copy link, email, social share buttons)
   - Referral banner on signup page ("Referred by a friend? Enter code")
6. Wire referral tracking into signup flow:
   - Capture `?ref=CODE` query param on landing page
   - Store in cookie/localStorage
   - Submit with registration
7. Implement reward logic:
   - Referrer gets $10 wallet credit on referred user's first purchase
   - Referred user gets 10% off first purchase
   - Cap at 50 referrals per user per month

## Success Metrics

| Metric | Target |
|---|---|
| Referral link generation | Working |
| Referral tracking on signup | Working |
| Reward distribution | Automated |
| Referral dashboard | Live |
| Share options | Link, email, social |
| Referral conversion rate | Track baseline |

## Daily Checklist

- [ ] Day 1: Schema design + migration + API endpoints
- [ ] Day 2: Mount router + referral tracking in signup flow
- [ ] Day 3: Frontend referral dashboard + share modal
- [ ] Day 4: Reward logic + integration tests + PR

## Dependencies

- Agent-000 (MASTER_STATE.md)
- Agent-001 (wallet/credit system for rewards)
- Agent-005 (onboarding flow integration)
- Agent-051 (referral activation campaigns)

## Key Files

- `backend/apps/api/main.py` — mount new router
- `backend/apps/api/routers/` — new `referrals.py`
- `frontend/workspace/src/pages/` — new referral page
- Token wallet router for credit rewards

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Create: backend/apps/api/routers/referrals.py
Mount in: backend/apps/api/main.py
Frontend: frontend/workspace/src/pages/Referrals.tsx
```
