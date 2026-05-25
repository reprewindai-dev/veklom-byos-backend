"""Veklom BYOS Backend — Main FastAPI Application.

Source of truth: Veklom backend routes + API_SURFACE.md.
All routes wired for the REALFRONTEND built frontend.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

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

from backend.core.config.settings import settings
from backend.core.database.database import Base, engine
from backend.core.plugins.manager import plugin_manager
from backend.core.security.middleware import SecurityHeadersMiddleware

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
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
OTEL_HEADERS = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
if OTEL_ENDPOINT and OTEL_HEADERS:
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
            critical = ("users", "exec_logs", "audit_logs", "workspaces", "repo_risk_gate_runs", "agents")
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

    yield

    # Graceful shutdown of plugins
    await plugin_manager.shutdown_all()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Instrument FastAPI with OpenTelemetry if configured
if OTEL_ENDPOINT and OTEL_HEADERS:
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

if settings.APP_ENV == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

app.add_middleware(SecurityHeadersMiddleware)


# --- Exception handlers ---
@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    if request.url.path.startswith("/workspace") or request.url.path.startswith("/login") or request.url.path.startswith("/github"):
        workspace_index = WORKSPACE_DIR / "index.html"
        if workspace_index.exists():
            return FileResponse(
                str(workspace_index),
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
    billing,
    command_center,
    compliance,
    copilot,
    exec_router,
    gfr,
    gpc,
    health,
    hrm,
    # langchain_ops intentionally not imported - kept off the surface until real
    marketplace,
    monitoring,
    pipelines,
    providers,
    repo_risk_gate,
    routing,
    sys,
    team,
    runtime_jobs,
    security,
    upload,
    workspace,
    internal_uacp,
    internal_operators,
    plugins,
    playground,
)

# Health & status (no prefix)
app.include_router(health.router)

# Auth - restore /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")

# System utilities
app.include_router(sys.router, prefix="/api/v1")

# Copilot registry
app.include_router(copilot.router, prefix="/api/v1")

# Workspace
app.include_router(workspace.router, prefix="/api/v1")

# AI execution
app.include_router(ai.router, prefix="/api/v1")
app.include_router(exec_router.router, prefix="/api")
app.include_router(exec_router.router, prefix="/api/v1")

# Playground — sessions, prompts, tools
app.include_router(playground.router, prefix="/api/v1")

# Runtime Jobs Status
app.include_router(runtime_jobs.router, prefix="/api/v1")

# Billing, wallet, subscriptions, budget, cost, payments, payouts
app.include_router(billing.router, prefix="/api/v1")

# Security, kill switch, locker
app.include_router(security.router, prefix="/api/v1")

# Compliance, privacy, content-safety, explainability, evidence, audit
app.include_router(compliance.router, prefix="/api/v1")

# Monitoring, metrics, insights, telemetry, platform pulse, suggestions
app.include_router(monitoring.router, prefix="/api/v1")

# Marketplace, vendors, listings, plugins
app.include_router(marketplace.router, prefix="/api/v1")

# Pipelines, deployments, routing, autonomous, edge/canary
app.include_router(pipelines.router, prefix="/api/v1")
app.include_router(pipelines.router)
app.include_router(routing.router, prefix="/api/v1")

# Admin, internal, search, upload, onboarding, referrals, support, export
app.include_router(admin.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")

# GPC (Governed Plan Compiler)
app.include_router(gpc.router, prefix="/api/v1")

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


def _mount_static():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    if WORKSPACE_DIR.exists():
        app.mount("/workspace", StaticFiles(directory=str(WORKSPACE_DIR), html=True), name="workspace")
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
    # Mount static directory for CSS, JS, branding, etc.
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    # Do NOT mount landing directory - it will be served by catch-all route


_mount_static()


@app.get("/config.js")
async def config_js():
    api_base = os.environ.get("VEKLOM_API_BASE", "/api/v1")
    content = f'window.__VEKLOM_API_BASE__ = "{api_base}";'
    return HTMLResponse(content=content, media_type="application/javascript")


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


@app.get("/robots.txt")
async def robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /workspace/\n\n"
        "Sitemap: https://veklom.com/sitemap.xml\n"
    )
    return HTMLResponse(content=content, media_type="text/plain")


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


@app.get("/llms.txt")
async def llms_txt():
    """llms.txt endpoint for AI model discovery and documentation."""
    llms_content = """# Veklom AI Model Support

Veklom supports multiple AI model providers through its governed execution layer. All models are routed through policy gates before execution.

## Supported Providers

### Ollama (Primary)
- Base URL: http://127.0.0.1:11434
- Default Model: qwen2.5:3b
- Autostart: Enabled
- Description: Local-first execution for maximum sovereignty

### Groq (Fallback)
- Base URL: https://api.groq.com/openai/v1
- Default Model: llama-3.1-8b-instant
- Description: High-performance hosted inference

### Hugging Face (Fallback)
- Base URL: https://router.huggingface.co/v1
- Default Model: meta-llama/Llama-3.1-8B-Instruct:fastest
- Description: Open-source model hub

## Model Capabilities

- Text generation and completion
- Code generation and analysis
- Document processing and extraction
- Compliance checking and policy evaluation
- Audit trail generation

## Governance Features

- Policy-before-provider architecture
- Real-time cost controls and spend caps
- Signed audit evidence for all executions
- BYOK (Bring Your Own Key) support
- Automatic redaction and PII protection

## Documentation

- API Documentation: https://veklom.com/docs
- Security Policy: https://veklom.com/legal/security
- Privacy Policy: https://veklom.com/legal/privacy
- Terms of Service: https://veklom.com/legal/terms

## Contact

- Email: founder@company.com
- Website: https://veklom.com
"""
    return HTMLResponse(content=llms_content, media_type="text/plain")


@app.get("/feedback")
async def feedback_page():
    path = LANDING_DIR / "feedback.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


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



@app.get("/gpc")
async def gpc_page():
    index_path = GPC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content=_gpc_html(), status_code=200)


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
