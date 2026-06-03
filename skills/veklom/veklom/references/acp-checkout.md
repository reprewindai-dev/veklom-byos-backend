# Buying via Agentic Commerce Protocol (ACP) checkout

Use this to buy marketplace packs, start a subscription, or top up reserve
credit. Backed by Stripe. Requires auth: a Veklom API key (`X-API-Key: byos_...`)
or a Bearer JWT.

## 1. Find the product

```bash
curl -s https://veklom.com/api/v1/agentic_commerce/product_feed
```

Each product has an `id` and a `product_type`:

- `marketplace` — id is the listing id (e.g. `ls_clinical_rag`)
- `subscription` — id like `plan_growth`, `plan_sovereign`
- `wallet_credit` — id like `credit_100` (or pass any dollar amount)
- `governed_service` — id like `svc_gpc_run` (prefer x402 for these; buying here
  prepays reserve credit)

## 2. Create a checkout session

```bash
curl -s -X POST https://veklom.com/api/v1/agentic_commerce/checkout_sessions \
  -H "X-API-Key: byos_YOURKEY" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "usd",
    "line_item_details": [
      { "product_type": "subscription", "item_id": "plan_growth", "quantity": 1 }
    ],
    "buyer": { "email": "agent-owner@example.com" }
  }'
```

Response is an ACP `checkout_session` with `status: ready_for_payment`,
`line_items`, and `totals`. Note the session `id` (`acs_...`).

## 3. Complete (pay + fulfill)

```bash
curl -s -X POST \
  https://veklom.com/api/v1/agentic_commerce/checkout_sessions/acs_XXX/complete \
  -H "X-API-Key: byos_YOURKEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: <stable-uuid>" \
  -d '{ "payment_data": { "provider": "stripe", "token": "<shared_payment_token>" } }'
```

- `payment_data.token` is a Stripe delegated/shared payment token from your
  payment provider. Free items (total = 0) complete with no token.
- On success the response has `status: completed`, an `order`, and a
  `fulfillment` array describing what happened:
  - marketplace → asset installed in the workspace
  - subscription → plan activated
  - wallet_credit / governed_service → reserve credited (funds x402 usage)

## Other operations

```bash
# Retrieve a session
curl -s https://veklom.com/api/v1/agentic_commerce/checkout_sessions/acs_XXX \
  -H "X-API-Key: byos_YOURKEY"

# Update buyer info
curl -s -X POST https://veklom.com/api/v1/agentic_commerce/checkout_sessions/acs_XXX \
  -H "X-API-Key: byos_YOURKEY" -H "Content-Type: application/json" \
  -d '{ "buyer": { "email": "new@example.com" } }'

# Cancel
curl -s -X POST https://veklom.com/api/v1/agentic_commerce/checkout_sessions/acs_XXX/cancel \
  -H "X-API-Key: byos_YOURKEY"
```

## Notes

- Completion is idempotent — completing an already-completed session returns the
  same order.
- A Veklom API key is created in the workspace UI (Settings → API keys) and
  always starts with `byos_`. Fund/scope it to only what the agent needs.
