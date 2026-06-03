# Paying Veklom governed runs with x402 (USDC on Base)

Use this for pay-per-call governed AI. No Veklom account is required — you only
need a wallet that can send USDC on Base (e.g. via the `bankr` skill).

## The flow

1. **Call the paid route normally.** Example — execute a GPC plan:

   ```bash
   curl -s -X POST https://veklom.com/api/v1/gpc/runs \
     -H "Content-Type: application/json" \
     -d '{"plan_id":"..."}'
   ```

2. **Receive HTTP 402** with payment instructions. Headers:

   - `X-Payment-Price-USDC` — amount to pay (e.g. `0.020`)
   - `X-Payment-Network` — `base`
   - `X-Payment-Asset` — USDC contract `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
   - `X-Payment-Address` — treasury address to pay (**read this live, do not hardcode**)
   - `X-Payment-Scheme` — `x402`

   Body also includes `price`, `payment.config_url`, and
   `retry.idempotency_key_required: true`.

   Full config any time: `curl -s https://veklom.com/.well-known/x402.json`

3. **Send USDC on Base** to `X-Payment-Address` for at least `X-Payment-Price-USDC`.
   With the `bankr` skill this is a USDC transfer on Base. Capture the
   transaction hash (`0x...`, 66 chars).

4. **Retry the exact same request** with the proof and a stable idempotency key:

   ```bash
   curl -s -X POST https://veklom.com/api/v1/gpc/runs \
     -H "Content-Type: application/json" \
     -H "X-Payment-Proof: 0x<tx_hash>" \
     -H "Idempotency-Key: <stable-uuid-for-this-call>" \
     -d '{"plan_id":"..."}'
   ```

   Veklom verifies the transaction on Base (correct USDC amount, correct
   destination, not previously used), then executes the call and returns the
   result plus a signed receipt (`request_id`, `evidence_id`, `receipt_url`).

## Notes

- Each tx hash is single-use (replay-protected). Pay once per call.
- Reuse the **same** `Idempotency-Key` if a retry is needed for one logical call.
- Some routes have a small free daily quota (see `free_daily` in the feed); those
  succeed without payment until the quota is exhausted, then return 402.
- Alternative to per-call USDC: buy a `wallet_credit` pack via ACP checkout
  (see `acp-checkout.md`) to prepay a reserve that funds governed usage.

## Paid routes (price in USDC, per call)

| Route | USDC | Free/day |
|---|---|---|
| `POST /api/v1/ai/inference` | 0.008 | 5 |
| `POST /api/v1/ai/chat` | 0.005 | 5 |
| `POST /api/v1/gpc/compile` | 0.015 | 3 |
| `POST /api/v1/gpc/intent-to-plan` | 0.010 | 3 |
| `POST /api/v1/gpc/runs` | 0.020 | 0 |
| `POST /api/v1/pipelines/trigger` | 0.025 | 0 |
| `POST /api/v1/runtime/jobs` | 0.020 | 0 |
| `POST /api/v1/evidence/export` | 0.005 | 2 |
| `POST /api/v1/compliance/report` | 0.010 | 1 |
| `POST /api/v1/marketplace/acquire` | 0.050 | 0 |
| `POST /api/v1/audit/verify` | 0.003 | 5 |

Prices are authoritative in the live feed / `/.well-known/x402.json`.
