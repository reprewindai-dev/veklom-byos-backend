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


***

## 12. Product Entitlement Architecture (Action-Locking, Tiers, Reserve & Local Operator Layout)

Veklom implements a **tier + reserve + marketplace add-on model** rather than an "everything is subscription" setup. The workspace features remain visible, navigation is open, previews are sandboxed, and only active mutation/execution actions are gated.

### 1. Entitlement Decision Structure

The backend entitlement service evaluates every gated action and returns:

```typescript
type EntitlementDecision = {
  canView: boolean;
  canPreview: boolean;
  canExecute: boolean;

  currentTier: "free" | "founding" | "standard" | "regulated";
  requiredTier?: "founding" | "standard" | "regulated";

  gateType:
    | "quota_gate"
    | "feature_gate"
    | "marketplace_gate"
    | "risk_gate"
    | "reserve_gate";

  action: string;
  reason: string;

  benefits: string[];
  bestFor: string[];

  recommendedUpgrade?: {
    tier: "founding" | "standard" | "regulated";
    headline: string;
    cta: string;
  };

  marketplaceAlternative?: {
    moduleId: string;
    name: string;
    price: string;
    note: string;
  };

  usageContext?: {
    freeRunsUsed: number;
    freeRunsLimit: number;
    attemptedFeatureCount: number;
    estimatedRunCost?: number;
  };
};
```

### 2. Tier Access and Quota Matrix

- **Free Evaluation ($0, no card)**:
  - 1 workspace, 1 user, 15 governed runs, 3 compare runs, 20 dry-run pipeline tests, 2 signed sandbox exports, marketplace browsing, live governance demo, playground access, basic model-routing/monitoring/billing previews.
  - Quotas: Hard-gated at 15 runs. Quota Gate fires showing upgrade path to Founding, Standalone Module purchase, or Regulated inquiry.
- **Founding Activation ($395 activation + $100–$150 minimum reserve)**:
  - production workspace, paid governed runs, saved prompts, GitHub connection, basic marketplace installs, safe terminal, API key creation, pipeline test/deploy, evidence packages à la carte, limited supervised agents (1 active agent/session at a time under human approval).
- **Standard ($795 activation + $250–$300 minimum reserve)**:
  - team workspace, production deployments, vault/compliance/monitoring/billing fully active, advanced marketplace installs, repo-risk/cost/policy gates included or discounted, scheduled pipelines, multi-agent workflows (limited concurrent agents).
- **Regulated (From $2,500 + regulated reserve)**:
  - UACP6 governance, SEKED human/org approval state, consent catalogs, auditor bundles, regulated evidence, SAML/SCIM, BYOS/private deployment, custom policy packs, regulated model registry, governed agent workforce with approval chains, dedicated onboarding/support.

### 3. Action-Gate Mapping

Only gate mutation/execution actions:
- `production_run`: requires `founding`
- `deploy` (production deployment / publish endpoint): requires `standard` (can also purchase "deploy-gate" standalone for $79/mo)
- `install_module`: requires `founding`
- `export_signed_evidence`: requires `regulated` (can also purchase "auditor-bundle" standalone for $299/mo)
- `create_api_key`: requires `founding`
- `activate_agent`: requires `founding` (can also purchase "agent-packs" standalone for $49/mo)
- `add_secret`: requires `standard`
- `invite_team_member`: requires `standard`
- `schedule_pipeline`: requires `standard`
- `execute_terminal_command`: requires `standard`
- `regulated_compliance_action`: requires `regulated`

### 4. Stripe Implementation
- **Tier activation**: Founding / Standard / Regulated checkout (pricing-plan setups combining recurring and usage-based charges).
- **Reserve funding**: USD-denominated operating reserve.
- **Marketplace purchases**: Module purchase, vendor payouts (Stripe Connect with NET-14 payouts and standard 12% / preferred 8% / founding 0% platform fee structures).

### 5. Local Operator Build Script (`veklom-finalize-local.ps1`)

Local machine operator directories (`.openclaw`, `.npm-global`, `.expo`, `.docker`) live under `%USERPROFILE%` as local build-runner infrastructure, keeping real containers, Hetzner, Coolify, and future BYOS installs clean:

```powershell
$UserRoot = $env:USERPROFILE

$OpenClawHome = $env:OPENCLAW_HOME
if (-not $OpenClawHome) { $OpenClawHome = Join-Path $UserRoot ".openclaw" }

$NpmGlobal = $env:NPM_CONFIG_PREFIX
if (-not $NpmGlobal) { $NpmGlobal = Join-Path $UserRoot ".npm-global" }

$ExpoHome = $env:EXPO_HOME
if (-not $ExpoHome) { $ExpoHome = Join-Path $UserRoot ".expo" }

$DockerConfig = $env:DOCKER_CONFIG
if (-not $DockerConfig) { $DockerConfig = Join-Path $UserRoot ".docker" }

$VeklomHome = Join-Path $UserRoot ".veklom"
$BackroomHome = Join-Path $VeklomHome "backroom"
$MarketplaceHome = Join-Path $VeklomHome "marketplace"
$TerminalHome = Join-Path $VeklomHome "terminal"

$dirs = @(
  $OpenClawHome,
  $NpmGlobal,
  $ExpoHome,
  $DockerConfig,
  $VeklomHome,
  $BackroomHome,
  $MarketplaceHome,
  $TerminalHome
)

foreach ($d in $dirs) {
  if (-not (Test-Path $d)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
  }
}

# Copy only safe artifacts.
Copy-Item ".\dist\terminal\*" $TerminalHome -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item ".\marketplace\catalog.json" $MarketplaceHome -Force -ErrorAction SilentlyContinue
Copy-Item ".\agents\skills\*" (Join-Path $OpenClawHome "skills") -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Veklom local operator build finalized."
```

***

## 13. System Components & Terminal Naming (Correction)

Veklom enforces a clear structural boundary between product presentation, agent orchestration, and sovereign governance:

### Core Architecture Splits
1. **Veklom**: The product shell, marketplace, and tenant workspace.
2. **UACP6 (Sovereign Governance Layer)**: Governs trust, consent, national/regulated workflows, compliance logs, identity checks, and integrity gates.
3. **UACP4 (Agent Artibus / ArbiterOS)**: The agent arbitration layer. Governs instruction validation, SEKED state compilation, memory cycles, decision frames, and SAIQ environmental/cost/policy routing.
4. **BYOS Backend**: The execution fabric (auth, tenants, billing, marketplace, model routing, tools/connectors execution).
5. **Marketplace**: Packages all reusable/monetizable modules (policy/cost gates, terminal packs, compliance analyzers, evidence bundle exports).

### Terminal Classifications
Veklom maintains three distinct terminal interfaces, each with dedicated operator responsibilities:
1. **PerplexTerminal v4.1 (Operator mobile terminal)**: Operator-facing visual cockpit displaying cognitive engine states, Zeno counterfactual speculation, Gladiator cognitive limits, and live MCP mesh topology.
2. **UACP Quantum Context Terminal (Technical/API terminal)**: Serves as the embedded developer console and endpoint runner. Supports quick operations like `POST /autonomous/execute`, health probes, and Zeno capabilities.
3. **Terminal 100 / Source-of-Truth Terminal (Canonical workspace terminal)**: Served at `/terminal` in production. Merges the visual strength of PerplexTerminal with the real endpoint execution of the Quantum Context Terminal, bridging command entries to real `VeklomRun` DB entities.

### Corrected Execution Loop
```text
User / Agent intent
  ↓
Veklom Run created
  ↓
UACP4 Agent Artibus / ArbiterOS decides
  ↓
SEKED validates human/org state
  ↓
SAIQ routes by policy > water > latency > carbon > cost
  ↓
BYOS runtime executes
  ↓
UACP6 sovereign layer seals governance / consent / audit meaning
  ↓
Decision Frame + Evidence + Billing + Marketplace accounting
  ↓
Terminal shows the real run
```

### Workspace Component Splits
* **Backroom Workspace (Founder/Operator Exclusive)**: Command Center, UACP6 governance ops, Product Studio, Marketplace Triage, internal 30-agent divisions, Capital-Guard, Hybrid-Forge, security engineering, FinOps, release readiness, production audit, wiring matrix.
* **Tenant Workspace**: Playground, Models, Marketplace, Pipelines, Deployments, Vault, Compliance, Monitoring, Billing, Team, Settings, safe optional terminal, evidence exports.


***

## 14. Onchain / Base / Agentic Trading Module

Veklom should include an onchain trading and treasury lane.

Do not keep agentic trading completely separate from Veklom.
Include it as a governed workspace module, with marketplace extensions and tiered execution rights.

Positioning:
Veklom is not trying to copy Base App.
Veklom uses Base/onchain rails as wallet, discovery, and settlement infrastructure.
Veklom owns agent governance, risk caps, approvals, evidence, terminal visibility, marketplace modules, and run history.

Feature names:
- Onchain Ops
- Trading Agents
- Treasury Agents
- Base Connector
- Wallet Execution Lane
- Agentic Trading Lab

Tiering:
Free:
- watch mode
- paper trading
- simulated portfolio
- demo signals
- no real execution

Founding:
- wallet connection
- approve-each-trade mode
- capped real trades
- evidence per trade
- no default leverage

Standard:
- Bounded autopilot
- strategy modules
- portfolio rules
- kill switch
- daily loss/spend caps
- allowed asset lists
- marketplace trading packs

Regulated / Premium:
- governed treasury
- entity wallets
- approval chains
- audit exports
- compliance evidence
- private/BYOS executor
- policy packs

Backroom:
- full founder trading lab
- agent experiments
- strategy testing
- marketplace triage for trading modules
- internal risk/capital guard

Execution rule:
Agents may propose, simulate, and execute trades only inside configured risk boundaries.
Every real trade must create a VeklomRun.
Every VeklomRun must include policy decision, risk check, cost/fee/slippage data, approval state, transaction result, and evidence record.

Never allow unrestricted blind wallet execution.
Never market guaranteed returns.
Never let agents directly hold raw credentials.
Use wallet signing, server-side execution adapters, proxy controls, spending caps, and kill switches.



