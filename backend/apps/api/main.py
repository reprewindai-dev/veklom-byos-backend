"""Veklom BYOS Backend — Main FastAPI Application.

Source of truth: LockerPhycer backend routes + API_SURFACE.md.
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


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
    gpc,
    health,
    marketplace,
    monitoring,
    pipelines,
    security,
    workspace,
)

# Health & status (no prefix)
app.include_router(health.router)

# Auth
app.include_router(auth.router, prefix="/api/v1")

# Workspace
app.include_router(workspace.router, prefix="/api/v1")

# AI execution
app.include_router(ai.router, prefix="/api/v1")
app.include_router(exec_router.router, prefix="/api")

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

# Admin, internal, search, upload, onboarding, referrals, support, export
app.include_router(admin.router, prefix="/api/v1")

# GPC (Governed Plan Compiler)
app.include_router(gpc.router, prefix="/api/v1")


# --- Frontend static files ---
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "static"


def _mount_static():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


_mount_static()


@app.get("/config.js")
async def config_js():
    api_base = os.environ.get("VEKLOM_API_BASE", "/api/v1")
    content = f'window.__VEKLOM_API_BASE__ = "{api_base}";'
    return HTMLResponse(content=content, media_type="application/javascript")


@app.get("/")
async def root():
    return await _serve_frontend(None)


async def _serve_frontend(request):
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content=_fallback_html(), status_code=200)


# GPC page
@app.get("/gpc")
async def gpc_page():
    gpc_dir = FRONTEND_DIR.parent / "gpc"
    index_path = gpc_dir / "index.html"
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
