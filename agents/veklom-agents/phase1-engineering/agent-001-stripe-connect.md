# Agent-001 — STRIPE CONNECT ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** CRITICAL — Revenue Blocking

---

## Mission

Wire Stripe Connect end-to-end so vendors receive automatic payouts. The marketplace router (`backend/apps/api/routers/marketplace_v1.py`) already has vendor onboarding and payment endpoints. Complete the destination charge splitting with platform fee.

## Current State

- `POST /marketplace/vendors/onboard` creates Stripe Express accounts — ✅ exists
- `POST /marketplace/payments/create-checkout` creates Stripe checkout — ✅ exists
- `POST /marketplace/payments/create-intent` creates PaymentIntent — ✅ exists
- `POST /marketplace/payouts/create` — ✅ endpoint exists
- **GAP:** Destination charge splitting (platform fee %) not wired in payment flow
- **GAP:** Vendor dashboard showing payout history not connected
- **GAP:** Webhook handler for `account.updated`, `payout.paid`, `payout.failed` incomplete

## Tasks

1. Read `backend/apps/api/routers/marketplace_v1.py` (891 lines) — understand current payment flow
2. Read `backend/apps/api/routers/subscriptions.py` — understand Stripe activation model
3. Implement destination charges on `create-checkout` and `create-intent`:
   - `transfer_data={"destination": vendor_stripe_account_id}`
   - `application_fee_amount` = platform fee (configurable %)
4. Add webhook handlers for Connect events:
   - `account.updated` → update vendor verification status
   - `payout.paid` → record successful payout
   - `payout.failed` → alert and retry logic
5. Add vendor payout dashboard endpoint:
   - `GET /marketplace/payouts/by-vendor/{vendor_id}` with date range filters
6. Add platform fee configuration:
   - `GET /admin/platform-fee` — current fee %
   - `PATCH /admin/platform-fee` — update fee %
7. Test with Stripe test mode before switching to live
8. Write integration tests for the full payment → payout flow

## Success Metrics

| Metric | Target |
|---|---|
| Destination charges working | Yes |
| Platform fee configurable | Yes |
| Vendor payout webhook handlers | 3 events |
| Payout dashboard endpoint | Yes |
| Integration tests passing | 100% |
| Time to vendor first payout | < 7 days after sale |

## Daily Checklist

- [ ] Day 1: Read existing payment code, map Stripe API calls
- [ ] Day 2: Implement destination charges + platform fee
- [ ] Day 3: Implement webhook handlers + payout dashboard
- [ ] Day 4: Integration tests + code review + PR

## Dependencies

- Agent-000 (MASTER_STATE.md for current state)
- Agent-008 (security review of payment flow)
- Stripe API keys (already in `.env` — LIVE mode)

## Key Files

- `backend/apps/api/routers/marketplace_v1.py` — main marketplace router
- `backend/apps/api/routers/subscriptions.py` — Stripe subscription model
- `backend/.env.example` — Stripe config vars

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Focus: backend/apps/api/routers/marketplace_v1.py
Test: pytest backend/tests/test_marketplace_payments.py
```
