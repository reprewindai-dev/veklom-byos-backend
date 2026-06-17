# Agent-005 — ONBOARDING ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Build a 5-minute onboarding wizard that takes new users from signup to first value. Currently, new users land on the Overview page with no guidance, no setup wizard, and no first-run experience.

## Current State

- Post-signup redirects to `/overview` — ✅
- No onboarding wizard or guided setup
- No first-run detection
- No progress indicators for account setup
- No "getting started" checklist

## Tasks

1. **First-Run Detection**:
   - Check `user.onboarding_completed` flag on login
   - Redirect to `/onboarding` if not completed
   - Allow skip with "I'll explore on my own" option
2. **Onboarding Wizard** (4 steps, < 5 minutes total):
   - **Step 1 — Welcome**: Name, role, company size, primary use case
   - **Step 2 — Connect**: Add first API key or connect first model provider
   - **Step 3 — Try It**: Run a preset playground prompt (ties to Agent-004)
   - **Step 4 — Explore**: Guided tour of key features (marketplace, pipelines, vault)
3. **Getting Started Checklist** (persistent sidebar widget):
   - [ ] Complete profile
   - [ ] Run first playground prompt
   - [ ] Create first pipeline
   - [ ] Browse marketplace
   - [ ] Invite a team member
   - [ ] Top up wallet
   - Progress bar showing completion %
4. **Backend**:
   - `PATCH /auth/me` — add `onboarding_completed`, `onboarding_step`, `use_case` fields
   - `POST /onboarding/complete` — mark onboarding done + track analytics event
   - `GET /onboarding/checklist` — return checklist status
5. **Welcome Email** (coordinate with Agent-052):
   - Trigger welcome email on signup via Resend
   - Include getting-started link and referral code

## Success Metrics

| Metric | Target |
|---|---|
| Onboarding completion rate | > 60% |
| Time to first value | < 5 minutes |
| Checklist item completion (Day 7) | > 3 items average |
| Drop-off at each step | Track baseline |

## Daily Checklist

- [ ] Day 1: First-run detection + wizard UI (steps 1-2)
- [ ] Day 2: Wizard steps 3-4 + backend endpoints
- [ ] Day 3: Getting started checklist widget
- [ ] Day 4: Welcome email trigger + integration tests + PR

## Dependencies

- Agent-003 (UX components)
- Agent-004 (playground presets for Step 3)
- Agent-052 (email automation for welcome email)

## Key Files

- `frontend/workspace/src/pages/` — new Onboarding.tsx
- `frontend/workspace/src/components/` — GettingStartedChecklist.tsx
- `backend/apps/api/routers/auth.py` — user profile updates

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Create: frontend/workspace/src/pages/Onboarding.tsx
Create: frontend/workspace/src/components/GettingStartedChecklist.tsx
```
