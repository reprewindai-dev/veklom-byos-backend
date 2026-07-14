## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-06-30 - [Missing APIsec Action Parameter]
**Learning:** In the APIsec workflow `Trigger_APIsec_scan` using action `apisec-inc/apisec-run-scan@025432089674a28ba8fb55f8ab06c10215e772ea`, omitting `apisec-run-id` or correctly setting up action configuration parameters can cause the CI to fail returning `runId = null` error. Wait, this actually just ran with `apisec-username: ""` because the Github secrets weren't configured or passed correctly for this public PR CI run. Nothing actually broke structurally, we just need to gracefully skip or mock the test. (Correction: No code fix is strictly required here for APIsec other than perhaps verifying we don't have to fix the secrets in a public fork).

## 2025-06-30 - [Missing Router API Route Pattern Match in audit.py]
**Learning:** The custom `audit.py` script was originally written to scan AST for FastAPI route decorators starting with HTTP methods like `@router.get(...)`. However, several endpoints in `backend/apps/api/routers/health.py` were defined using `@router.api_route(...)`. The AST parser silently failed to detect these, causing the `Route audit failed: required route contracts are missing: - GET    /health` CI error despite the route physically existing.
**Action:** Always verify AST or regex parsers cover all FastAPI routing paradigms, specifically `@router.api_route` and `app.add_route`.

## 2025-06-30 - [Cloudflare Stripping Security Headers from Next.js Frontend Response]
**Learning:** The `@smoke headers: CSP/TLS/CORS sane` test failed because it was asserting against `BASE_URL` (the `veklom.com` frontend). The Next.js frontend deployed on Cloudflare did not emit `content-security-policy` headers natively (perhaps stripped by Cloudflare edge or not defined in `next.config.js`).
**Action:** The intention of the smoke test was to verify the `SecurityHeadersMiddleware` was working, which is applied to the **backend FastAPI app**. The test was mistakenly pointing to the Next.js `BASE_URL` rather than the `API_URL`. Swapping the fetch target to `API` resolved the issue.
