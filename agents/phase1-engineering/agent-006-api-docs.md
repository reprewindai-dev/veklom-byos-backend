# Agent-006 — API DOCS ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** MEDIUM

---

## Mission

Create public developer documentation for the Veklom API. OpenAPI/Swagger is currently auth-gated and disabled in production. Build a public docs site with interactive examples, authentication guide, and SDK quickstarts.

## Current State

- FastAPI auto-generates OpenAPI spec — ✅ (but disabled in prod)
- 40+ routers with endpoints — ✅
- No public API documentation site
- No SDK or quickstart guides
- No interactive API explorer

## Tasks

1. Enable OpenAPI spec export (read-only, public subset)
2. Set up docs site (Mintlify, Docusaurus, or static):
   - Authentication guide (JWT flow, API keys)
   - Endpoint reference (grouped by domain)
   - Interactive "Try It" panels
   - Code examples in Python, JavaScript, cURL
3. Write quickstart guides:
   - "Your First API Call" (auth + basic endpoint)
   - "Running a Pipeline" (create → execute → poll results)
   - "Marketplace Integration" (list → purchase → download)
4. Generate SDK stubs (Python + TypeScript)
5. Deploy docs to `docs.veklom.com` or `/docs` path

## Success Metrics

| Metric | Target |
|---|---|
| Endpoints documented | 40+ |
| Quickstart guides | 3 |
| Code examples per endpoint | 3 languages |
| Docs site deployed | Yes |
| Time to first API call (new dev) | < 10 minutes |

## Daily Checklist

- [ ] Day 1: Export OpenAPI spec, set up docs framework
- [ ] Day 2: Write endpoint reference for auth, pipelines, marketplace
- [ ] Day 3: Quickstart guides + code examples
- [ ] Day 4: Deploy docs site + PR

## Dependencies

- Agent-000 (MASTER_STATE.md for endpoint inventory)
- Agent-008 (security review of public API surface)

## Playbook

```
Repo: byosbackened
Branch: main
Reference: BACKEND_API_INVENTORY.md for endpoint map
Output: docs/ directory or separate docs repo
```
