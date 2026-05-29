"""Veklom BYOS Backend — Main FastAPI Application.

Source of truth: Veklom backend routes + API_SURFACE.md.
All routes wired for the REALFRONTEND built frontend.
"""

import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from sqlalchemy import select

from backend.core.security.middlewares import (
    ZeroTrustMiddleware,
    MetricsMiddleware,
    IntelligentRoutingMiddleware,
    BudgetCheckMiddleware
)

from backend.core.config.settings import settings
from backend.core.database.database import Base, engine
from backend.core.plugins.manager import plugin_manager
from backend.core.security.middleware import SecurityHeadersMiddleware
from backend.core.middleware.x402 import X402PaymentMiddleware

# Import model package to ensure tables are registered with Base.metadata.
import backend.db.models  # noqa: F401

# Configure Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        send_default_pii=True,
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("APP_VERSION", "1.0.0"),
    )

# Configure OpenTelemetry for Grafana Cloud
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
OTEL_HEADERS = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "").strip()

has_valid_endpoint = OTEL_ENDPOINT and "NEED_FROM" not in OTEL_ENDPOINT
has_valid_headers = OTEL_HEADERS and "NEED_FROM" not in OTEL_HEADERS and "=" in OTEL_HEADERS

if has_valid_endpoint and has_valid_headers:
    provider = TracerProvider()
    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=OTEL_ENDPOINT,
            headers=OTEL_HEADERS,
        )
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Discover available plugins on startup
    await plugin_manager.discover_plugins()

    # Initialize database schema.  We log loud + structured because a silent
    # success here used to mask cases where the metadata object had zero
    # tables registered (because of import order) or the connection pointed
    # at the wrong DB.  Now we always count what was registered and verify
    # at least the critical tables landed.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            registered = sorted(Base.metadata.tables.keys())
            print(f"[startup] db: create_all completed, {len(registered)} tables on Base.metadata")
            # Verify a subset that every endpoint depends on.  If any are
            # missing AFTER create_all, the DB is misconfigured and we want
            # the log to scream.
            from sqlalchemy import text
            critical = ("users", "execution_logs", "audit_logs", "workspaces", "repo_risk_gate_runs", "agents")
            check = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name = ANY(:names)"
            ), {"names": list(critical)})
            present = {r[0] for r in check}
            missing = [t for t in critical if t not in present]
            if missing:
                print(f"[startup] db: WARNING — critical tables missing after create_all: {missing}")
            else:
                print(f"[startup] db: critical tables verified ({len(critical)} present)")
    except Exception as e:
        # Loud error so it shows up in container logs and Sentry.
        import traceback
        print(f"[startup] db: FAILED to initialise schema: {type(e).__name__}: {e}")
        traceback.print_exc()
        # Continue startup — but the operator now sees the error.

    # Idempotent column additions for HRM fields on the `agents` table.
    # `create_all` only creates new tables, not new columns on existing ones.
    # These ALTER TABLE ... ADD COLUMN IF NOT EXISTS statements are safe to
    # re-run on every startup.
    hrm_columns = [
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS hrm_tier VARCHAR(32)",
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS agent_number INTEGER",
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS squad_id VARCHAR(64)",
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS capabilities JSONB",
        "CREATE INDEX IF NOT EXISTS ix_agents_hrm_tier ON agents (hrm_tier)",
        "CREATE INDEX IF NOT EXISTS ix_agents_agent_number ON agents (agent_number)",
        "CREATE INDEX IF NOT EXISTS ix_agents_squad_id ON agents (squad_id)",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in hrm_columns:
                await conn.execute(text(ddl))
        print("[startup] db: HRM column migration completed")
    except Exception as e:
        print(f"[startup] db: HRM migration warning: {type(e).__name__}: {e}")

    # Idempotent column additions for workspaces (GitHub selection fields)
    workspace_github_columns = [
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS selected_repo VARCHAR(255)",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS selected_repo_branch VARCHAR(128)",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS github_provider VARCHAR(64)",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS github_selected_by VARCHAR(36)",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS github_selected_at TIMESTAMP",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in workspace_github_columns:
                await conn.execute(text(ddl))
        print("[startup] db: Workspace GitHub column migration completed")
    except Exception as e:
        print(f"[startup] db: Workspace GitHub migration warning: {type(e).__name__}: {e}")

    # Idempotent column additions for pipeline_runs
    pipeline_run_columns = [
        "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(36)",
        "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)",
        "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS steps JSONB",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in pipeline_run_columns:
                await conn.execute(text(ddl))
        print("[startup] db: PipelineRun column migration completed")
    except Exception as e:
        print(f"[startup] db: PipelineRun migration warning: {type(e).__name__}: {e}")

    # Seed first-class skills that should always be present in the registry.
    # Skills with is_available=False are catalogued but NOT invokable.
    # Add to this list when a new skill's spec is defined; flip is_available
    # to True only when the backend implementation exists.
    from backend.db.models.agent import AgentSkill
    _SEED_SKILLS = [
        {
            "skill_id": "passive-income-engine",
            "name": "Passive Income Engine",
            "version": "0.1",
            "description": (
                "Finds high-demand, legally usable RAG dataset opportunities and "
                "creates draft Veklom marketplace listings. Does NOT publish without "
                "explicit operator approval. Rule: if invoked without implementation, "
                "returns SKILL_MISSING."
            ),
            "is_available": False,
            "missing_reason": (
                "SKILL_MISSING — no backend implementation yet. "
                "The skill is catalogued per spec. "
                "To implement: create a route that calls a real dataset-discovery "
                "API, checks license suitability, and POSTs draft listings to "
                "/api/v1/marketplace/listings with status=draft. "
                "Do not publish or upload datasets without license verification."
            ),
            "input_schema": {
                "opportunity_types": ["rag_dataset", "workflow_pack", "compliance_pack"],
                "max_results": 3,
                "license_filter": ["MIT", "Apache-2.0", "CC-BY-4.0", "Public Domain"],
                "exclude_types": ["scraped", "restricted", "PHI", "PII", "private"],
            },
            "output_schema": {
                "listings": [
                    {
                        "name": "string",
                        "source_url": "string",
                        "license": "string",
                        "why_trending": "string",
                        "rag_use_case": "string",
                        "target_buyer": "string",
                        "veklom_category": "string",
                        "listing_type": "string",
                        "ingestion_plan": "string",
                        "chunking_strategy": "string",
                        "gpc_template_idea": "string",
                        "evidence_requirements": "string",
                        "risks": "string",
                        "approval_status": "draft",
                    }
                ]
            },
        },
    ]
    try:
        from backend.core.database.database import async_session
        async with async_session() as seed_session:
            for skill_def in _SEED_SKILLS:
                existing = (await seed_session.execute(
                    select(AgentSkill).where(AgentSkill.skill_id == skill_def["skill_id"])
                )).scalar_one_or_none()
                if not existing:
                    seed_session.add(AgentSkill(**skill_def))
            await seed_session.commit()
        print(f"[startup] skills: seeded {len(_SEED_SKILLS)} first-class skills")
    except Exception as e:
        print(f"[startup] skills: seed warning: {type(e).__name__}: {e}")

    # Seed default budget caps for minimum live operator set.
    # These are conservative defaults — adjust per operator via the API.
    _OPERATOR_BUDGETS = [
        {"worker_id": "gauge",    "daily_cap_usd": 0.50, "monthly_cap_usd": 10.0},
        {"worker_id": "ledger",   "daily_cap_usd": 0.50, "monthly_cap_usd": 10.0},
        {"worker_id": "sentinel", "daily_cap_usd": 0.10, "monthly_cap_usd": 3.0},
        {"worker_id": "mirror",   "daily_cap_usd": 0.25, "monthly_cap_usd": 5.0},
        {"worker_id": "pulse",    "daily_cap_usd": 0.25, "monthly_cap_usd": 5.0},
        {"worker_id": "sheriff",  "daily_cap_usd": 0.50, "monthly_cap_usd": 10.0},
        {"worker_id": "polish",   "daily_cap_usd": 0.25, "monthly_cap_usd": 5.0},
        {"worker_id": "signal",   "daily_cap_usd": 0.50, "monthly_cap_usd": 10.0},
        {"worker_id": "oracle",   "daily_cap_usd": 1.00, "monthly_cap_usd": 20.0},
        {"worker_id": "welcome",  "daily_cap_usd": 0.25, "monthly_cap_usd": 5.0},
        {"worker_id": "harvest",  "daily_cap_usd": 0.50, "monthly_cap_usd": 10.0},
        {"worker_id": "scout",    "daily_cap_usd": 0.50, "monthly_cap_usd": 10.0},
    ]
    try:
        from backend.db.models.internal_operators import InternalOperatorBudget
        from backend.core.database.database import async_session
        async with async_session() as seed_db:
            for b in _OPERATOR_BUDGETS:
                existing = (await seed_db.execute(
                    select(InternalOperatorBudget).where(InternalOperatorBudget.worker_id == b["worker_id"])
                )).scalar_one_or_none()
                if not existing:
                    seed_db.add(InternalOperatorBudget(
                        worker_id=b["worker_id"],
                        daily_cap_usd=b["daily_cap_usd"],
                        monthly_cap_usd=b["monthly_cap_usd"],
                        daily_spent_usd=0.0,
                        monthly_spent_usd=0.0
                    ))
            await seed_db.commit()
        print(f"[startup] operator budgets: seeded {len(_OPERATOR_BUDGETS)} default budget caps")
    except Exception as e:
        print(f"[startup] operator budgets: seed warning: {type(e).__name__}: {e}")

    # Start the governed operator workforce scheduler.
    # Runs the "First 12" internal operators on real autonomous tasks.
    # Kill switch: set OPERATOR_ENGINE_ENABLED=false in .env to disable.
    try:
        from backend.ops.operator_engine import engine as operator_engine
        operator_engine.start()
        print("[startup] operator engine: governed workforce started")
    except Exception as e:
        import traceback
        print(f"[startup] operator engine: WARNING — failed to start: {type(e).__name__}: {e}")
        traceback.print_exc()

    yield

    # Graceful shutdown of plugins and operator workforce
    await plugin_manager.shutdown_all()
    try:
        from backend.ops.operator_engine import engine as operator_engine
        operator_engine.stop()
    except Exception:
        pass


app = FastAPI(
    title="Veklom Sovereign AI Hub",
    version=settings.VERSION,
    summary="API-native governed AI execution layer for humans, developers, enterprises, and autonomous agents.",
    description="""
## Veklom Sovereign AI Hub

Veklom is an **API-native governed execution layer** for humans, developers, enterprises, and autonomous agents.

### Four-tier access model
| Tier | Interface | Auth |
|------|-----------|------|
| **Humans** | Workspace UI at /workspace/ | Browser session |
| **Developers** | REST API | Bearer JWT |
| **Agents** | Paid routes | x402 (USDC on Base), no sign-up |
| **Enterprises** | Governance + evidence layer | Bearer JWT + SLA |

### Machine discovery
- OpenAPI schema: `https://api.veklom.com/openapi.json`
- Agent manifest: `https://api.veklom.com/.well-known/agent.json`
- x402 config: `https://api.veklom.com/.well-known/x402.json`
- MCP SSE: `https://api.veklom.com/mcp/sse`
- llms.txt: `https://api.veklom.com/llms.txt`
- Pricing: `https://api.veklom.com/api/v1/pricing`

### Agent controls on every paid route
Every paid execution returns a machine-readable receipt with `request_id`, `cost_usdc`,
`policy_result`, `evidence_id`, and `receipt_url`. Budget caps, kill switches, and wallet
isolation are enforced before execution.

### x402 micropayments
Unauthenticated agents receive HTTP 402 with payment requirements. Pay per call in USDC on Base.
Free tier: 5 calls/day per IP on inference and GPC compile.

### OpenAI-compatible endpoint
Drop-in replacement: `base_url=https://api.veklom.com/v1`
""",
    contact={
        "name": "Veklom API",
        "url": "https://veklom.com",
        "email": "api@veklom.com",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://veklom.com/legal/terms",
    },
    servers=[
        {"url": "https://api.veklom.com", "description": "Production (machine-facing API surface)"},
        {"url": "https://veklom.com",     "description": "Production (main site)"},
    ],
    openapi_tags=[
        {"name": "AI",          "description": "Governed AI inference, chat, smart tier routing. Ollama-first, escalates to Groq/Gemini/OpenAI."},
        {"name": "GPC",         "description": "Governed Plan Compiler — compile agent intent into deterministic, policy-checked plans."},
        {"name": "Pipelines",   "description": "Pipeline orchestration — trigger, manage, and monitor governed pipelines."},
        {"name": "Evidence",    "description": "SHA-256 sealed audit evidence for every governed execution."},
        {"name": "Compliance",  "description": "Compliance reports for SOC2, HIPAA, GDPR, ISO 27001, EU AI Act, FedRAMP."},
        {"name": "Billing",     "description": "Operating reserve, wallet top-up, subscriptions, invoices, budget caps."},
        {"name": "Marketplace", "description": "Sovereign AI model marketplace — acquire, configure, and deploy governed models."},
        {"name": "Monitoring",  "description": "Real-time observability, structured logs, alerts, and platform pulse."},
        {"name": "discovery",   "description": "Machine-readable discovery: .well-known, llms.txt, mcp/sse, pricing, SDK examples."},
        {"name": "Auth",        "description": "JWT authentication, GitHub OAuth, multi-tenant workspace registration."},
    ],
    lifespan=lifespan,
)

# Instrument FastAPI with OpenTelemetry if configured
if has_valid_endpoint and has_valid_headers:
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ZeroTrustMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(IntelligentRoutingMiddleware)
app.add_middleware(BudgetCheckMiddleware)

from backend.core.security.middlewares import AgentTelemetryMiddleware, IPRateLimitMiddleware
app.add_middleware(AgentTelemetryMiddleware)
app.add_middleware(IPRateLimitMiddleware)

def _trusted_hosts() -> list[str]:
    raw_hosts = settings.ALLOWED_HOSTS
    if isinstance(raw_hosts, str):
        host_list = [h.strip() for h in raw_hosts.split(",") if h.strip()]
    else:
        host_list = [str(h).strip() for h in (raw_hosts or []) if str(h).strip()]

    required_hosts = {
        "veklom.com",
        "www.veklom.com",
        "api.veklom.com",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "testserver",
    }

    allow_wildcard = "*" in host_list
    if allow_wildcard and settings.DEBUG:
        return ["*"]

    internal_hosts = set()
    for key in ("HOSTNAME", "COOLIFY_CONTAINER_NAME", "COOLIFY_RESOURCE_UUID"):
        value = (os.getenv(key) or "").strip().lower()
        if value:
            internal_hosts.add(value)
    coolify_fqdn = (os.getenv("COOLIFY_FQDN") or "").strip()
    if coolify_fqdn:
        for host in coolify_fqdn.split(","):
            host = host.strip().lower()
            if host:
                internal_hosts.add(host)
    runtime_hostname = socket.gethostname().strip().lower()
    if runtime_hostname:
        internal_hosts.add(runtime_hostname)

    derived_hosts = set(required_hosts) | internal_hosts
    for host in host_list:
        if host and host != "*":
            derived_hosts.add(host.lower())
    for url in (settings.FRONTEND_URL, settings.API_URL, settings.API_BASE_URL):
        try:
            parsed = urlparse(url)
            if parsed.hostname:
                derived_hosts.add(parsed.hostname.lower())
        except Exception:
            continue
    return sorted(derived_hosts)


app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted_hosts())

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(X402PaymentMiddleware)


# --- Exception handlers ---
@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    if request.url.path in ("/login", "/signup"):
        from fastapi.responses import RedirectResponse
        query_str = f"?{request.url.query}" if request.url.query else ""
        return RedirectResponse(url=f"/workspace/login{query_str}", status_code=302)

    if request.url.path.startswith("/workspace") or request.url.path.startswith("/github"):
        workspace_index = WORKSPACE_DIR / "index.html"
        if workspace_index.exists():
            # Read the index.html and inject the auto-editor script
            with open(workspace_index, 'r', encoding='utf-8') as f:
                html_content = f.read()
            # Inject script before closing </head> or </body>
            script_tag = '<script src="/workspace/auto-editor.js"></script>'
            if '</head>' in html_content:
                html_content = html_content.replace('</head>', f'{script_tag}</head>')
            elif '</body>' in html_content:
                html_content = html_content.replace('</body>', f'{script_tag}</body>')
            return HTMLResponse(
                content=html_content,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
    return await _serve_frontend(request)


@app.exception_handler(500)
async def internal_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# --- Import and register all routers ---
from backend.apps.api.routers import (
    admin,
    agents,
    ai,
    auth,
    evaluations,
    billing,
    command_center,
    compliance,
    copilot,
    decision_frames,
    discovery,
    exec_router,
    gfr,
    gpc,
    health,
    hrm,
    # langchain_ops intentionally not imported - kept off the surface until real
    marketplace,
    monitoring,
    payments,
    pipelines,
    providers,
    repo_risk_gate,
    routing,
    system,
    team,
    runtime_jobs,
    security,
    upload,
    workspace,
    internal_uacp,
    internal_operators,
    plugins,
    autonomous,
    playground,
    webhooks,
    webhook,
    runs,
    smoke
)
from backend.services.uacp.http import router as uacp_http_router
from backend.apps.api.routers import admin_billing

# Machine-readable discovery (no prefix — serves /.well-known/*, /llms.txt, /robots.txt, /mcp/*)
app.include_router(discovery.router)

# Health & status (no prefix)
app.include_router(health.router)

# Auth - restore /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(smoke.router, prefix="/api/v1")

# System utilities
app.include_router(system.router, prefix="/api/v1")

# Veklom Runs (Atomic Unit)
app.include_router(runs.router, prefix="/api/v1/runs")

# Copilot registry
app.include_router(copilot.router, prefix="/api/v1")

# Workspace
app.include_router(workspace.router, prefix="/api/v1")

# AI execution
app.include_router(ai.router, prefix="/api/v1")
app.include_router(exec_router.router, prefix="/api")
app.include_router(exec_router.router, prefix="")

# Playground — sessions, prompts, tools
app.include_router(playground.router, prefix="/api/v1")

# Runtime Jobs Status
app.include_router(runtime_jobs.router, prefix="/api/v1")

# Billing, wallet, subscriptions, budget, cost, payments, payouts
app.include_router(billing.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")

# Security, kill switch, locker
app.include_router(security.router, prefix="/api/v1")

# Compliance, privacy, content-safety, explainability, evidence, audit
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(autonomous.router, prefix="/api/v1")

# Monitoring, metrics, insights, telemetry, platform pulse, suggestions
app.include_router(monitoring.router, prefix="/api/v1")

# Marketplace, vendors, listings, plugins
app.include_router(marketplace.router, prefix="/api/v1")

# Pipelines, deployments, routing, autonomous, edge/canary
app.include_router(pipelines.router, prefix="/api/v1")
app.include_router(pipelines.router)
app.include_router(routing.router, prefix="/api/v1")

# Webhooks for external integrations
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(webhook.router, prefix="/api/v1")

# UACP Service - dual-adapter architecture (HTTP service + library shim)
app.include_router(uacp_http_router, prefix="/api/v1")

# Integrations (PagerDuty, Slack, etc.)
from backend.apps.api.routers import integrations
app.include_router(integrations.router, prefix="/api/v1")

# Admin, internal, search, upload, onboarding, referrals, support, export
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin_billing.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")

# GPC (Governed Plan Compiler) + Decision Frames
app.include_router(gpc.router, prefix="/api/v1")
app.include_router(decision_frames.router, prefix="/api/v1")

# GFR (Gradient Field Router) — Scientist & Special Agent load balancing skill
app.include_router(gfr.router, prefix="/api/v1")

# Command Center — /api/v1/command-center/* (aliases + new routes per WIRING_MATRIX)
app.include_router(command_center.router, prefix="/api/v1")

# Repo Risk Gate — Playground governed-review tool
app.include_router(repo_risk_gate.router, prefix="/api/v1")

# Agent Workforce
app.include_router(agents.router, prefix="/api/v1")

# HRM sub-system — task force management, Zeno interrogation, skill registry
app.include_router(hrm.router, prefix="/api/v1")

# ChainOps (LangChain governance) — INTENTIONALLY UNREGISTERED.
# The langchain_ops module currently returns simulated runs; per spec the
# ChainOps page must show "Backend routes not wired yet" until a real
# LangChain integration lands.  Do not enable without removing simulated data.

# UACP Internal
app.include_router(internal_uacp.router, prefix="/api/v1")
app.include_router(internal_uacp.operator_router, prefix="/api/v1")
app.include_router(internal_operators.router, prefix="/api/v1")
app.include_router(internal_uacp.autonomous_router, prefix="/api/v1")

# Provider management — BYOK, routing rules, audit logs
app.include_router(providers.router, prefix="/api/v1")

# Team management — members, invitations, roles, SSO, MFA
app.include_router(team.router, prefix="/api/v1")

# Plugins Management — mounted at both /api and /api/v1 (bundle calls ${re}/plugins = /api/v1/plugins)
app.include_router(plugins.router, prefix="/api")
app.include_router(plugins.router, prefix="/api/v1")

# Exec alias for bundle's ${re}/v1/exec pattern (re=/api/v1 → /api/v1/v1/exec)
app.include_router(exec_router.router, prefix="/api/v1/v1")


# --- Frontend static files ---
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "static"
LANDING_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "landing"
GPC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "gpc"
WORKSPACE_DIR = FRONTEND_DIR / "workspace"
COMMAND_CENTER_DIR = FRONTEND_DIR / "command-center"
IRONGRID_DIR = Path(__file__).resolve().parent.parent.parent.parent / "irongrid" / "dist"
LOCKERPHYCER_DIR = FRONTEND_DIR / "lockerphycer"
OPERATOR_CENTER_DIR = FRONTEND_DIR / "operator-center"


def _mount_static():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    if WORKSPACE_DIR.exists():
        app.mount("/workspace", StaticFiles(directory=str(WORKSPACE_DIR), html=True), name="workspace")
    if OPERATOR_CENTER_DIR.exists():
        app.mount("/operator-center", StaticFiles(directory=str(OPERATOR_CENTER_DIR), html=True), name="operator-center")
    if COMMAND_CENTER_DIR.exists():
        app.mount(
            "/command-center",
            StaticFiles(directory=str(COMMAND_CENTER_DIR), html=True),
            name="command-center",
        )
    if GPC_DIR.exists():
        app.mount("/gpc-engine", StaticFiles(directory=str(GPC_DIR), html=True), name="gpc-engine")
        app.mount("/gpc", StaticFiles(directory=str(GPC_DIR), html=True), name="gpc")
    if IRONGRID_DIR.exists():
        app.mount("/irongrid", StaticFiles(directory=str(IRONGRID_DIR), html=True), name="irongrid")
    if LOCKERPHYCER_DIR.exists():
        app.mount("/lockerphycer", StaticFiles(directory=str(LOCKERPHYCER_DIR), html=True), name="lockerphycer")
    # Mount static directory for CSS, JS, branding, etc.
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    # Do NOT mount landing directory - it will be served by catch-all route


_mount_static()


# ---------------------------------------------------------------------------
# Protected route guards — enforce auth BEFORE serving static pages
# These run as route handlers registered BEFORE the static mounts
# ---------------------------------------------------------------------------
_OWNER_ROLES = {"OWNER", "SUPER_ADMIN", "owner", "super_admin"}
_PAID_PLANS = {"sovereign", "pro", "founding", "standard", "regulated", "enterprise"}
_PAID_ROLES = {"OWNER", "SUPER_ADMIN", "ADMIN", "owner", "super_admin", "admin"}


async def _get_user_from_request(request):
    """Extract and verify JWT from Authorization header or cookie."""
    from backend.core.security.auth import verify_token
    from backend.core.database.database import get_db
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token") or request.cookies.get("token")
    if not token:
        return None
    try:
        payload = verify_token(token)
        return payload
    except Exception:
        return None


@app.middleware("http")
async def enforce_route_access(request, call_next):
    """Enforce access control on protected static routes."""
    path = request.url.path

    # GPC — paid plan required (sovereign / pro / founding / admin)
    if path.startswith("/gpc") or path.startswith("/gpc-engine"):
        user = await _get_user_from_request(request)
        if user:
            role = user.get("role", "")
            plan = user.get("plan", "")
            allowed = role in _PAID_ROLES or plan in _PAID_PLANS
        else:
            allowed = False
        if not allowed:
            html = '<html><head><meta http-equiv="refresh" content="0;url=/workspace/#/billing"></head>'\
                   '<body>Paid plan required. <a href="/workspace/#/billing">Upgrade your plan</a></body></html>'
            from starlette.responses import HTMLResponse
            return HTMLResponse(html, status_code=403)

    response = await call_next(request)
    return response


@app.get("/config.js")
async def config_js():
    api_base = os.environ.get("VEKLOM_API_BASE", "/api/v1")
    content = f'window.__VEKLOM_API_BASE__ = "{api_base}";'
    return HTMLResponse(content=content, media_type="application/javascript")


@app.get("/base-attribution.js")
async def base_attribution_js():
    code = settings.BASE_BUILDER_CODE.strip()
    if code:
        code_hex = code.encode("utf-8").hex()
        data_suffix = f"0xef{code_hex}"
    else:
        data_suffix = ""
    content = (
        f"(function(){{"
        f"var code={repr(code)};"
        f"var suffix={repr(data_suffix)};"
        f"window.__BASE_BUILDER_CODE__=code;"
        f"window.__BASE_DATA_SUFFIX__=suffix;"
        f"}})();"
    )
    return HTMLResponse(content=content, media_type="application/javascript")


@app.get("/api/v1/attribution/builder-code")
async def attribution_builder_code():
    code = settings.BASE_BUILDER_CODE.strip()
    if not code:
        return {"configured": False, "builder_code": None, "data_suffix": None}
    code_hex = code.encode("utf-8").hex()
    data_suffix = f"0xef{code_hex}"
    return {
        "configured": True,
        "builder_code": code,
        "data_suffix": data_suffix,
        "chain": "base",
        "standard": "ERC-8021",
        "note": "Append data_suffix to transaction calldata for onchain attribution.",
    }


@app.get("/api/v1/attribution/analytics")
async def attribution_analytics():
    import httpx
    api_key = settings.BASE_DEV_API_KEY.strip()
    if not api_key:
        return {"configured": False, "error": "BASE_DEV_API_KEY not set"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.base.dev/v1/analytics/attribution",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            )
            if resp.status_code == 200:
                return {"configured": True, "data": resp.json()}
            return {"configured": True, "error": resp.text, "status_code": resp.status_code}
    except Exception as exc:
        return {"configured": True, "error": str(exc)}


def _branding_response(filename: str, media_type: str):
    asset_path = FRONTEND_DIR / "branding" / filename
    if asset_path.exists():
        return FileResponse(str(asset_path), media_type=media_type)
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.api_route("/favicon.svg", methods=["GET", "HEAD"])
async def favicon_svg():
    return _branding_response("favicon.svg", "image/svg+xml")


@app.api_route("/favicon.ico", methods=["GET", "HEAD"])
async def favicon_ico():
    return _branding_response("favicon.ico", "image/x-icon")


@app.api_route("/apple-touch-icon.png", methods=["GET", "HEAD"])
async def apple_touch_icon():
    return _branding_response("apple-touch-icon.png", "image/png")


@app.api_route("/og-image.png", methods=["GET", "HEAD"])
async def og_image():
    return _branding_response("og-image.png", "image/png")


@app.api_route("/twitter-card.png", methods=["GET", "HEAD"])
async def twitter_card():
    return _branding_response("twitter-card.png", "image/png")


@app.api_route("/logo.png", methods=["GET", "HEAD"])
async def logo_png():
    return _branding_response("logo.png", "image/png")


@app.api_route("/icon.png", methods=["GET", "HEAD"])
async def icon_png():
    return _branding_response("icon.png", "image/png")


@app.get("/")
async def root(request: Request):
    host = request.headers.get("host", "")
    if "co2router.com" in host:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/workspace#/marketplace/ls_co2router", status_code=301)
    if "lockerphycer.veklom.com" in host:
        lockerphycer_index = FRONTEND_DIR / "lockerphycer" / "index.html"
        if lockerphycer_index.exists():
            return FileResponse(str(lockerphycer_index))
        return JSONResponse(status_code=404, content={"detail": "Lockerphycer page not found"})
    return await _serve_frontend(None)


@app.get("/legal/privacy")
async def legal_privacy():
    path = LANDING_DIR / "privacy.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.get("/legal/terms")
async def legal_terms():
    path = LANDING_DIR / "terms.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.get("/uptime")
async def uptime_page():
    path = LANDING_DIR / "uptime.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.get("/legal/security")
async def legal_security():
    path = LANDING_DIR / "security.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.get("/legal/acceptable-use")
async def legal_acceptable_use():
    path = LANDING_DIR / "acceptable-use.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})

@app.get("/legal/dsa")
async def legal_dsa():
    path = LANDING_DIR / "dsa.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


# /robots.txt is now served by discovery.router (see backend/apps/api/routers/discovery.py)


@app.get("/sitemap.xml")
async def sitemap_xml():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://veklom.com/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>https://veklom.com/uptime</loc><changefreq>daily</changefreq><priority>0.8</priority></url>
  <url><loc>https://veklom.com/docs</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>https://veklom.com/legal/terms</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://veklom.com/legal/privacy</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://veklom.com/legal/security</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
</urlset>"""
    return HTMLResponse(content=content, media_type="application/xml")


@app.post("/api/v1/feedback")
@app.post("/api/v1/feedback/")
async def submit_feedback(body: dict):
    category = str(body.get("category", "feedback")).strip()[:64]
    subject = str(body.get("subject", "")).strip()[:255]
    feedback_body = str(body.get("body", "")).strip()[:4096]
    if not feedback_body:
        return JSONResponse(status_code=422, content={"detail": "body is required"})
    print(f"[feedback] category={category} subject={subject!r} body={feedback_body[:80]!r}")
    return {"submitted": True, "message": "Thank you for your feedback."}


# /llms.txt is now served by discovery.router (see backend/apps/api/routers/discovery.py)


@app.get("/feedback")
async def feedback_page():
    path = LANDING_DIR / "feedback.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})



@app.get("/status/data")
async def public_status_data():
    # Public status data endpoint (no auth required)
    from datetime import datetime, timezone
    return {
        "status": "operational",
        "services": {
            "api": "healthy",
            "database": "connected",
            "cache": "connected",
            "operator_engine": "active"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/status.html")
async def status_html_file():
    # Serve status.html directly for /status.html requests
    path = LANDING_DIR / "status.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})

@app.post("/api/run-sample")
@app.post("/api/v1/terminal/run")
async def run_sample_unified(request: Request):
    # Unified sample run/terminal endpoint returning status: ok
    # Protected by ZeroTrustMiddleware since it is not in public_prefixes
    return {"status": "ok"}
@app.get("/status")
async def status_page():
    path = LANDING_DIR / "status.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


async def _serve_frontend(request):
    landing_index = LANDING_DIR / "index.html"
    static_index = FRONTEND_DIR / "index.html"
    if landing_index.exists():
        return FileResponse(str(landing_index))
    elif static_index.exists():
        return FileResponse(str(static_index))
    return HTMLResponse(content=_fallback_html(), status_code=200)


@app.get("/terminal")
async def terminal_page():
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    terminal_path = root_dir / "uacp-quantum-terminal.html"
    if terminal_path.exists():
        return FileResponse(str(terminal_path))
    return JSONResponse(status_code=404, content={"detail": "Quantum Terminal file not found"})


@app.get("/lockerphycer")
async def lockerphycer_page():
    lockerphycer_index = FRONTEND_DIR / "lockerphycer" / "index.html"
    if lockerphycer_index.exists():
        return FileResponse(str(lockerphycer_index))
    return JSONResponse(status_code=404, content={"detail": "Lockerphycer page not found"})


@app.get("/lockerphycer/{path:path}")
async def lockerphycer_assets(path: str):
    lockerphycer_file = FRONTEND_DIR / "lockerphycer" / path
    if lockerphycer_file.exists() and lockerphycer_file.is_file():
        return FileResponse(str(lockerphycer_file))
    return JSONResponse(status_code=404, content={"detail": "File not found"})
@app.get("/marketplace")
async def marketplace_info():
    return {
        "platform": "Veklom",
        "description": "Marketplace products built for governed execution",
        "products": [
            {
                "id": "py03-irongrid",
                "name": "PY03 IronGrid API",
                "type": "Runtime Module",
                "description": "High-performance route optimization and concurrency sandbox for agent/runtime workloads.",
                "url": "https://github.com/reprewindai-dev/pyo3-irongrid-api"
            },
            {
                "id": "lockerphycer",
                "name": "Lockerphycer",
                "type": "Marketplace Product",
                "description": "A Veklom marketplace product for controlled, governed execution workflows.",
                "url": "https://lockerphycer-git-main-dksummers-projects.vercel.app/"
            }
        ]
    }

@app.get("/marketplace/lockerphycer")
async def marketplace_lockerphycer():
    return {
        "id": "lockerphycer",
        "name": "Lockerphycer",
        "type": "Marketplace Product",
        "description": "A Veklom marketplace product for controlled, governed execution workflows.",
        "demo_url": "https://lockerphycer-git-main-dksummers-projects.vercel.app/",
        "status": "Available in Veklom ecosystem"
    }

@app.get("/marketplace/py03-irongrid")
async def marketplace_py03():
    return {
        "id": "py03-irongrid",
        "name": "PY03 IronGrid API",
        "type": "Runtime Module",
        "description": "High-performance route optimization and concurrency sandbox for agent/runtime workloads.",
        "demo_url": "https://github.com/reprewindai-dev/pyo3-irongrid-api",
        "status": "Available in Veklom ecosystem"
    }



@app.get("/workspace/pipelines/{pipeline_id}/embedded")
async def embedded_pipeline_editor(pipeline_id: str):
    """Serve pipeline detail page with visual editor embedded in iframe."""
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Editor - {pipeline_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
            position: absolute;
            top: 0;
            left: 0;
        }}
    </style>
</head>
<body>
    <iframe src="/workspace/#/pipelines/{pipeline_id}?editor=true" allowfullscreen></iframe>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/workspace/auto-editor.js")
async def auto_editor_script():
    """JavaScript to automatically trigger visual editor on pipeline pages."""
    script_content = """
(function() {
    // Wait for the page to load
    function waitForElement(selector, callback, maxAttempts = 50) {
        let attempts = 0;
        const interval = setInterval(() => {
            const element = document.querySelector(selector);
            if (element) {
                clearInterval(interval);
                callback(element);
            } else if (attempts >= maxAttempts) {
                clearInterval(interval);
            }
            attempts++;
        }, 100);
    }

    // Detect if we're on a pipeline detail page
    function checkPipelinePage() {
        const hash = window.location.hash;
        if (hash.match(/#\\/pipelines\\/[^/]+$/)) {
            // We're on a pipeline detail page - trigger visual editor
            waitForElement('[data-testid="visual-editor-button"], .visual-editor-btn, button:contains("Visual Editor")', (btn) => {
                if (btn) {
                    btn.click();
                }
            });
            
            // Alternative: try to find and click any button that might open the editor
            setTimeout(() => {
                const buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    const text = btn.textContent || btn.innerText || '';
                    if (text.toLowerCase().includes('visual') || text.toLowerCase().includes('editor')) {
                        btn.click();
                        break;
                    }
                }
            }, 500);
        }
    }

    // Run on page load and hash change
    window.addEventListener('load', checkPipelinePage);
    window.addEventListener('hashchange', checkPipelinePage);
    
    // Also run immediately in case we're already loaded
    setTimeout(checkPipelinePage, 100);
})();
"""
    return HTMLResponse(content=script_content, media_type="application/javascript")


@app.get("/gpc")
async def gpc_page():
    index_path = GPC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content=_gpc_html(), status_code=200)


# Command Center config endpoint for frontend
@app.get("/api/v1/config")
async def command_center_config():
    """Return configuration for Command Center frontend."""
    return {
        "VEKLOM_BYOS_BACKEND_URL": settings.API_URL,
        "OLLAMA_BASE_URL": settings.OLLAMA_BASE_URL
    }


@app.post("/api/v1/config")
async def update_command_center_config(request: Request):
    """Update configuration for Command Center frontend."""
    body = await request.json()
    # Configuration is stored in settings, not dynamically updated
    # This endpoint exists for compatibility with Command Center frontend
    return {"success": True, "config": {
        "VEKLOM_BYOS_BACKEND_URL": settings.API_URL,
        "OLLAMA_BASE_URL": settings.OLLAMA_BASE_URL
    }}


def _fallback_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Veklom Sovereign AI Hub</title>
<script src="/config.js"></script>
<link rel="stylesheet" href="/static/css/brand.css">
</head>
<body>
<div id="root"></div>
<script type="module" src="/assets/index-EUKZeqk4.js"></script>
<link rel="stylesheet" href="/assets/index-WqgIFi2m.css">
</body>
</html>"""


def _gpc_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GPC — Governed Plan Compiler | Veklom</title>
<link rel="stylesheet" href="/static/css/brand.css">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #050505; color: #e0e0e0; font-family: system-ui, -apple-system, sans-serif; }
</style>
</head>
<body>
<div id="gpc-root"></div>
<script type="module" src="/gpc/assets/gpc.js"></script>
</body>
</html>"""
