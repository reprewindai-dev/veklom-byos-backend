# Agent-005 — ONBOARDING ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Build a 5-minute onboarding wizard. New users land on the Overview page with zero guidance. Fix that.

## First Actions

```bash
cat backend/apps/api/routers/auth.py      # registration flow
cat backend/apps/api/routers/workspace.py  # workspace setup
curl -s https://veklom.com/api/v1/auth/me -H "Authorization: Bearer $TOKEN" | jq .
# Check: does user object have onboarding_completed field?
```

## Tasks

### Task 1: Onboarding State Tracking
```python
# Add to users table migration:
# onboarding_step VARCHAR(50) DEFAULT 'not_started'
# onboarding_completed_at TIMESTAMPTZ

# Onboarding steps:
STEPS = [
    "welcome",           # Step 1: Welcome + value prop
    "workspace_setup",   # Step 2: Name workspace, set timezone
    "first_api_key",     # Step 3: Create first API key
    "connect_model",     # Step 4: Configure first AI model
    "first_run",         # Step 5: Run first AI inference via playground
]
```

### Task 2: Onboarding API
```python
GET  /api/v1/onboarding/status
# → { current_step, completed_steps, percent_complete }

POST /api/v1/onboarding/complete-step
# body: { step: "workspace_setup", data: {...} }
# → { next_step, remaining_steps }

POST /api/v1/onboarding/skip
# → marks onboarding skipped, sets completed flag
```

### Task 3: First-Run Triggers
```python
# On new user registration (hook into auth.py):
# 1. Create default workspace
# 2. Generate first API key automatically
# 3. Set onboarding_step = "welcome"
# 4. Send welcome email via Resend (see HERALD agent config)
```

### Task 4: Onboarding Completion Rewards
```python
# When all 5 steps complete:
# 1. Grant $5 free credits to wallet
# 2. Badge: "Pioneer" on user profile
# 3. Unlock playground presets
```

## Success Metrics
| Metric | Target |
|---|---|
| Time to first API call | < 5 minutes |
| Onboarding completion rate | > 60% |
| Step skip rate | < 30% per step |
