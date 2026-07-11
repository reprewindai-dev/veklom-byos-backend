# Veklom BYOS Backend

Veklom AI is a private governed AI backend that allows secure, compliant, and customizable AI workload management on your own infrastructure, offering policy control, cost management, auditing, and tenant isolation.

## Core Capabilities
- **Private AI Backend**: Veklom BYOS (Bring Your Own Server) allows organizations to run AI workloads on their own servers or cloud infrastructure, ensuring full control over data and deployment environments.
- **Governance and Policy Control**: The platform provides detailed policy management capabilities to enforce organizational standards and compliance requirements. Teams can define rules on how AI models are used, which workloads are permitted, and what access controls are applied.
- **Routing and Multi-Tenant Support**: Veklom supports workload routing and tenant isolation, enabling multiple teams or clients to operate securely on the same infrastructure without risk of data crossover.
- **Cost Controls**: The platform includes cost management features that allow monitoring and controlling compute expenditure for AI workloads across tenants, helping organizations optimize resource usage and reduce unnecessary spend.
- **Audit and Evidence Tracking**: Every AI operation can be logged for audit purposes. This ensures accountability, traceability, and evidence collection for regulatory compliance or internal reviews.
- **API Key Management**: Veklom provides flexible API key management, making it straightforward to integrate with existing applications and control access to AI models and services.
- **Compliance and Security**: The platform emphasizes regulatory compliance, supporting industry-standard security practices and allowing organizations to maintain audits, access controls, and secure operations on their own infrastructure.

## Deployment Flexibility
Veklom can be deployed on local servers or in private clouds, providing enterprises with maximum control over data location, security, and network configuration. This flexibility is especially valuable for organizations dealing with sensitive data or operating in highly regulated industries such as healthcare and finance.

## Summary
Veklom is designed for organizations that need a secure, multitenant, and policy-driven AI platform while maintaining full control over their infrastructure. Its key features—policy management, tenant isolation, cost controls, audit logging, and API integration—make it suitable for enterprise-grade AI operations where governance, compliance, and operational transparency are critical.

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

Health check: `GET http://localhost:80/health`

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
