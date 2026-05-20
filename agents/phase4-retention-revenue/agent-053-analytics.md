# Agent-053 — ANALYTICS AGENT

**Phase:** 4 — Retention & Revenue
**Timeline:** Days 7–14
**Committee:** Revenue
**Priority:** HIGH

---

## Mission

Implement product analytics to track user behavior, conversion funnels, and business metrics. Set up PostHog (or equivalent), build dashboards, and establish KPI tracking. Enable data-driven decision making for all agents.

## Current State

- Sentry DSN configured for error tracking — ✅
- Prometheus metrics endpoint exists — ✅
- **GAP:** No product analytics (PostHog, Mixpanel, Amplitude)
- **GAP:** No conversion funnel tracking
- **GAP:** No user behavior analytics
- **GAP:** No business dashboard

## Tasks

1. **PostHog Setup**:
   - Install PostHog (self-hosted for sovereignty, or cloud)
   - Add frontend tracking snippet
   - Configure backend event tracking
   - Set up privacy-compliant data collection
2. **Event Tracking**:
   - Page views (all routes)
   - User actions: signup, login, pipeline_created, deployment_created, marketplace_purchase, wallet_topup, referral_sent
   - Feature usage: playground_run, listing_viewed, api_key_created
   - Errors: payment_failed, auth_error, api_error
3. **Conversion Funnels**:
   - Signup funnel: landing → signup → onboarding → first value
   - Purchase funnel: browse → listing view → checkout → payment → confirmation
   - Upgrade funnel: free user → pricing page → checkout → paid
   - Referral funnel: share → click → signup → convert
4. **Business Dashboard**:
   - Real-time KPIs: registered users, DAU, MRR, vendor count
   - Cohort retention charts
   - Revenue by plan tier
   - Top vendors by sales
   - Geographic distribution
5. **Reporting**:
   - Daily automated KPI email to stakeholders
   - Weekly growth report
   - Monthly business review data pack

## Success Metrics

| Metric | Target |
|---|---|
| Analytics tracking live | Yes |
| Events tracked | 15+ types |
| Funnels configured | 4 |
| Dashboard live | Yes |
| Data-driven decisions enabled | All agents have access |

## Daily Checklist

- [ ] Check analytics data quality (no missing events)
- [ ] Review conversion funnels for drop-off points
- [ ] Update business dashboard
- [ ] Share daily KPI snapshot with team
- [ ] Report analytics findings to PROGRESS.md

## Dependencies

- Agent-003 (frontend event tracking integration)
- Agent-050 (pricing funnel tracking)
- Agent-052 (email analytics integration)
