# Veklom BYOS Backend

> **Bring Your Own Server** — Private governed AI backend you run on your own infrastructure.

Veklom BYOS Backend is the Veklom sovereign runtime infrastructure repo. Its job is to run paid,
tenant-isolated AI workloads with deterministic routing contracts, audit evidence, billing enforcement,
and private-runtime support.

The system boundary is:

| Repo / Layer | Role | Owns |
|--------------|------|------|
| `veklom-byos-backend` | Sovereign Runtime Infrastructure | tenant runtime, auth, billing, provider execution, audit APIs |
| `UACP` | Constitutional Coordination Layer | governance hierarchy, worker gates, escalation doctrine |
| `GPC` | Deterministic Planning / Execution Compiler | intent-to-plan compilation, execution graph state, replay surface |
| `py03-irongrid` | Deterministic Routing Mesh | route scoring, mesh pressure, latency topology, data movement economics |

The bottleneck is not the model alone. The bottleneck is routing, orchestration, memory movement,
governance, token waste, inter-agent coordination, latency, deterministic execution, verification,
and infrastructure economics.

Veklom BYOS Backend runs AI workloads with:

- **Policy enforcement** — content safety, PII/PHI redaction, compliance checks
- **Intelligent routing** — model fallback, cost-quality-risk autonomous selection
- **Cost controls** — token wallet, budget rules, real-time spend tracking
- **Audit & evidence** — tamper-evident hashed audit logs, hash verification
- **API key management** — scoped keys, per-key usage tracking, kill switch
- **Tenant/workspace isolation** — full multi-tenant with role-based access
- **Optional private runtime** — connect your own vLLM, Ollama, or OpenAI-compatible endpoint

Designed for enterprise teams, healthcare organizations, and security-conscious companies that cannot send data through shared cloud AI infrastructure.

---

## Quick Start

```bash
git clone https://github.com/reprewindai-dev/veklom-byos-backend
cd veklom-byos-backend
cp .env.example .env
# Fill in required env vars (see ENVIRONMENT.md)
pip install -r requirements.txt
alembic upgrade head
uvicorn backend.apps.api.main:app --reload
```

Health check: `GET http://localhost:8088/health`

### Login & Registration

The backend supports three authentication methods:

1. **Register** - Create a new account:
   ```bash
   POST /api/v1/auth/register
   {
     "email": "your@email.com",
     "password": "your-password",
     "full_name": "Your Name",
     "workspace_name": "My Workspace"
   }
   ```

2. **Login** - Sign in with email/password:
   ```bash
   POST /api/v1/auth/login
   {
     "email": "your@email.com",
     "password": "your-password"
   }
   ```

3. **Free Evaluation Session** - Try without registration:
   ```bash
   POST /api/v1/auth/eval-session
   {
     "fingerprint": "browser-fingerprint"
   }
   ```

After login, use the `access_token` in the `Authorization: Bearer <token>` header for authenticated requests.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [SETUP.md](./SETUP.md) | Local development setup |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Docker / Coolify / Render / Hetzner deploy |
| [ENVIRONMENT.md](./ENVIRONMENT.md) | All environment variables explained |
| [API_SURFACE.md](./API_SURFACE.md) | Every route family and endpoint |
| [SECURITY_MODEL.md](./SECURITY_MODEL.md) | Auth, isolation, secrets architecture |
| [LICENSE_ACTIVATION.md](./LICENSE_ACTIVATION.md) | Buyer license key activation |
| [BUYER_PACKAGE.md](./BUYER_PACKAGE.md) | What you receive, support terms |
| [SELLABLE_BACKEND_AUDIT.md](./SELLABLE_BACKEND_AUDIT.md) | Module readiness audit |
| [SOURCE_BACKEND_INVENTORY.md](./SOURCE_BACKEND_INVENTORY.md) | Full folder/route/dep inventory |
| [DETERMINISTIC_AI_INFRASTRUCTURE.md](./DETERMINISTIC_AI_INFRASTRUCTURE.md) | Veklom/UACP/GPC/py03-irongrid role doctrine |
| [GOVERNED_OPERATIONAL_RUNTIME.md](./GOVERNED_OPERATIONAL_RUNTIME.md) | Operational runtime substrate, telemetry, governance, BYOS, and survivability spec |

---

## Architecture

```
veklom-byos-backend/
├── backend/
│   ├── apps/api/
│   │   ├── main.py          # FastAPI app, middleware, router registration
│   │   └── routers/         # 43 router modules
│   ├── core/                # Config, auth, DB engine, security
│   ├── db/                  # SQLAlchemy models, Alembic migrations
│   ├── license/             # License server, package guard
│   ├── scripts/             # Deploy, health, license scripts
│   └── tests/               # pytest test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .env.production.example
```

---

## Core Capabilities

### AI Execution
- `POST /api/v1/exec` — SSE streaming inference with policy enforcement
- OpenAI-compatible interface
- Connect to OpenAI, Anthropic, vLLM, Ollama, or any compatible endpoint
- Per-request cost prediction before execution
- Autonomous routing: selects best model by cost/quality/risk

### Governance & Compliance
- Content safety scoring on every request
- PII/PHI detection and optional redaction
- Compliance regulation checks (HIPAA, GDPR, SOC2)
- Explainability endpoint for model decisions
- Tamper-evident audit logs with SHA hash chains

### Security
- JWT authentication + optional MFA
- API key management with scoped permissions
- Kill switch: instantly revoke all AI access
- Locker isolation: per-tenant security boundaries
- Security event log

### Billing & Cost
- Token wallet with prepaid credit model
- Budget rules with hard/soft limits
- Real-time spend tracking
- Stripe subscriptions + metered usage
- Topup checkout flow

### Multi-Tenant
- Full workspace isolation
- Role-based access (owner, admin, member, viewer)
- Per-workspace model configs, API keys, budgets
- Admin panel for user/workspace management

---

## License

Commercial license. See [LICENSE_ACTIVATION.md](./LICENSE_ACTIVATION.md) and [BUYER_PACKAGE.md](./BUYER_PACKAGE.md).

© 2026 CO2 Router / Veklom. All rights reserved.
