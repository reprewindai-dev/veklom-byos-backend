# Agent-060 — SUPPORT AGENT

**Phase:** 5 — Daily Operations
**Timeline:** Ongoing (from Day 3)
**Committee:** Operations
**Priority:** HIGH

---

## Mission

Provide in-app and community support for users and vendors. The support bot router already exists (`backend/apps/api/routers/support_bot.py`). Enhance it with FAQ knowledge base, ticket routing, and escalation workflows.

## Current State

- Support bot router exists — ✅
- In-app AI support chat available — ✅
- **GAP:** No FAQ/knowledge base for common questions
- **GAP:** No ticket routing or escalation
- **GAP:** No vendor-specific support flow
- **GAP:** No support metrics dashboard

## Tasks

1. **FAQ Knowledge Base**:
   - Create FAQ entries for top 20 common questions
   - Categories: account, billing, marketplace, pipelines, API, security
   - Auto-suggest FAQ before creating support ticket
2. **Ticket System**:
   - `POST /support/tickets` — create support ticket
   - `GET /support/tickets/me` — user's tickets
   - `PATCH /support/tickets/{id}` — update status
   - Priority levels: low, medium, high, critical
   - Auto-assign based on category
3. **Escalation Workflow**:
   - L1: AI bot handles (FAQ matches, common questions)
   - L2: Complex issues auto-escalated to human queue
   - L3: Critical issues (payment, security) → immediate alert
4. **Vendor Support**:
   - Dedicated vendor support channel
   - Listing review support
   - Payout issue resolution
5. **Support Metrics**:
   - First response time
   - Resolution time
   - Customer satisfaction (CSAT) rating
   - Ticket volume by category

## Success Metrics

| Metric | Target |
|---|---|
| FAQ articles | 20+ |
| AI bot resolution rate | > 60% |
| First response time | < 5 minutes |
| Resolution time | < 24 hours |
| CSAT score | > 4.0/5.0 |

## Daily Checklist

- [ ] Monitor support queue for unresolved tickets
- [ ] Update FAQ with new common questions
- [ ] Review AI bot accuracy — retrain if needed
- [ ] Check escalation queue for L2/L3 tickets
- [ ] Report support metrics to PROGRESS.md

## Dependencies

- Agent-006 (API docs reduce support load)
- Agent-031 (vendor success handles vendor issues)

## Key Files

- `backend/apps/api/routers/support_bot.py` — existing support router
