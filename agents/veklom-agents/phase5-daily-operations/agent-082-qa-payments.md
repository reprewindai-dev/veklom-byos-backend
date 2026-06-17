# Agent-082 — QA (Payments & Billing)

**Phase:** Cross-phase — QA
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** CRITICAL

---

## Mission

Test all payment flows: Stripe checkout, subscription activation, wallet top-up, marketplace purchases, vendor payouts, webhook handling, and refunds.

## Test Cases

1. Subscription checkout for each plan tier
2. Wallet top-up via Stripe checkout
3. Marketplace purchase → vendor payout flow
4. Webhook signature verification
5. Failed payment handling and retry
6. Refund processing
7. Invoice generation
8. Stripe Connect vendor onboarding flow

## Dependencies

- Agent-001 (Stripe Connect), Agent-050 (pricing), Agent-080 (QA lead)
