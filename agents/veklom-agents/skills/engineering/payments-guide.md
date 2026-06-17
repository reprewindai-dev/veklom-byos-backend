# Payments Engineering Guide

## Stripe Keys (in .env)
- STRIPE_SECRET_KEY → server-side Stripe operations
- STRIPE_PUBLISHABLE_KEY → frontend
- STRIPE_WEBHOOK_SECRET → webhook signature verification
- PLATFORM_FEE_PERCENT → default 10

## Stripe Connect (Vendor Payouts)
```python
# Destination charge — auto-splits platform fee
stripe.PaymentIntent.create(
    amount=amount_cents,
    currency="usd",
    transfer_data={"destination": vendor.stripe_account_id},
    application_fee_amount=int(amount_cents * 0.10)
)
```

## Webhook Verification (MANDATORY)
```python
@router.post("/api/v1/webhooks/stripe")
async def stripe_webhook(request: Request):
    sig = request.headers.get("stripe-signature")
    payload = await request.body()
    event = stripe.Webhook.construct_event(
        payload, sig, os.getenv("STRIPE_WEBHOOK_SECRET")
    )
    # No signature = raise ValueError → 400
```

## Key Events to Handle
- payment_intent.succeeded → activate subscription/credits
- customer.subscription.updated → sync plan limits
- invoice.payment_failed → trigger dunning email
- account.updated → sync vendor Connect status
- payout.paid → log vendor payout in ledger

## Test Cards
- Success: 4242 4242 4242 4242
- Decline: 4000 0000 0000 0002
- 3DS required: 4000 0025 0000 3155
