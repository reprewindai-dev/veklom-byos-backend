# Veklom Backend Middleware Audit & Alignment

**Source of Truth:** `veklom-byos-backend`
**Date:** 2026-05-21

## Overview
An audit of an older Veklom backend identified the need for `EntitlementCheckMiddleware` and `TokenDeductionMiddleware` to enforce subscription plans and decrement wallet tokens per execution.

However, the `veklom-byos-backend` implements security boundaries using robust **FastAPI Dependency Injection (`Depends`)** rather than brittle ASGI middlewares. Therefore, these audit requirements have been successfully ported into our dependency architecture.

## Entitlement Checks
- **Old Concept:** `EntitlementCheckMiddleware`
- **New Implementation:** `backend/core/security/entitlements.py`
- **Behavior:** Exposes `require_entitlement(plan: str)` as a route dependency. It verifies if the user's workspace possesses at least the requested subscription plan hierarchy: `starter -> pro -> sovereign -> enterprise`.

## Token Deduction Guard
- **Old Concept:** `TokenDeductionMiddleware`
- **New Implementation:** `backend/core/security/wallet_guard.py`
- **Behavior:** Maps exact routes to an `endpoint_catalog` token cost. Exposes a `TokenDeductionGuard` class that intercepts requests, checks the workspace token wallet, and atomically deducts tokens (or operates in "test mode" to simply log the impending deductions without failure).

## Deployment Phases
- **Phase 1-3:** Documentation and integration in staging (Done).
- **Phase 4-5:** Enable in TEST MODE (Done). The guards will execute but will **not** block traffic or mutate database rows until Phase 6.
- **Phase 6:** Full database deduction enabled.
