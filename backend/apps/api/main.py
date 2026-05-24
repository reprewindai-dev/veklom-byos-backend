"""Veklom BYOS Backend — Main FastAPI Application.

Source of truth: Veklom backend routes + API_SURFACE.md.
All routes wired for the REALFRONTEND built frontend.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.core.config.settings import settings
from backend.core.database.database import Base, engine
from backend.core.plugins.manager import plugin_manager

# Import model package to ensure tables are registered with Base.metadata.
import backend.db.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Discover available plugins on startup
    await plugin_manager.discover_plugins()
    
    # Initialize database schema
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Database schema initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        # Continue anyway - tables might already exist
    
    yield
    
    # Graceful shutdown of plugins
    await plugin_manager.shutdown_all()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

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


# --- Exception handlers ---
@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    if request.url.path.startswith("/workspace") or request.url.path.startswith("/login") or request.url.path.startswith("/github"):
        workspace_index = WORKSPACE_DIR / "index.html"
        if workspace_index.exists():
            return FileResponse(str(workspace_index))
    return await _serve_frontend(request)


@app.exception_handler(500)
async def internal_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# --- Import and register all routers ---
from backend.apps.api.routers import (
    admin,
    ai,
    auth,
    billing,
    compliance,
    exec_router,
    gfr,
    gpc,
    health,
    marketplace,
    monitoring,
    pipelines,
    routing,
    runtime_jobs,
    security,
    upload,
    workspace,
    internal_uacp,
    internal_operators,
    plugins,
)

# Health & status (no prefix)
app.include_router(health.router)

# Auth - restore /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")

# Workspace
app.include_router(workspace.router, prefix="/api/v1")

# AI execution
app.include_router(ai.router, prefix="/api/v1")
app.include_router(exec_router.router, prefix="/api")
app.include_router(exec_router.router, prefix="/api/v1")

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

# UACP Internal
app.include_router(internal_uacp.router, prefix="/api/v1")
app.include_router(internal_uacp.operator_router, prefix="/api/v1")
app.include_router(internal_operators.router, prefix="/api/v1")
app.include_router(internal_uacp.autonomous_router, prefix="/api/v1")

# Plugins Management
app.include_router(plugins.router, prefix="/api")


# --- Frontend static files ---
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "static"
LANDING_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "landing"
GPC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "gpc"
WORKSPACE_DIR = FRONTEND_DIR / "workspace"
COMMAND_CENTER_DIR = FRONTEND_DIR / "command-center"


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
async def root():
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
