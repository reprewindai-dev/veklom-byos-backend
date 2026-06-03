# Veklom catalog overview

The live, authoritative catalog is always:
`GET https://veklom.com/api/v1/agentic_commerce/product_feed`

It returns four product types. Prices below are indicative; trust the feed.

## 1. governed_service (pay-per-call, x402 USDC on Base)

Run governed AI directly. Pay per call with x402 (see `x402-payments.md`) or
prepay a reserve credit. Examples: AI Inference ($0.008), AI Chat ($0.005),
GPC Compile ($0.015), GPC Intent-to-Plan ($0.010), GPC Run ($0.020), Pipeline
Trigger ($0.025), Runtime Job ($0.020), Evidence Export ($0.005), Compliance
Report ($0.010), Marketplace Acquire ($0.050), Audit Verify ($0.003).

## 2. marketplace (one-time / pack, Stripe)

Sovereign packs, compliance packs, connectors, prompts, models. Buy via ACP
checkout; the asset is installed into the buyer's workspace on completion.

## 3. subscription (recurring, Stripe)

- `plan_growth` — Veklom Growth, $299/mo (5 deployments, routing controls, 30d audit)
- `plan_sovereign` — Veklom Sovereign, $799/mo (unlimited deployments, HIPAA/SOC2 packs, 1yr audit)

(Community is free and Enterprise is custom — not directly checkout-able.)

## 4. wallet_credit (prepaid reserve, Stripe)

Packs of `$50 / $100 / $250 / $500` (or any amount via `credit_<amount>`).
Credits the workspace operating reserve, which funds governed (x402) usage.

## Discovery URLs

- Agent manifest: `https://veklom.com/.well-known/agent.json`
- x402 config: `https://veklom.com/.well-known/x402.json`
- Machine pricing: `https://veklom.com/api/v1/pricing`
- Product feed (JSON): `https://veklom.com/api/v1/agentic_commerce/product_feed`
- Catalog feed (CSV, Stripe ACS import): `https://veklom.com/api/v1/agentic_commerce/feed.csv`
