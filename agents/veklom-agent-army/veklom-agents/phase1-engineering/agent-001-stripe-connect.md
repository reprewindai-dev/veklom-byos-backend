# Agent-001 — STRIPE CONNECT ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** CRITICAL — Revenue Blocking
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Wire Stripe Connect end-to-end so vendors receive automatic payouts. The marketplace router at `backend/apps/api/routers/marketplace_v1.py` has vendor onboarding endpoints. Complete destination charge splitting, webhook verification, and payout flow.

## First Actions (Read Before Touching Code)

```bash
# 1. Read these files first:
cat backend/apps/api/routers/marketplace_v1.py
cat backend/apps/api/routers/billing.py
cat backend/apps/api/routers/subscriptions.py
cat .env.example  # find Stripe key names
cat backend/db/models.py  # find vendor/payment models
```

## Tasks

### Task 1: Complete Stripe Connect Onboarding
```python
# File: backend/apps/api/routers/marketplace_v1.py
# Add to existing vendor onboarding endpoint:
POST /api/v1/marketplace/vendors/connect
# → Creates Stripe Connect account, returns OAuth link
# → On redirect back: capture account_id, store on vendor record
```

### Task 2: Destination Charge Splitting
```python
# Every marketplace purchase auto-splits:
# Platform: 10% (configurable via env PLATFORM_FEE_PERCENT)
# Vendor: 90%
stripe.PaymentIntent.create(
    amount=amount_cents,
    currency="usd",
    transfer_data={"destination": vendor.stripe_account_id},
    application_fee_amount=platform_fee_cents
)
```

### Task 3: Webhook Verification
```python
# File: backend/apps/api/routers/webhooks.py (create if missing)
@router.post("/api/v1/webhooks/stripe")
async def stripe_webhook(request: Request):
    sig = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(
        await request.body(), sig, os.getenv("STRIPE_WEBHOOK_SECRET")
    )
    # Handle: payment_intent.succeeded, account.updated, payout.paid
```

### Task 4: Payout Dashboard Endpoint
```python
GET /api/v1/marketplace/vendors/{id}/payouts
# → { balance, pending, payouts: [...] }
```

### Task 5: Tests + Deploy
```bash
cd backend && pytest tests/test_payments.py -v
git add -A && git commit -m "agent-001: complete Stripe Connect flow"
git push origin feature/agent-001-stripe-connect
```

## Guardrail Rules
- CQ-08: Stripe keys in `.env` only — NEVER hardcoded
- OPS-01: Branch = `feature/agent-001-stripe-connect`
- OPS-06: Update PROGRESS.md after each task

## Success Metrics
| Metric | Target |
|---|---|
| Vendor payout flow | End-to-end working in test mode |
| Charge split accuracy | 100% correct |
| Webhook signature verification | No bypass possible |
| Test coverage on payment code | > 90% |

## Dependencies
- Agent-008 (Security) reviews webhook handler before merge
- Agent-082 (QA Payments) runs full payment flow tests
