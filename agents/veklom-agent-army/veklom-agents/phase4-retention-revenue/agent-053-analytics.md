# Agent-053 — ANALYTICS AGENT

**Phase:** 4 — Retention & Revenue
**Timeline:** Days 7–14
**Committee:** Revenue
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Implement product analytics to track user behavior, conversion funnels, and business metrics. The `/api/v1/telemetry` endpoint already exists — build on top of it.

## First Actions

```bash
cat backend/apps/api/routers/telemetry.py   # see what's tracked
cat backend/apps/api/routers/insights.py    # existing analytics endpoints
curl -s https://veklom.com/api/v1/insights/summary \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## KPI Dashboard Backend

```python
GET /api/v1/admin/kpis
# Returns real business metrics:
{
    "mrr": 0.00,               # Monthly Recurring Revenue
    "arr": 0.00,               # Annual Run Rate
    "total_users": 0,
    "paying_users": 0,
    "trial_users": 0,
    "conversion_rate": 0.0,    # trial → paid
    "churn_rate": 0.0,         # monthly
    "arpu": 0.0,               # average revenue per user
    "ai_runs_today": 0,
    "tokens_used_today": 0,
    "top_models": [],
    "new_signups_7d": 0,
    "revenue_7d": 0.00
}
```

## Funnel Tracking

```python
# Track these conversion funnel events via /api/v1/telemetry:
FUNNEL_EVENTS = [
    "page_view",          # anonymous visitor
    "signup_started",     # opened registration
    "signup_completed",   # created account
    "onboarding_started",
    "first_ai_run",       # activation
    "upgrade_viewed",     # saw pricing
    "upgrade_started",    # clicked upgrade
    "upgrade_completed",  # paid
]
```

## Tasks

1. Build `/api/v1/admin/kpis` endpoint with real DB queries
2. Add funnel event tracking to auth + onboarding flows
3. Build daily metrics cron job (store in `metrics_daily` table)
4. Create `/api/v1/admin/funnel` endpoint showing conversion rates
5. Wire PROGRESS.md daily KPI snapshot

## Success Metrics
| Metric | Target |
|---|---|
| KPI endpoint accuracy | Real data, no mocks |
| Funnel tracking coverage | All 8 events instrumented |
| Daily metrics job | Runs at 00:00 UTC |
