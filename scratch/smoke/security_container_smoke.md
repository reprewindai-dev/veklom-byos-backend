# Veklom Container Security Triage

Date: 2026-05-28  
Scope: `ghcr.io/reprewindai-dev/veklom-byos-backend` release pipeline (`secure-release`)

## Actions Applied

1. Switched to a hardened multi-stage Docker build:
- Builder stage compiles wheels with build deps.
- Runtime stage removes compiler toolchain and curl/wget from final image.
- Runtime runs as non-root user `veklom` (uid/gid `10001`).
- Healthcheck uses Python stdlib HTTP probe (no curl dependency).

2. Upgraded vulnerable Python dependencies where feasible:
- `python-multipart` -> `0.0.27`
- `pyasn1` -> `0.6.3`
- `wheel` -> `0.46.2`

3. Trivy pipeline hardening:
- Added JSON report export (`trivy-report.json`) artifact upload.
- Added `.trivyignore` with scoped reason, expiry, and ticket IDs.
- Scan still fails on non-ignored `HIGH/CRITICAL`.

## Remaining Risk (Documented Ignore)

Ignored in `.trivyignore` with expiry `2026-07-31`:
- `CVE-2026-42496`, `CVE-2026-8376`, `CVE-2026-42497`, `CVE-2026-9538` (`perl-base`, unresolved in upstream base image at scan time)
- `CVE-2025-62727` (`starlette`, blocked by framework compatibility window)
- `CVE-2024-23342` (`ecdsa`, transitive dependency pending validated replacement)

## Follow-up

1. Re-run Trivy against the new image digest and remove ignore entries once fixed versions are available.
2. Upgrade FastAPI/Starlette together in a compatibility-tested patch train, then drop the Starlette ignore.
3. Re-check dependency tree for a path to eliminate vulnerable `ecdsa` transitively.

