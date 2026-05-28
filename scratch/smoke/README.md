# Veklom smoke suites

These smoke suites are cross-platform (`Windows` and `Linux`) and use `httpx`/`playwright` instead of shell curl temp-files.

## Required environment

- `SMOKE_BASE_URL` (default: `https://api.veklom.com`)
- `SMOKE_WEB_BASE_URL` (default: `https://veklom.com`)
- `SMOKE_TIMEOUT_SECONDS` (default varies per suite)
- `SMOKE_API_HOST` (optional override; default from `SMOKE_BASE_URL`)
- `SMOKE_WEB_HOST` (optional override; default from `SMOKE_WEB_BASE_URL`)

### Auth bootstrap requirements

For authenticated and x402 paid-path checks:

- API runtime env must include `SMOKE_TEST_ENABLED=true`
- API runtime env must include `SMOKE_TEST_SECRET=<secret>`
- CI/runner env must include the same `SMOKE_TEST_SECRET`

`SMOKE_TEST_SECRET` must be configured only in Coolify/CI secrets, never committed.

**Note:** When running smoke tests locally without `SMOKE_TEST_SECRET`, the x402 payment smoke test will report 1 failure for the authenticated check. This is expected behavior - the unpaid 402 flow will still pass, which validates the payment protocol for anonymous users.

## Current smoke test status (2026-05-28)

- ✅ `anonymous_public_smoke.py`: PASS: 20 FAIL: 0
- ✅ `ui_playwright_smoke.py`: PASS: 5 FAIL: 0
- ⚠️ `x402_payment_smoke.py`: PASS: 1 FAIL: 1 (requires SMOKE_TEST_SECRET for authenticated flow)
- ⚠️ `authenticated_user_smoke.py`: Requires SMOKE_TEST_SECRET

## Commands

```powershell
python scratch/smoke/anonymous_public_smoke.py
python scratch/smoke/authenticated_user_smoke.py
python scratch/smoke/x402_payment_smoke.py
python scratch/smoke/ui_playwright_smoke.py
python scratch/smoke/openapi_validate.py
```

