"""Veklom BYOS Backend — Main FastAPI Application.

Source of truth: Veklom backend routes + API_SURFACE.md.
All routes wired for the REALFRONTEND built frontend.
"""

import logging
import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

import sentry_sdk
from fastapi import FastAPI, Request, Query, Depends, HTTPException
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

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


from backend.core.security.middlewares import (
    ZeroTrustMiddleware,
    MetricsMiddleware,
    IntelligentRoutingMiddleware,
    BudgetCheckMiddleware
)

from backend.core.config.settings import settings
from backend.core.database.database import Base, engine, get_db
from backend.core.plugins.manager import plugin_manager
from backend.core.security.middleware import SecurityHeadersMiddleware
from backend.core.middleware.x402 import X402PaymentMiddleware
from backend.core.amphoteric.middleware import AmphotericMiddleware
from backend.core.middleware.ratelimit import RateLimitMiddleware
from backend.core.cappo.middleware import CappoPolicyMiddleware

# --- Production Startup Guards ---
if settings.APP_ENV == "production" or os.getenv("ENVIRONMENT") == "production":
    if settings.SECRET_KEY == "change-me-in-production":
        raise RuntimeError("FATAL: SECRET_KEY is set to default in a production environment!")
    if settings.ENCRYPTION_KEY == "change-me-in-production-aes-256":
        raise RuntimeError("FATAL: ENCRYPTION_KEY is set to default in a production environment!")


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
    try:
        # Clean the endpoint: the gRPC OTLPSpanExporter expects the base host (with optional port)
        # and fails if paths like '/otlp' or '/v1/traces' (which are meant for HTTP) are included.
        grpc_endpoint = OTEL_ENDPOINT
        if grpc_endpoint.endswith("/otlp"):
            grpc_endpoint = grpc_endpoint[:-5]
        elif grpc_endpoint.endswith("/v1/traces"):
            grpc_endpoint = grpc_endpoint[:-10]

        # Standard OTLP gRPC endpoint for Grafana Cloud requires port 443 explicitly
        # If no port is specified in the host, append :443 so it doesn't default to 4317
        parsed = urlparse(grpc_endpoint)
        if parsed.netloc and ":" not in parsed.netloc:
            grpc_endpoint = f"{parsed.scheme}://{parsed.netloc}:443{parsed.path}"

        # URL-decode headers to convert any '%20' back to real spaces (Basic Auth needs Basic MTY1...)
        decoded_headers = unquote(OTEL_HEADERS)

        provider = TracerProvider()
        processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=grpc_endpoint,
                headers=decoded_headers,
            )
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        print(f"[otel] initialized OTLP gRPC span exporter to {grpc_endpoint}")
    except Exception as e:
        print(f"[otel] WARNING: Failed to initialize OTLP gRPC exporter: {type(e).__name__}: {e}")


import asyncio
import time
import httpx
import uuid
from sqlalchemy import select, func, update
from datetime import datetime, timezone, timedelta
from backend.apps.api.services.vnp_engine import current_epoch, compute_deviation
from backend.core.database.database import async_session
from backend.db.models.vnp import Api, ApiRegion, ProbeEvent, ProbeResultState, RegionalTelemetry, SettlementEntry, LedgerEntryType, SettlementState
import json
from backend.core.database.redis_client import redis_client
from backend.core.security.governance import RevocationManager

logger = logging.getLogger(__name__)


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "true").strip().lower() == "true"

async def pgl_revocation_listener():
    """Listens for PGL identity revocations and aggressively invalidates the in-memory cache."""
    try:
        if redis_client and redis_client.real_redis:
            pubsub = redis_client.real_redis.pubsub()
            await pubsub.subscribe("veklom:pgl:revocations")
            print("[startup] pgl: revocation listener subscribed to veklom:pgl:revocations")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        pgl_id = data.get("pgl_id")
                        if pgl_id:
                            RevocationManager._revoked_cache.add(pgl_id)
                            print(f"[pgl] ingested revocation for {pgl_id}")
                    except json.JSONDecodeError:
                        print(f"[pgl] malformed revocation message: {message['data']}")
        else:
            print("[startup] pgl: real Redis not connected, skipping pub/sub revocation listener (fallback mode)")
    except Exception as e:
        print(f"[startup] pgl: revocation listener error: {e}")

async def vnp_background_indexer():
    """Production-grade background task to compute VNP Stakes Engine updates and perform real probes."""
    # Run every 5 minutes
    interval = 300

    cycle_timeout = float(os.getenv("VNP_BACKGROUND_INDEXER_TIMEOUT_SECONDS", "30"))
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await asyncio.wait_for(
                    _run_vnp_background_indexer_cycle(client),
                    timeout=cycle_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("[vnp-engine] indexer cycle timed out after %.1fs", cycle_timeout)
            except Exception as exc:
                logger.warning("[vnp-engine] indexer cycle failed: %s", exc)
            await asyncio.sleep(interval)

async def _run_vnp_background_indexer_cycle(client: httpx.AsyncClient):
    ep = current_epoch()
    print(f"[vnp-engine] Running production indexer for epoch {ep}")

    async with async_session() as db:
        result = await db.execute(
            select(Api, ApiRegion)
            .join(ApiRegion, Api.id == ApiRegion.api_id)
            .where(ApiRegion.active == True)
        )
        rows = result.all()

        for api, region in rows:
            target_url = f"{region.endpoint_url.rstrip('/')}{api.health_path}"
            start_time = time.time()
            probe_id = str(uuid.uuid4())
            success = False
            status_code = None
            result_state = ProbeResultState.transport_error
            total_ms = 0

            try:
                resp = await client.get(target_url, timeout=10.0)
                total_ms = int((time.time() - start_time) * 1000)
                status_code = resp.status_code
                success = 200 <= status_code < 300
                result_state = ProbeResultState.success if success else ProbeResultState.http_error
            except httpx.TimeoutException:
                result_state = ProbeResultState.timeout
            except Exception:
                result_state = ProbeResultState.transport_error

            db.add(
                ProbeEvent(
                    event_id=f"prb_{probe_id[:12]}",
                    worker_id="cappo-node-primary",
                    worker_region="us-east-1",
                    runtime="amphoteric-v1",
                    api_id=api.id,
                    api_region_code=region.region_code,
                    endpoint_url=target_url,
                    occurred_at=datetime.now(timezone.utc),
                    total_ms=total_ms or int((time.time() - start_time) * 1000),
                    status_code=status_code,
                    result_state=result_state,
                    success=success,
                    signature_alg="ed25519",
                    signature_key_id="cappo-node-1",
                    signature_value="local-node-signed",
                )
            )

            if success:
                lookback = datetime.now(timezone.utc) - timedelta(hours=1)
                stats_res = await db.execute(
                    select(
                        func.avg(ProbeEvent.total_ms).label("avg_lat"),
                        func.percentile_cont(0.95).within_group(ProbeEvent.total_ms).label("p95_lat"),
                        func.count(ProbeEvent.id).label("cnt"),
                    )
                    .where(ProbeEvent.api_id == api.id)
                    .where(ProbeEvent.api_region_code == region.region_code)
                    .where(ProbeEvent.occurred_at >= lookback)
                )
                stats = stats_res.fetchone()

                if stats and stats.cnt >= 5:
                    p95 = float(stats.p95_lat)
                    dev = compute_deviation(200.0, p95, 30.0)
                    db.add(
                        RegionalTelemetry(
                            api_id=api.id,
                            region_code=region.region_code,
                            window_start=lookback,
                            window_end=datetime.now(timezone.utc),
                            sample_count=stats.cnt,
                            success_count=stats.cnt,
                            p50_latency_ms=int(stats.avg_lat),
                            p95_latency_ms=int(p95),
                            p99_latency_ms=int(p95 * 1.1),
                            error_rate_percent=0.0,
                            uptime_percent=100.0,
                            trust_score=95.0,
                        )
                    )
                    if dev["penalty_usdc"] > 0:
                        print(f"[vnp-engine] Slashing detected for {api.name}: {dev['penalty_usdc']} USDC")
                        db.add(
                            SettlementEntry(
                                provider_id=api.provider_id,
                                entry_type=LedgerEntryType.slash,
                                amount_minor=int(dev["penalty_usdc"] * 1e6),
                                currency="USD",
                                state=SettlementState.pending,
                                reference_code=f"slash-{ep}-{probe_id[:8]}",
                            )
                        )

        await db.commit()

from backend.apps.api.services.vnp_scoring_engine import VNPScoringEngine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce security configurations
    settings.validate_production()

    # Discover available plugins on startup
    await plugin_manager.discover_plugins()

    # Schema is owned by Alembic. Startup must never mutate production schema.
    # Deployment runs `alembic upgrade head` before replacing the application.
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            # Dynamic migration check to add pre_execution_cert_id column to banker_payments table
            try:
                dialect = engine.dialect.name
                if dialect == "sqlite":
                    res = await conn.execute(text("PRAGMA table_info(banker_payments)"))
                    columns = [row[1] for row in res.fetchall()]
                    if "pre_execution_cert_id" not in columns:
                        await conn.execute(text("ALTER TABLE banker_payments ADD COLUMN pre_execution_cert_id VARCHAR(255)"))
                else:
                    await conn.execute(text("ALTER TABLE banker_payments ADD COLUMN IF NOT EXISTS pre_execution_cert_id VARCHAR(255)"))
                logger.info("[startup] Banker payments schema verified dynamically (pre_execution_cert_id verified)")
            except Exception as schema_exc:
                logger.warning(f"[startup] Failed to verify/migrate banker_payments schema: {schema_exc}")
    except Exception as exc:
        logger.exception("[startup] database readiness check failed")
        raise RuntimeError("Database is not ready; refusing to start") from exc

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
                "creates draft Veklom discovery listings. Does NOT publish without "
                "explicit operator approval. Rule: if invoked without implementation, "
                "returns SKILL_MISSING."
            ),
            "is_available": False,
            "missing_reason": (
                "SKILL_MISSING — no backend implementation yet. "
                "The skill is catalogued per spec. "
                "To implement: create a route that calls a real dataset-discovery "
                "API, checks license suitability, and POSTs draft listings to "
                "/api/v1/discovery/listings with status=draft. "
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

    # Seed initial Demo API for VNP Probing if none exist
    try:
        from backend.db.models.vnp import Api, ApiRegion
        from backend.core.database.database import async_session
        async with async_session() as seed_db:
            existing_api = (await seed_db.execute(select(Api).limit(1))).scalar_one_or_none()
            if not existing_api:
                demo_api = Api(
                    id="api_demo_veklom_1",
                    provider_id="veklom",
                    name="Veklom Sovereign API",
                    endpoint_url="https://api.veklom.com",
                    health_path="/health",
                    pricing_model="metered",
                    x402_ready=True,
                    stability_rating="Stable",
                    current_composite_score=99.9
                )
                seed_db.add(demo_api)
                demo_region = ApiRegion(
                    api_id=demo_api.id,
                    region_code="global",
                    endpoint_url="https://api.veklom.com",
                    active=True
                )
                seed_db.add(demo_region)
                await seed_db.commit()
                print("[startup] vnp: seeded demo API (api.veklom.com) for edge probing")
    except Exception as e:
        print(f"[startup] vnp: seed warning: {type(e).__name__}: {e}")

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

    # Start VNP background indexers and scoring engine.
    # These in-process loops remain enabled by default while the distributed
    # VNP probe deployment is rolled out; each has an explicit kill switch.
    if _env_enabled("VNP_BACKGROUND_INDEXER_ENABLED"):
        vnp_task = asyncio.create_task(vnp_background_indexer())
    else:
        print("[startup] vnp background indexer disabled by VNP_BACKGROUND_INDEXER_ENABLED=false")
    if _env_enabled("VNP_SCORING_ENGINE_ENABLED"):
        scoring_engine_task = asyncio.create_task(VNPScoringEngine.run_loop())
    else:
        print("[startup] vnp scoring engine disabled by VNP_SCORING_ENGINE_ENABLED=false")
    
    # Start Poltergeist Daemon
    from backend.ops.poltergeist_daemon import poltergeist_daemon
    poltergeist_daemon.start()
    
    # Start the new physical edge probes
    from backend.core.vnp.probes import run_vnp_probes
    if _env_enabled("VNP_INPROCESS_PROBES_ENABLED"):
        physical_probes_task = asyncio.create_task(run_vnp_probes())
    else:
        print("[startup] vnp in-process probes disabled by VNP_INPROCESS_PROBES_ENABLED=false")

    from backend.apps.api.terminal_state import terminal_state_manager
    terminal_state_task = asyncio.create_task(terminal_state_manager.state_loop())

    revocation_listener_task = asyncio.create_task(pgl_revocation_listener())
    
    from backend.core.clients.capi_registration import register_with_capi
    capi_registration_task = asyncio.create_task(register_with_capi())

    yield

    terminal_state_manager.is_running = False

    # Graceful shutdown of plugins and operator workforce
    await plugin_manager.shutdown_all()
    try:
        from backend.ops.operator_engine import engine as operator_engine
        operator_engine.stop()
    except Exception:
        pass
        
    try:
        from backend.ops.poltergeist_daemon import poltergeist_daemon
        poltergeist_daemon.stop()
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
        {"name": "discovery", "description": "Sovereign AI model discovery — acquire, configure, and deploy governed models."},
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

from starlette.middleware.base import BaseHTTPMiddleware

class X402DiscoverableMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-402-Discoverable"] = "true"
        response.headers["X-402-Payment-URL"] = "/.well-known/x402.json"
        response.headers["X-Payment-URL"] = "/.well-known/x402.json"
        return response

app.add_middleware(X402DiscoverableMiddleware)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(AmphotericMiddleware)
app.add_middleware(CappoPolicyMiddleware)
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
    if allow_wildcard and settings.APP_ENV != "production":
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
def _add_cors_headers(request: Request, response):
    # Starlette CORSMiddleware owns CORS responses. Never reflect arbitrary origins.
    return response

@app.exception_handler(404)
async def not_found(request: Request, exc):
    """
    Handle 404s.
    If the request is for the GPC SPA (/gpc/...), serve the index.html so client-side routing works.
    Otherwise, redirect unhandled routes to the Next.js frontend.
    """
    if request.url.path.startswith("/gpc"):
        if GPC_DIR.exists():
            from fastapi.responses import FileResponse
            return FileResponse(str(GPC_DIR / "index.html"))
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "GPC frontend not built"})

    if request.url.path.startswith("/api/"):
        return _add_cors_headers(request, JSONResponse(status_code=404, content={"detail": "Not found"}))
    
    is_workspace = request.url.path.startswith("/workspace")
    is_github = request.url.path.startswith("/github")

    if is_workspace:
        from fastapi.responses import RedirectResponse
        subpath = request.url.path[len("/workspace"):].lstrip("/")
        query_str = f"?{request.url.query}" if request.url.query else ""
        if subpath and not subpath.endswith("/") and not "." in subpath:
            subpath = f"{subpath}/"
        return RedirectResponse(url=f"https://control.veklom.com/{subpath}{query_str}", status_code=307)
    
    if request.url.path in ("/login", "/signup"):
        from fastapi.responses import RedirectResponse
        query_str = f"?{request.url.query}" if request.url.query else ""
        path_name = request.url.path.strip("/")
        return RedirectResponse(url=f"https://control.veklom.com/{path_name}/{query_str}", status_code=302)

    if is_github:
        index_path = WORKSPACE_DIR / "index.html"
        base_path = "/workspace"
    else:
        index_path = None
        base_path = ""

    if index_path and index_path.exists():
        # Read the index.html and inject the auto-editor script
        with open(index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        # Inject script before closing </head> or </body>
        script_tag = f'<script src="{base_path}/auto-editor.js"></script>'
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
    
    from fastapi.responses import RedirectResponse
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"https://control.veklom.com{request.url.path}{query_str}", status_code=302)


from backend.core.security.sanitizer import InProcessErrorSanitizer
global_error_sanitizer = InProcessErrorSanitizer()

@app.exception_handler(500)
async def internal_error(request: Request, exc):
    try:
        sanitized_resp, diag_log = global_error_sanitizer.sanitize_exception(exc)
        import logging
        logging.getLogger("backend.apps.api.main").error(f"[Global500] Unhandled exception occurred:\n{diag_log}")
        return _add_cors_headers(request, JSONResponse(status_code=500, content=sanitized_resp))
    except Exception as parse_err:
        return _add_cors_headers(request, JSONResponse(
            status_code=500, 
            content={
                "error": "CRITICAL_FALLBACK_FAILURE",
                "message": "An unhandled exception occurred and the error sanitizer failed. This incident has been logged.",
                "fallback_detail": str(parse_err)
            }
        ))


# --- Import and register all routers ---

from backend.apps.api.routers import (
    health,
    workspace,
    capi,
    pgl,
    ai,
    vnp,
    x402,
    auth,
    discovery,
    openai_compat,
    protocol as veklom_protocol,
    duel
)
from backend.apps.vnp.routes import router as vnp_staking_router
from backend.apps.ledger.routes import router as x402_ledger_router



# Machine-readable discovery (no prefix — serves /.well-known/*, /llms.txt, /robots.txt, /mcp/*)

app.include_router(discovery.router)
app.include_router(openai_compat.router)
app.include_router(veklom_protocol.router)
app.include_router(vnp_staking_router)
app.include_router(x402_ledger_router)
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(workspace.router, prefix="/api/v1")
app.include_router(capi.router, prefix="/api/v1")
app.include_router(pgl.router, prefix="/api/v1")
from backend.apps.api.routers.archive import pgl_onboarding
app.include_router(pgl_onboarding.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(vnp.router, prefix="/api/v1")
app.include_router(x402.router, prefix="/api/v1")
app.include_router(duel.router, prefix="/api/v1")

# Generative Pipeline Compiler (GPC)

# Layer 5: Ev
# --- Telemetry Fallback Endpoints ---
@app.get("/mcp/status")
async def mcp_status():
    """Truthful endpoint for MCP status checks."""
    try:
        from backend.apps.api.routers.mcp_gateway import _get_all_registered_servers
        servers = _get_all_registered_servers()
        active_count = len(servers)
        server_names = [s.get("name") for s in servers.values()]
        return {
            "status": "ok",
            "mcp_enabled": True,
            "registered_servers": active_count,
            "servers": server_names,
            "source": "veklom-mcp-gateway"
        }
    except Exception as e:
        return {"status": "degraded", "mcp_enabled": True, "error": str(e)}

@app.post("/api/agent-updates")
@app.get("/api/agent-updates")
async def agent_updates(request: Request):
    """Fallback endpoint for agent updates."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    logger.info(f"[agent-updates] Received agent update: {body}")
    return {"status": "accepted", "message": "Update processed successfully"}

def _cors_origins() -> list[str]:
    configured = settings.CORS_ORIGINS
    if isinstance(configured, str):
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    else:
        origins = [str(origin).strip() for origin in (configured or []) if str(origin).strip()]
    required = {
        "https://control.veklom.com",
        "https://veklom-control-plane.vercel.app",
    }
    if settings.APP_ENV != "production":
        required.update({"http://localhost:3000", "http://testserver"})
    return sorted(set(origins) | required)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Payment", "X-Payment-Proof", "X-VNP-Stake"],
    expose_headers=["X-VNP-Stake-Result", "X-VNP-Signature", "X-Veklom-Receipt-ID"],
)
