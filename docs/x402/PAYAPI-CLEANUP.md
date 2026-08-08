# PayAPI / x402 cleanup status

This note records the cleanup boundary while the canonical external paid-capability verification flow is being rebuilt.

## Removed legacy surface

- `backend/apps/api/routers/archive/payapi_compliance.py` was an archived compatibility router for the old PayAPI catalog. It must not be restored or mounted as a production router.
- `tests/test_payapi_compliance.py` was a route-presence smoke test, not execution verification. It accepted 200/201/401/402 and therefore did not prove payment, capability delivery, output validity, evidence binding, or replay rejection.

## Current rule

External x402 readiness is **not** established by route existence, TLS, a 402 response, or settlement alone.

The replacement verification path must bind:

1. payment challenge,
2. verified payment proof,
3. canonical capability id + version,
4. governance authorization,
5. actual execution,
6. contract-valid output,
7. output hash,
8. durable evidence/receipt,
9. replay + idempotency protection.

## Tracking

- #173 — real paid-execution verification test
- #174 — retire PayAPI catalog-era route sprawl and choose one canonical external x402 capability
- cAPI #32 — canonical ownership across repos

Do not add new PayAPI-specific runtime routes while those issues are open. New external listing work should target the canonical capability contract selected in #174.
