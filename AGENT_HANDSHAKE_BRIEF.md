# Veklom Agent Handshake Brief
## Backend Integration Source of Truth

***

## 1. Backend Base URL

```
Production:  https://veklom.com/api/v1
             (or https://app.veklom.com/api/v1)

Local dev:   http://localhost:8088/api/v1
```

The backend runs on **port 8088** internally. Coolify forwards 443 → 8088. Never hardcode `:8088` in production — always use the HTTPS domain. 

***

## 2. Health Check (first thing any agent should call)

```
GET https://veklom.com/health
```

Expected: `200 OK`. If this fails, the backend is down or Coolify's port forwarding is broken. Stop there before wiring anything else. 

***

## 3. Auth Handshake (every client must do this first)

### Register
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@domain.com",
  "password": "securepassword",
  "full_name": "Display Name"
}
```

### Login → get JWT
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@domain.com",
  "password": "securepassword"
}
```

Response includes:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer"
}
```

### All subsequent requests must include:
```http
Authorization: Bearer <access_token>
```

JWT access tokens expire in **30 minutes**. Refresh tokens last **30 days**. Use `POST /api/v1/auth/refresh` with the refresh token to get a new access token without re-login. 

***

## 4. CORS — Allowed Origins

The backend only accepts requests from these origins. Any frontend calling the API must be served from one of these: 

```
https://veklom.com
https://www.veklom.com
https://app.veklom.com
```

For local development, `localhost` and `127.0.0.1` are allowed. If you deploy a new frontend to a new domain (e.g., `marketplace.veklom.com`), you must add it to `CORS_ORIGINS` in the Coolify environment before it will work.

***

## 5. Key API Route Groups

All routes are prefixed with `/api/v1`. 

| Route Group | Prefix | Purpose |
|---|---|---|
| Auth | `/api/v1/auth/` | Register, login, refresh, logout, MFA |
| Users | `/api/v1/users/` | Profile, settings, tenant membership |
| Marketplace | `/api/v1/marketplace/` | Listings, modules, tool packages |
| AI/Router | `/api/v1/ai/` | LLM routing, provider selection, inference |
| Billing | `/api/v1/billing/` | Stripe subscriptions, usage metering |
| Governance | `/api/v1/governance/` | UACP policy gates, audit ledger |
| Webhooks | `/api/v1/webhooks/` | Stripe, Resend inbound webhooks |

***

## 6. What Each Veklom System Calls on the Backend

Use this so no agent invents its own endpoints:

| System | What it calls | Notes |
|---|---|---|
| **V3 Black Box** | `/api/v1/ai/` routes | Intent → governed execution. JWT required |
| **UACP** | `/api/v1/governance/` routes | Policy evaluation, integrity gates, audit ledger |
| **GPC** | `/api/v1/ai/` (plan phase) | Structured execution plan generation |
| **Marketplace** | `/api/v1/marketplace/` routes | Listings, module registry, vendor packages |
| **GreenVision** | `/api/v1/ai/` + routing params | Carbon/cost/region signals passed as metadata |
| **IronGrid** | Internal routing substrate | Does not call API directly — feeds into AI router |

***

## 7. Environment Variables Any Frontend Needs

For any React/TS frontend connecting to the backend, set these as env vars (`.env` or Coolify environment): 

```env
VITE_API_BASE_URL=https://veklom.com/api/v1
VITE_APP_ENV=production
VITE_STRIPE_PUBLISHABLE_KEY=YOUR_STRIPE_PUBLISHABLE_KEY
```

For local dev:
```env
VITE_API_BASE_URL=http://localhost:8088/api/v1
VITE_APP_ENV=development
```

***

## 8. Standard Fetch Pattern (copy-paste for any frontend component)

```typescript
// veklom-api.ts — shared client, import this everywhere
const BASE = import.meta.env.VITE_API_BASE_URL ?? 'https://veklom.com/api/v1';

export async function veklomFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }

  return res.json();
}
```

Usage in any component:
```typescript
// Login
const { access_token } = await veklomFetch('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});

// Any protected call
const listings = await veklomFetch('/marketplace/listings', {}, access_token);
```

***

## 9. V3 Black Box Specific Handshake

When V3 sends intent to the backend, it should call the AI router with a structured payload:

```typescript
// V3 → backend intent submission
const result = await veklomFetch('/ai/execute', {
  method: 'POST',
  body: JSON.stringify({
    intent: "user's raw input",
    tenant_id: "tenant-uuid",
    policy_context: "standard",   // or "strict" / "audit"
    provider_preference: "auto",  // or "openai" / "gemini" / "groq"
  })
}, access_token);
```

The backend applies UACP policy gates, routes to the correct provider, returns governed output + audit checksum. V3 displays only the governed output in the center panel. 

***

## 10. Common Failure Modes an Agent Should Handle

| Symptom | Root cause | Fix |
|---|---|---|
| `401 Unauthorized` | Missing or expired JWT | Re-run auth login, use fresh `access_token` |
| `500` on auth endpoints | DB connection failed | Verify `DATABASE_URL` in Coolify uses `5.78.135.11`, not `postgres:5432` |
| CORS error in browser | Frontend domain not in `CORS_ORIGINS` | Add domain to Coolify env var, redeploy |
| API routes 404 | Port 8088 not forwarded | Coolify must forward 80/443 → 8088 |
| Empty AI responses | Provider key missing | Add `OPENAI_API_KEY` / `GEMINI_API_KEY` in Coolify env |

***

## 11. Landing page audience pills correction

On the public homepage, the audience/persona pills must be:

1. Teams
2. Developers
3. Agents
4. Enterprise

Do not use “Humans” as the landing page audience label.

Use “Teams” instead.

Reason:
“Humans” sounds abstract and cold. “Teams” is clearer, more commercial, and better matches the product motion: workspace, collaboration, governance, monitoring, compliance, and shared execution.

Important:
Only replace the public landing page persona/audience label “Humans” with “Teams.”
Do not remove technical uses of “human” where it is correct, such as:
- human approval
- human-in-the-loop
- human/operator state
- SEKED human state
- human review gates

### Homepage Structure

Homepage audience pills:

#### Teams
- Default selected pill.
- Shows Veklom as the governed AI workspace for real teams.
- Focus: workspace, playground, team command center, monitoring wall, compliance wall, Govern UI, billing/reserve, marketplace, evidence.
- CTA: Start Free Evaluation
- Secondary CTA: Explore Workspace

#### Developers
- Shows Veklom as the governed build/deploy layer.
- Focus: APIs, terminal, pipelines, GitHub/repo risk gates, model routing, x402, MCP, CLI, deploy previews.
- CTA: Open Developer Terminal
- Secondary CTA: View API / Docs

#### Agents
- Shows Veklom as the runtime and arbitration layer for governed agents.
- Focus: UACP4 Agent Artibus, ArbiterOS, SEKED, SAIQ, safe execution, policy gates, approvals, evidence, spend controls.
- CTA: See Agent Runtime
- Secondary CTA: View Governance Flow

#### Enterprise
- Shows Veklom as the sovereign governance and compliance platform.
- Focus: UACP6, consent catalogs, audit chain, regulated evidence, BYOS/private deployment, SAML/SCIM, model registry, compliance exports.
- CTA: Request Regulated Access
- Secondary CTA: View Trust Layer

### Copy Direction

#### Teams pill copy
- **Headline**: Give your team a governed AI workspace.
- **Body**: Use the Playground, Marketplace, Pipelines, Monitoring Wall, Compliance Wall, Govern UI, and Terminal in one control plane. Explore everything in Free, then unlock production execution when your team is ready.
- **Feature chips**:
  - Workspace
  - Playground
  - Team Command Center
  - Monitoring Wall
  - Compliance Wall
  - Govern UI
  - Marketplace
  - Evidence

### Important Distinction
- **Public landing “Team Command Center”** = tenant-facing workspace overview/control surface.
- **Backroom “Command Center”** = founder/operator-only internal control room.
- Do not expose founder-only backroom controls to tenants just because the homepage says Command Center.

