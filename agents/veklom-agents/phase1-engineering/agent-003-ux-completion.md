# Agent-003 — UX COMPLETION ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Close all frontend UX gaps: fix the overview endpoint, add empty states, loading skeletons, toast notifications, and ensure mobile responsiveness at 375px breakpoint.

## Current State

- `GET /monitoring/overview` returns 404 — frontend handles gracefully but shows error banner
- List views show raw "no items" instead of warm empty states with CTAs
- No loading skeletons on data-loading views
- No success/error toast notifications on write operations
- Mobile responsiveness untested at 375px

## Tasks

1. **Fix Overview Endpoint** — implement `GET /monitoring/overview` returning `OverviewPayload`:
   - KPI cards (total users, active pipelines, monthly spend, uptime)
   - Routing utilization chart data
   - Spend rollup (7-day)
   - Recent runs (last 10)
   - Policy events (last 5)
2. **Empty States** — add warm empty states with CTAs to all list views:
   - Pipelines: "Create your first pipeline" + CTA button
   - Deployments: "Deploy your first model" + CTA button
   - Marketplace: "Browse the marketplace" + CTA button
   - Monitoring: "No events yet — your system is healthy"
   - Team: "Invite your first team member" + CTA button
3. **Loading Skeletons** — add shimmer/skeleton UI to:
   - Overview page (KPI cards, charts)
   - Pipeline list
   - Deployment list
   - Marketplace catalog
   - Billing/wallet balance
4. **Toast Notifications** — add success/error toasts on all write operations:
   - Pipeline create/update/delete
   - Deployment create/promote/rollback
   - API key create/revoke
   - Settings save
   - Wallet top-up
5. **Mobile Responsiveness** — test and fix all pages at 375px:
   - Sidebar collapse to hamburger menu
   - Cards stack vertically
   - Tables become scrollable or card-based
   - Modals fit viewport

## Success Metrics

| Metric | Target |
|---|---|
| Overview endpoint working | Yes |
| Empty states on all list views | 5+ views |
| Loading skeletons | All data-loading views |
| Toast notifications | All write operations |
| Mobile-responsive pages | All 13 routes |

## Daily Checklist

- [ ] Day 1: Fix overview endpoint + empty states
- [ ] Day 2: Loading skeletons on all views
- [ ] Day 3: Toast notification system + wire to all writes
- [ ] Day 4: Mobile responsiveness pass + PR

## Dependencies

- Agent-000 (MASTER_STATE.md for gap inventory)
- Agent-005 (onboarding flow coordinates with empty states)

## Key Files

- `frontend/workspace/src/pages/` — all page components
- `backend/apps/api/routers/monitoring.py` — overview endpoint
- `frontend/workspace/src/components/` — shared UI components

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Focus: frontend/workspace/src/pages/ + backend monitoring router
Test: npm run dev (frontend) + visual inspection at 375px
```
