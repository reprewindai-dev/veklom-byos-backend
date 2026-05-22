# API_SURFACE.md — Complete API Route Reference

Base URL: `https://your-domain.com/api/v1`

All routes require `Authorization: Bearer <token>` unless marked public.

---

## Health & Status

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | Public | Health check — returns `{status, version, timestamp}` |
| GET | `/status` | Public | Platform status snapshot |
| GET | `/platform/pulse` | Auth | Real-time platform metrics |
| GET | `/platform/pulse/stream` | Auth | SSE stream of live platform events |

---

## Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | Public | Register new user |
| POST | `/auth/login` | Public | Login, returns JWT pair |
| POST | `/auth/logout` | Auth | Invalidate session |
| POST | `/auth/refresh` | Public | Refresh access token |
| GET | `/auth/me` | Auth | Current user profile |
| PATCH | `/auth/me` | Auth | Update profile |
| POST | `/auth/mfa/enable` | Auth | Enable MFA |
| POST | `/auth/mfa/verify` | Auth | Verify MFA code |
| GET | `/auth/api-keys` | Auth | List user API keys |
| POST | `/auth/api-keys` | Auth | Create API key |
| DELETE | `/auth/api-keys/{id}` | Auth | Revoke API key |
| GET | `/auth/oauth/github` | Public | GitHub OAuth initiation |
| GET | `/auth/oauth/github/callback` | Public | GitHub OAuth callback |

---

## AI Execution

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/exec` | Auth | SSE streaming inference (OpenAI-compatible) |
| POST | `/ai/complete` | Auth | Non-streaming completion |
| GET | `/ai/models` | Auth | List available models |
| POST | `/ai/predict-cost` | Auth | Cost prediction before execution |
| POST | `/ai/transcribe` | Auth | Audio transcription |
| POST | `/upload` | Auth | File upload for context |

---

## Workspace & Tenant

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/workspace` | Auth | Get current workspace |
| PATCH | `/workspace/settings` | Auth | Update workspace settings |
| GET | `/workspace/models` | Auth | Workspace model configurations |
| PATCH | `/workspace/models/{id}` | Auth | Toggle/update model config |
| GET | `/workspace/api-keys` | Auth | Workspace-scoped API keys |
| POST | `/workspace/api-keys` | Auth | Create workspace API key |
| DELETE | `/workspace/api-keys/{id}` | Auth | Delete workspace API key |
| GET | `/workspace/members` | Auth | List workspace members |
| POST | `/workspace/members/invite` | Auth | Invite member |

---

## Routing & Autonomous

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/routing` | Auth | Deterministic runtime routing contract |
| GET | `/routing/topology` | Auth | Route classes and `py03-irongrid` substrate contract |
| GET | `/routing/economics` | Auth | Token, latency, verification, and routing economics model |
| GET | `/routing/operational-runtime` | Auth | Governed operational runtime substrate contract |
| GET | `/routing/stack` | Auth | Veklom/UACP/GPC/py03-irongrid responsibility boundaries |
| POST | `/routing/decision` | Auth | Deterministic workload route classification |
| GET | `/autonomous/decisions` | Auth | Autonomous routing decision log |
| POST | `/autonomous/override` | Auth | Manual routing override |

---

## Compliance

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/compliance/regulations` | Auth | List compliance frameworks |
| POST | `/compliance/check` | Auth | Run compliance check on content |
| GET | `/privacy/status` | Auth | PII/PHI detection status |
| POST | `/privacy/scan` | Auth | Scan content for PII/PHI |
| POST | `/content-safety/check` | Auth | Content safety scoring |
| GET | `/explainability/{request_id}` | Auth | Model decision explanation |

---

## Audit

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/audit/logs` | Auth | Paginated audit log |
| GET | `/audit/logs/{id}` | Auth | Single audit log entry |
| GET | `/audit/verify/{id}` | Auth | Verify audit log hash integrity |

---

## Security

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/security/events` | Auth | Security event log |
| POST | `/kill-switch/activate` | Auth (admin) | Instantly disable all AI access |
| POST | `/kill-switch/deactivate` | Auth (admin) | Re-enable AI access |
| GET | `/kill-switch/status` | Auth | Kill switch current state |
| GET | `/locker/users` | Auth (admin) | Isolated user list |
| GET | `/locker/security` | Auth (admin) | Locker security events |
| GET | `/locker/monitoring` | Auth (admin) | Locker monitoring data |

---

## Billing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/wallet/balance` | Auth | Current token wallet balance |
| GET | `/wallet/transactions` | Auth | Transaction history |
| GET | `/wallet/topup/options` | Auth | Available topup packages |
| POST | `/wallet/topup/checkout` | Auth | Create Stripe checkout for topup |
| GET | `/subscriptions/current` | Auth | Current subscription plan |
| GET | `/subscriptions/plans` | Public | Available subscription plans |
| POST | `/subscriptions/checkout` | Auth | Create Stripe subscription checkout |
| GET | `/billing/invoices` | Auth | Invoice history |
| GET | `/budget/rules` | Auth | Budget rules list |
| POST | `/budget/rules` | Auth | Create budget rule |
| DELETE | `/budget/rules/{id}` | Auth | Delete budget rule |
| GET | `/cost/predict` | Auth | Cost prediction |

---

## Marketplace

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/marketplace/listings` | Auth | List marketplace items |
| GET | `/marketplace/listings/{id}` | Auth | Single listing |
| POST | `/marketplace/listings` | Auth | Create listing |
| PATCH | `/marketplace/listings/{id}` | Auth | Update listing |
| DELETE | `/marketplace/listings/{id}` | Auth | Remove listing |
| GET | `/marketplace/automation` | Auth | Automation workflows |
| POST | `/marketplace/automation` | Auth | Create automation |

---

## Pipelines

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/pipelines` | Auth | List pipelines |
| POST | `/pipelines` | Auth | Create pipeline |
| GET | `/pipelines/{id}` | Auth | Pipeline detail |
| PATCH | `/pipelines/{id}` | Auth | Update pipeline |
| DELETE | `/pipelines/{id}` | Auth | Delete pipeline |
| POST | `/pipelines/{id}/run` | Auth | Execute pipeline |
| GET | `/pipeline/interactive/session` | Auth | Interactive pipeline session |
| POST | `/demo/pipeline/run` | Auth | Demo pipeline run |

---

## Deployments & Edge

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/deployments` | Auth | List deployments |
| POST | `/deployments` | Auth | Create deployment |
| PATCH | `/deployments/{id}` | Auth | Update deployment |
| DELETE | `/deployments/{id}` | Auth | Remove deployment |
| GET | `/edge/canary/status` | Auth | Edge canary deployment status |
| POST | `/edge/canary/promote` | Auth | Promote canary to production |

---

## Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/users` | Admin | All users across workspaces |
| PATCH | `/admin/users/{id}` | Admin | Update user |
| DELETE | `/admin/users/{id}` | Admin | Delete user |
| GET | `/admin/workspaces` | Admin | All workspaces |

---

## Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/monitoring/health` | Auth | Monitoring health summary |
| GET | `/monitoring/events` | Auth | Monitoring event stream |
| GET | `/insights/summary` | Auth | Analytics summary |
| GET | `/metrics` | Auth | Prometheus-compatible metrics |
| POST | `/telemetry` | Auth | Client telemetry ingest |

---

## Internal / UACP (Advanced)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/internal/uacp/status` | Admin | UACP control plane status |
| POST | `/internal/uacp/command` | Admin | Issue UACP command |
| GET | `/internal/operators` | Admin | Operator registry |
| POST | `/internal/operators` | Admin | Register operator |
| GET | `/source-of-truth/snapshot` | Admin | Source of truth snapshot |
| POST | `/source-of-truth/sync` | Admin | Force sync |
