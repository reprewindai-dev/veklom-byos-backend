# Agent-050 — PRICING AGENT

**Phase:** 4 — Retention & Revenue
**Timeline:** Days 7–14
**Committee:** Revenue
**Priority:** CRITICAL
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Build and optimize the pricing page and wire Stripe subscription tiers. Currently only a static `landing/pricing.html`. Must wire dynamic pricing to Stripe, implement 3-tier model, optimize for conversion.

## First Actions

```bash
cat backend/apps/api/routers/subscriptions.py
cat backend/apps/api/routers/billing.py
curl -s https://veklom.com/api/v1/subscriptions/plans | jq .
# Check: are Stripe price IDs configured in .env?
```

## Pricing Tiers (DO NOT MODIFY WITHOUT APPROVAL)

```python
PLANS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 49,
        "price_annual": 39,  # per month
        "stripe_price_id_monthly": "price_starter_monthly",
        "stripe_price_id_annual": "price_starter_annual",
        "features": [
            "100K tokens/month",
            "3 AI models",
            "Basic audit logs",
            "Email support"
        ],
        "limits": {"tokens_monthly": 100000, "models": 3, "users": 1}
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 149,
        "price_annual": 119,
        "features": [
            "1M tokens/month",
            "All AI models",
            "Full audit logs + compliance",
            "Private runtime (Ollama/vLLM)",
            "Priority support"
        ],
        "limits": {"tokens_monthly": 1000000, "models": -1, "users": 5}
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 499,
        "price_annual": 399,
        "features": [
            "Unlimited tokens",
            "Custom model routing",
            "SOC2/HIPAA compliance",
            "Dedicated infrastructure",
            "SLA + dedicated support"
        ],
        "limits": {"tokens_monthly": -1, "models": -1, "users": -1}
    }
}
```

## Tasks

1. Ensure `/api/v1/subscriptions/plans` returns PLANS above
2. Wire Stripe checkout: `POST /api/v1/subscriptions/checkout` → real Stripe price IDs
3. Handle subscription webhooks: `customer.subscription.updated`, `invoice.payment_failed`
4. Enforce plan limits in AI execution middleware
5. Build upgrade prompt: trigger when user hits 80% of token limit

## Success Metrics
| Metric | Target |
|---|---|
| Pricing page conversion | > 3% |
| Stripe checkout completion | > 70% |
| Failed payment recovery | > 50% (dunning) |
