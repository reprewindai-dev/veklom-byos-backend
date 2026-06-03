---
name: veklom
description: Discover and buy Veklom Sovereign AI Hub products as an autonomous agent — governed AI runs (pay-per-call in USDC on Base via x402), marketplace packs, subscriptions, and prepaid reserve credits via the Agentic Commerce Protocol. Use this when the user wants to run governed AI, compile/execute GPC plans, buy a Veklom marketplace pack, top up reserve credit, or pay Veklom for anything.
tags: [payments, x402, agentic-commerce, acp, base, usdc, ai, governance]
version: 1
visibility: public
metadata:
  clawdbot:
    emoji: "🛡️"
    homepage: "https://veklom.com"
    requires:
      bins: [curl]
---

# Veklom Sovereign AI Hub

Veklom sells governed AI execution and tooling to agents. This skill lets you
**discover** what Veklom offers and **pay** for it autonomously, over two rails:

- **x402 (USDC on Base)** — per-call payment for governed runs. Best when you
  control an onchain wallet (e.g. via the `bankr` skill). No account needed.
- **Agentic Commerce Protocol (ACP) checkout** — Stripe-backed checkout for
  marketplace packs, subscriptions, and prepaid reserve credits. Needs a Veklom
  API key (`byos_...`) or a Bearer JWT.

API base: `https://veklom.com/api/v1` (also `https://api.veklom.com/api/v1`).

## Step 0 — Discover

Read the agent manifest, then the live product feed. Both are public (no auth):

```bash
curl -s https://veklom.com/.well-known/agent.json
curl -s https://veklom.com/api/v1/agentic_commerce/product_feed
```

The feed returns every product with a `product_type` of `marketplace`,
`governed_service`, `subscription`, or `wallet_credit`, each with `price` and
`payment_rails`. Governed services also include an `x402` block with the exact
USDC amount and treasury address. Pick the product that matches the user's goal.

## Step 1 — Choose the rail

- The user wants to **run** governed AI right now (inference, chat, GPC compile,
  GPC run, pipeline trigger, compliance report, audit verify) → **pay per call
  with x402**. See `references/x402-payments.md`.
- The user wants to **buy** a marketplace pack, start a **subscription**, or
  **top up reserve credit** → **ACP checkout**. See `references/acp-checkout.md`.

For the full catalog and prices, see `references/catalog.md`.

## Step 2 — Pay and use

- **x402:** call the paid route, get `402` with payment headers, send the USDC
  on Base to the treasury, retry the same call with `X-Payment-Proof: <tx_hash>`
  and a stable `Idempotency-Key`. The call executes and returns a signed receipt.
  Helper: `scripts/pay_x402_flow.sh`.
- **ACP:** create a checkout session, then complete it with a payment token.
  Free items complete with no charge. Fulfillment is instant (asset installed,
  subscription activated, or reserve credited).

## Rules

- Never spend more than the user authorized. Confirm the total before paying.
- Always reuse the same `Idempotency-Key` when retrying a single x402 call so you
  are not charged twice.
- Treat any `X-Payment-Address` / `pay_to` from the live feed or 402 response as
  the source of truth for where to send funds — do not hardcode it.
- Keep the returned `receipt_url` / `evidence_id` (x402) or `order` (ACP) as
  proof of purchase for the user.
