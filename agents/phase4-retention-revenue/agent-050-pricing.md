# Agent-050 — PRICING AGENT

**Phase:** 4 — Retention & Revenue
**Timeline:** Days 7–14
**Committee:** Revenue
**Priority:** CRITICAL

---

## Mission

Build and optimize the pricing page and Stripe subscription tiers. Currently only a static `landing/pricing.html` exists. Wire dynamic pricing to Stripe subscriptions, implement the 3-tier model, and optimize for conversion.

## Current State

- Subscription router exists with plan tiers (free, starter, pro, sovereign, enterprise) — ✅
- `POST /subscriptions/checkout` creates Stripe checkout — ✅
- Operating Reserve model (1000 units = $1 USD) — ✅
- **GAP:** No dynamic pricing page wired to subscription checkout
- **GAP:** No plan comparison table
- **GAP:** No annual vs monthly toggle
- **GAP:** No upgrade/downgrade flow

## Tasks

1. **Dynamic Pricing Page**:
   - 3-column plan comparison (Starter $395, Pro $795, Sovereign $2500)
   - Feature comparison table per tier
   - Annual vs monthly toggle (15% annual discount)
   - "Most Popular" badge on Pro plan
   - Enterprise "Contact Us" CTA
   - FAQ section addressing common pricing questions
2. **Stripe Integration**:
   - Wire each plan card "Get Started" to `POST /subscriptions/checkout`
   - Handle checkout success/cancel redirects
   - Display current plan badge for logged-in users
   - Implement upgrade/downgrade flow
3. **Pricing Optimization**:
   - Add social proof (customer count, logos)
   - Add money-back guarantee badge
   - Add "Founding Member" pricing for early adopters
   - A/B test pricing page layout
4. **Billing Portal**:
   - Wire `POST /subscriptions/billing-portal` for plan management
   - Show invoice history
   - Handle cancellation flow with exit survey

## Success Metrics

| Metric | Target |
|---|---|
| Pricing page live | Yes |
| Checkout conversion rate | > 3% |
| Plan distribution | Track baseline |
| Upgrade rate (free → paid) | > 5% |
| MRR (Day 14) | $7,500 |

## Daily Checklist

- [ ] Day 7: Build dynamic pricing page with plan comparison
- [ ] Day 8: Wire Stripe checkout for all plans
- [ ] Day 9: Upgrade/downgrade flow + billing portal
- [ ] Day 10-14: A/B test and optimize conversion

## Dependencies

- Agent-001 (Stripe Connect for vendor payments)
- Agent-003 (UX components)
- Agent-005 (onboarding → pricing upsell)
- Agent-052 (email nudges for upgrade)

## Key Files

- `backend/apps/api/routers/subscriptions.py` — subscription router
- `frontend/workspace/src/pages/` — pricing page
- `landing/pricing.html` — static pricing (replace with dynamic)

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Focus: subscriptions.py + new Pricing.tsx page
Stripe plans: starter ($395), pro ($795), sovereign ($2500)
```
