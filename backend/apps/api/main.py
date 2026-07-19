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

    # Initialize database schema.  We log loud + structured because a silent
    # success here used to mask cases where the metadata object had zero
    # tables registered (because of import order) or the connection pointed
    # at the wrong DB.  Now we always count what was registered and verify
    # at least the critical tables landed.
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("[startup] db: Extension 'vector' created or already exists")
    except Exception as ext_err:
        print(f"[startup] db: Warning — Could not enable 'vector' extension: {ext_err}. Dynamic vector fallbacks will be used.")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            registered = sorted(Base.metadata.tables.keys())
            print(f"[startup] db: create_all completed, {len(registered)} tables on Base.metadata")
            from sqlalchemy import inspect
            critical = ("users", "execution_logs", "audit_logs", "workspaces", "agents")
            
            def get_present_tables(sync_conn):
                return inspect(sync_conn).get_table_names()
            
            present_tables = await conn.run_sync(get_present_tables)
            present = set(present_tables)
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

    # Idempotent column additions for vnp_apis
    vnp_api_columns = [
        "ALTER TABLE vnp_apis ADD COLUMN IF NOT EXISTS x402_ready BOOLEAN DEFAULT false",
        "ALTER TABLE vnp_apis ADD COLUMN IF NOT EXISTS pricing_model VARCHAR(50) DEFAULT 'metered'",
        "ALTER TABLE vnp_apis ADD COLUMN IF NOT EXISTS current_composite_score FLOAT DEFAULT 100.0",
        "ALTER TABLE vnp_apis ADD COLUMN IF NOT EXISTS stability_rating VARCHAR(50) DEFAULT 'Stable'",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in vnp_api_columns:
                await conn.execute(text(ddl))
        print("[startup] db: vnp_apis column migration completed")
    except Exception as e:
        print(f"[startup] db: vnp_apis migration warning: {type(e).__name__}: {e}")

    # Idempotent column additions for VNP physical probe events.
    # Earlier production tables used the v0.1.16 physical-probe shape
    # (occurred_at/api_region_code/signature_value/total_ms). The current
    # ORM/card surface reads the normalized v1.0 names below, so preserve and
    # map old probe evidence forward on every startup.
    vnp_probe_event_columns = [
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS partition_key VARCHAR(20)",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS region VARCHAR(50)",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS worker_signature TEXT",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS latency_ms FLOAT",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS http_version VARCHAR(10)",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS tls_version VARCHAR(20)",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS error_reason VARCHAR(255)",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS measured_at TIMESTAMPTZ",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS evidence_hash VARCHAR",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS provenance_hash VARCHAR",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS cryptography_anchor VARCHAR",
        "ALTER TABLE vnp_probe_events ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ",
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'vnp_probe_events' AND column_name = 'occurred_at'
            ) THEN
                EXECUTE 'UPDATE vnp_probe_events SET measured_at = COALESCE(measured_at, occurred_at) WHERE measured_at IS NULL';
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'vnp_probe_events' AND column_name = 'received_at'
            ) THEN
                EXECUTE 'UPDATE vnp_probe_events SET created_at = COALESCE(created_at, received_at) WHERE created_at IS NULL';
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'vnp_probe_events' AND column_name = 'api_region_code'
            ) THEN
                EXECUTE 'UPDATE vnp_probe_events SET region = COALESCE(region, api_region_code) WHERE region IS NULL';
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'vnp_probe_events' AND column_name = 'signature_value'
            ) THEN
                EXECUTE 'UPDATE vnp_probe_events SET worker_signature = COALESCE(worker_signature, signature_value) WHERE worker_signature IS NULL';
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'vnp_probe_events' AND column_name = 'total_ms'
            ) THEN
                EXECUTE 'UPDATE vnp_probe_events SET latency_ms = COALESCE(latency_ms, total_ms::float) WHERE latency_ms IS NULL';
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'vnp_probe_events' AND column_name = 'error_class'
            ) THEN
                EXECUTE 'UPDATE vnp_probe_events SET error_reason = COALESCE(error_reason, error_class) WHERE error_reason IS NULL';
            END IF;
        END $$;
        """,
        "UPDATE vnp_probe_events SET measured_at = COALESCE(measured_at, now()) WHERE measured_at IS NULL",
        "UPDATE vnp_probe_events SET created_at = COALESCE(created_at, now()) WHERE created_at IS NULL",
        "UPDATE vnp_probe_events SET partition_key = COALESCE(partition_key, to_char(measured_at, 'YYYY-MM')) WHERE partition_key IS NULL",
        "UPDATE vnp_probe_events SET region = COALESCE(region, 'unknown') WHERE region IS NULL",
        "UPDATE vnp_probe_events SET worker_signature = COALESCE(worker_signature, '') WHERE worker_signature IS NULL",
        "UPDATE vnp_probe_events SET latency_ms = COALESCE(latency_ms, 0) WHERE latency_ms IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_probe_events_api_region_measured_at ON vnp_probe_events (api_id, region, measured_at)",
        "CREATE INDEX IF NOT EXISTS idx_vnp_node_heartbeats_node_sequence ON vnp_node_heartbeats (node_id, sequence DESC)",
        "CREATE INDEX IF NOT EXISTS idx_vnp_node_heartbeats_node_timestamp ON vnp_node_heartbeats (node_id, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_vnp_observations_node_sequence ON vnp_observations (node_id, sequence DESC)",
        "CREATE INDEX IF NOT EXISTS idx_vnp_observations_node_created_at ON vnp_observations (node_id, created_at DESC)",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in vnp_probe_event_columns:
                await conn.execute(text(ddl))
        print("[startup] db: vnp_probe_events compatibility migration completed")
    except Exception as e:
        print(f"[startup] db: vnp_probe_events migration warning: {type(e).__name__}: {e}")

    vnp_regional_telemetry_columns = [
        "ALTER TABLE vnp_regional_telemetry ADD COLUMN IF NOT EXISTS provenance_hash VARCHAR",
        "ALTER TABLE vnp_regional_telemetry ADD COLUMN IF NOT EXISTS on_chain_anchor VARCHAR",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in vnp_regional_telemetry_columns:
                await conn.execute(text(ddl))
        print("[startup] db: vnp_regional_telemetry compatibility migration completed")
    except Exception as e:
        print(f"[startup] db: vnp_regional_telemetry migration warning: {type(e).__name__}: {e}")

    # Idempotent column additions for vnp_claim_requests
    vnp_claim_requests_columns = [
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(200) DEFAULT 'public'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS api_domain VARCHAR(255) DEFAULT 'unknown.local'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS provider_name VARCHAR(255) DEFAULT 'Unknown Provider'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS api_name VARCHAR(255) DEFAULT 'Unknown API'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS base_url VARCHAR(500) DEFAULT 'https://api.unknown.com'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS health_path VARCHAR(255) DEFAULT '/health'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS company_name VARCHAR(255) DEFAULT 'Unknown Company'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255) DEFAULT 'unknown@veklom.com'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS pgl_provider_id VARCHAR(200)",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS pgl_certificate_id VARCHAR(200)",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS dns_record VARCHAR(255) DEFAULT ''",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS dns_value VARCHAR(255) DEFAULT ''",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'submitted'",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ",
        "ALTER TABLE vnp_claim_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT (now() + interval '30 days')",
        "UPDATE vnp_claim_requests SET workspace_id = COALESCE(workspace_id, 'public') WHERE workspace_id IS NULL",
        "UPDATE vnp_claim_requests SET api_domain = COALESCE(api_domain, 'unknown.local') WHERE api_domain IS NULL",
        "UPDATE vnp_claim_requests SET company_name = COALESCE(company_name, 'Unknown Company') WHERE company_name IS NULL",
        "UPDATE vnp_claim_requests SET contact_email = COALESCE(contact_email, 'unknown@veklom.com') WHERE contact_email IS NULL",
        "UPDATE vnp_claim_requests SET dns_record = COALESCE(dns_record, '') WHERE dns_record IS NULL",
        "UPDATE vnp_claim_requests SET dns_value = COALESCE(dns_value, '') WHERE dns_value IS NULL",
        "UPDATE vnp_claim_requests SET status = COALESCE(status, 'submitted') WHERE status IS NULL",
        "UPDATE vnp_claim_requests SET created_at = COALESCE(created_at, now()) WHERE created_at IS NULL",
        "UPDATE vnp_claim_requests SET expires_at = COALESCE(expires_at, now() + interval '30 days') WHERE expires_at IS NULL",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in vnp_claim_requests_columns:
                await conn.execute(text(ddl))
        print("[startup] db: vnp_claim_requests column migration completed")
    except Exception as e:
        print(f"[startup] db: vnp_claim_requests migration warning: {type(e).__name__}: {e}")

    # Idempotent column additions for PGL tables
    pgl_columns = [
        "ALTER TABLE pgl_certificates ADD COLUMN IF NOT EXISTS pgl_identity_id VARCHAR(36)",
        "ALTER TABLE pgl_ledger_events ADD COLUMN IF NOT EXISTS pgl_identity_id VARCHAR(36)",
        "ALTER TABLE birth_certificates ADD COLUMN IF NOT EXISTS pgl_identity_id VARCHAR(36)",
        "ALTER TABLE genome_versions ADD COLUMN IF NOT EXISTS pgl_identity_id VARCHAR(36)",
    ]
    try:
        async with engine.begin() as conn:
            for ddl in pgl_columns:
                await conn.execute(text(ddl))
        print("[startup] db: PGL column migration completed")
    except Exception as e:
        print(f"[startup] db: PGL migration warning: {type(e).__name__}: {e}")

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

# --- Middleware ---
# allow_origin_regex lets the VEKLOM-CORE-LIVE applet (Google AI Studio / Cloud Run /
# Firebase Hosting) and *.veklom.com call the API cross-origin, in addition to the
# explicit CORS_ORIGINS list. Regex (not "*") keeps allow_credentials valid.
_CORS_ORIGIN_REGEX = (
    r"https://"
    r"(?:"
    r"([a-z0-9-]+\.)*veklom\.com|"                  # Veklom domains
    r"([a-z0-9-]+\.)*(usercontent\.goog|aistudio\.google\.com)|" # AI Studio sandboxes
    r"veklom-core-live(-[a-z0-9]+)?\.([a-z0-9-]+\.)*(run\.app|web\.app|firebaseapp\.com|vercel\.app)" # Shared hosting strictly for veklom-core-live
    r")$"
)

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
    if allow_wildcard or settings.DEBUG or os.getenv("COOLIFY_RESOURCE_UUID"):
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
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, x-vnp-stake"
    return response

@app.exception_handler(404)
async def not_found(request: Request, exc):
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
    
    if request.url.path in ("/login", "/signup", "/governance", "/governance/"):
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
    duel,
    bingo,
    veklom_id,
    discovery,
    discovery_api
)
from backend.apps.api.routers import (
    agent_arena, agent_evaluation, agent_guardrails, agent_memory, agents, ai, amphoteric, auth, authority,
    authority_runs, autonomous, billing, command_center, compliance,
    copilot, diagnostics, discovery, docs, edge, edge_llm, evaluations,
    evidence, fax, forensics, health, integrations, internal_uacp,
    mcp, monitoring, onboarding_dashboard, onboarding_demo, payments,
    pgl, pgl_adapter, pgl_onboarding, plugins, pricing, providers, rag,
    referrals, repogate_api, routing, runs, runtime_jobs,
    runtime_telemetry, security, seked, smoke, system, team, upload, vnp,
    vnp_beacon, vnp_control, vnp_incidents, vnp_ingest, vnp_v2, vnp_onboarding, vnp_stream,
    workspace, x402, gpc, decision_frames, exec_router, internal_operators, hrm,
    benchmarks, nexus, pipelines, webhooks, webhook, gfr, admin, admin_billing, agency,
    build_release, langchain_ops, playground, arena, conversation_memory, cappo_edge, cappo_inside, locks, terminal,
    genome, well_known, capi, governed, evidence_pack, mission_lock, banker, wallet, duel, claims, badges, tasks,
    demo
)
from backend.services.uacp.http import router as uacp_http_router
from backend.apps.api.routers import admin_billing
from backend.apps.gpc.routes import router as gpc_router
from backend.apps.api.routers import openai_compat
from backend.apps.api.routers import protocol as veklom_protocol
from backend.apps.api.routers import asyncapi_schema
from backend.apps.api.routers import payapi_compliance
from backend.apps.api.routers import session_mesh
from backend.apps.api.routers import telemetry as telemetry_router



# Machine-readable discovery (no prefix — serves /.well-known/*, /llms.txt, /robots.txt, /mcp/*)
app.include_router(discovery.router)
app.include_router(gpc_router)

# OpenAI-compatible gateway — serves /v1/chat/completions and /v1/models
# This is the real endpoint advertised in the openapi.json schema.
# Accepts Bearer JWT or X-API-Key: byos_...
app.include_router(openai_compat.router)

# Veklom Protocol manifest — /protocol.json and /protocol/introspect
app.include_router(veklom_protocol.router)
app.include_router(asyncapi_schema.router)

# Health & status (no prefix)
app.include_router(health.router)

# Auth - restore /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(smoke.router, prefix="/api/v1")
# repo_risk_gate excised
app.include_router(repogate_api.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(hrm.router, prefix="/api/v1")
app.include_router(terminal.router, prefix="/api/terminal")
app.include_router(amphoteric.router, prefix="/api/v1")
app.include_router(vnp_onboarding.router, prefix="/api/v1")
app.include_router(vnp_stream.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(badges.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1/tasks")

# System utilities
app.include_router(system.router, prefix="/api/v1")

# Veklom Runs (Atomic Unit)
app.include_router(runs.router, prefix="/api/v1/runs")

# Genome (PGL) inner-engine read surface — certificates, life ledger, chain verify
app.include_router(genome.router, prefix="/api/v1")

# Agency / Memory — durable agent state (rank/posture/privileges), memory, notifications
app.include_router(agency.router, prefix="/api/v1")

# Copilot registry
app.include_router(copilot.router, prefix="/api/v1")

# Workspace
app.include_router(workspace.router, prefix="/api/v1")

# AI execution
app.include_router(ai.router, prefix="/api/v1")
app.include_router(edge_llm.router, prefix="/api/v1")
app.include_router(exec_router.router, prefix="/api")
app.include_router(exec_router.router, prefix="")

# Playground — sessions, prompts, tools
app.include_router(playground.router, prefix="/api/v1")

# Runtime Jobs Status
app.include_router(runtime_jobs.router, prefix="/api/v1")

# Billing, wallet, subscriptions, budget, cost, payments, payouts
app.include_router(billing.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")

# Security & SEKED
app.include_router(security.router, prefix="/api/v1")
app.include_router(seked.router, prefix="/api/v1")

# Compliance, privacy, content-safety, explainability, evidence, audit
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(autonomous.router, prefix="/api/v1")

# Monitoring, metrics, insights, telemetry, platform pulse, suggestions
app.include_router(monitoring.router, prefix="/api/v1")
app.include_router(runtime_telemetry.router, prefix="/api/v1")
app.include_router(locks.router, prefix="/api/v1")
app.include_router(mission_lock.router, prefix="/api/v1")


# Benchmarks
app.include_router(benchmarks.router, prefix="/api/v1")
app.include_router(benchmarks.router, prefix="/api")
app.include_router(nexus.router, prefix="/api/v1")


# Pipelines, deployments, routing, autonomous, edge/canary
app.include_router(pipelines.router, prefix="/api/v1")
app.include_router(health.router)
app.include_router(duel.router, prefix="/api/v1")
app.include_router(bingo.router, prefix="/api/v1")
app.include_router(veklom_id.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(pipelines.router)
app.include_router(routing.router, prefix="/api/v1")

# Webhooks for external integrations
app.include_router(webhooks.router, prefix="/api/v1")

# Payment Relayer Webhook Ingress
app.include_router(webhook.router, prefix="/api/v1")

# Edge Legacy & Webhook Ingestion Ingress
app.include_router(edge.router, prefix="/api/v1")
app.include_router(payapi_compliance.router, prefix="/api/v1")
app.include_router(session_mesh.router, prefix="/api/v1")
app.include_router(telemetry_router.router)



# x402 Payment & Verification Ingress
app.include_router(x402.router, prefix="/api/v1")
app.include_router(banker.router, prefix="/api/v1")

# Demo (Interactive Tracing for Hostile Agent Interception)
app.include_router(demo.router, prefix="/api/v1/demo")

# UACP Service - dual-adapter architecture (HTTP service + library shim)
app.include_router(uacp_http_router, prefix="/api/v1")

# Integrations (PagerDuty, Slack, etc.)
from backend.apps.api.routers import integrations
app.include_router(integrations.router, prefix="/api/v1")

# Fax Connector Integrations (Hospitals, Legal, Government, Financial Services)
from backend.apps.api.routers import fax
app.include_router(fax.router, prefix="/api/v1")

# Forensics Flight Recorder (Black Box Replay)
from backend.apps.api.routers import forensics
app.include_router(forensics.router, prefix="/api/v1")


# Admin, internal, search, upload, onboarding, referrals, support, export
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin_billing.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")

# GPC (Governed Plan Compiler) + Decision Frames
app.include_router(gpc.router, prefix="/api/v1")
from backend.apps.gpc import routes as gpc_pipeline_routes
app.include_router(gpc_pipeline_routes.router)
app.include_router(decision_frames.router, prefix="/api/v1")

# GFR (Gradient Field Router) — Scientist & Special Agent load balancing skill
app.include_router(gfr.router, prefix="/api/v1")

# Command Center — /api/v1/command-center/* (aliases + new routes per WIRING_MATRIX)
app.include_router(command_center.router, prefix="/api/v1")

# Repo Risk Gate — Excised to standalone gateway

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

# Dynamic MCP Proxy Gateway — OpenAPI dynamic tools & transparent proxying
from backend.apps.api.routers import mcp_gateway
app.include_router(mcp_gateway.router)

# Team management — members, invitations, roles, SSO, MFA
app.include_router(team.router, prefix="/api/v1")

# Plugins Management — mounted at both /api and /api/v1 (bundle calls ${re}/plugins = /api/v1/plugins)
app.include_router(plugins.router, prefix="/api")
app.include_router(plugins.router, prefix="/api/v1")

# Exec alias for bundle's ${re}/v1/exec pattern (re=/api/v1 → /api/v1/v1/exec)
app.include_router(exec_router.router, prefix="/api/v1/v1")

# Veklom Authority Arena simulation endpoints
app.include_router(arena.router)

# Benchmark Arena — Trust Leaderboard, Staking, Gemini Schema Compiler
app.include_router(benchmarks.router, prefix="/api/v1")

# VNP - Data Plane Ingestion and Route Beacon
from backend.apps.api.routers import vnp, vnp_ingest, vnp_beacon, vnp_control, vnp_incidents
app.include_router(vnp_incidents.router, prefix="/api/v1")
app.include_router(banker.router, prefix="/api/v1")
app.include_router(wallet.router, prefix="/api/v1")
app.include_router(duel.router, prefix="/api/v1")
app.include_router(autonomous.router, prefix="/api/v1")
app.include_router(vnp.router, prefix="/api")
app.include_router(vnp.router, prefix="/api/v1")
app.include_router(vnp_ingest.router, prefix="/api/v1")
app.include_router(vnp_beacon.router, prefix="/api/v1")
app.include_router(vnp_control.router, prefix="/api/v1")
app.include_router(vnp_incidents.router, prefix="/api/v1")

# VNP v2.0 - Unified Execution Core (Aligned with Interlink Prototype)
from backend.apps.api.routers import vnp_v2
app.include_router(vnp_v2.router, prefix="/api")


# --- Frontend static files ---
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "static"
LANDING_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "landing"
GPC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "gpc"
WORKSPACE_DIR = FRONTEND_DIR / "workspace"
SOVEREIGN_CONTROL_NODE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "sovereign-control-node"
COMMAND_CENTER_DIR = FRONTEND_DIR / "command-center"
REPOGATE_DIR = FRONTEND_DIR / "repogate"
IRONGRID_DIR = Path(__file__).resolve().parent.parent.parent.parent / "irongrid" / "dist"
LOCKERPHYCER_DIR = FRONTEND_DIR / "lockerphycer"
OPERATOR_CENTER_DIR = FRONTEND_DIR / "operator-center"
ARENA_DIR = FRONTEND_DIR / "arena"
FAULT_MATRIX_DIR = FRONTEND_DIR / "fault-matrix" / "dist"
UACPV3_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uacpv3" / "dist"
WORKSPACE_NEXT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "static" / "workspace-next"
TERMINAL_DIR = FRONTEND_DIR / "terminal"


def _mount_static():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    # Legacy static /terminal mount disabled to allow Next.js decoupled redirects
    # if TERMINAL_DIR.exists():
    #     app.mount("/terminal", StaticFiles(directory=str(TERMINAL_DIR), html=True), name="terminal")
    if WORKSPACE_NEXT_DIR.exists():
        app.mount("/workspace-next", StaticFiles(directory=str(WORKSPACE_NEXT_DIR), html=True), name="workspace-next")
    if SOVEREIGN_CONTROL_NODE_DIR.exists():
        app.mount("/control-plane-next", StaticFiles(directory=str(SOVEREIGN_CONTROL_NODE_DIR), html=True), name="control-plane-next")
    if OPERATOR_CENTER_DIR.exists():
        app.mount("/operator-center", StaticFiles(directory=str(OPERATOR_CENTER_DIR), html=True), name="operator-center")
    if COMMAND_CENTER_DIR.exists():
        app.mount(
            "/command-center",
            StaticFiles(directory=str(COMMAND_CENTER_DIR), html=True),
            name="command-center",
        )
    if REPOGATE_DIR.exists():
        app.mount("/repogate", StaticFiles(directory=str(REPOGATE_DIR), html=True), name="repogate")
    if GPC_DIR.exists():
        pass
    if IRONGRID_DIR.exists():
        app.mount("/irongrid", StaticFiles(directory=str(IRONGRID_DIR), html=True), name="irongrid")
    if LOCKERPHYCER_DIR.exists():
        app.mount("/lockerphycer", StaticFiles(directory=str(LOCKERPHYCER_DIR), html=True), name="lockerphycer")
    if ARENA_DIR.exists():
        app.mount("/arena", StaticFiles(directory=str(ARENA_DIR), html=True), name="arena")
    if FAULT_MATRIX_DIR.exists():
        app.mount("/fault-matrix", StaticFiles(directory=str(FAULT_MATRIX_DIR), html=True), name="fault-matrix")
    if UACPV3_DIR.exists():
        app.mount("/uacpv3", StaticFiles(directory=str(UACPV3_DIR), html=True), name="uacpv3")
        app.mount("/uacp", StaticFiles(directory=str(UACPV3_DIR), html=True), name="uacp")
    # Mount static directory for CSS, JS, branding, etc.
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    # Do NOT mount landing directory - it will be served by catch-all route



@app.get("/workspace")
@app.get("/workspace/")
async def redirect_workspace_root(request: Request):
    from fastapi.responses import RedirectResponse
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"https://control.veklom.com/dashboard/{query_str}", status_code=307)


@app.get("/login")
@app.get("/login/")
@app.get("/workspace/login")
@app.get("/workspace/login/")
async def redirect_login(request: Request):
    from fastapi.responses import RedirectResponse
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"https://control.veklom.com/login{query_str}", status_code=307)


@app.get("/signup")
@app.get("/signup/")
@app.get("/workspace/signup")
@app.get("/workspace/signup/")
async def redirect_signup(request: Request):
    from fastapi.responses import RedirectResponse
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"https://control.veklom.com/signup{query_str}", status_code=307)


@app.get("/terminal")
@app.get("/terminal/")
@app.get("/terrrinal")
@app.get("/terrrinal/")
async def redirect_terminal_root(request: Request):
    from fastapi.responses import RedirectResponse
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"https://control.veklom.com/terminal/{query_str}", status_code=307)


@app.get("/control-plane-next/subscription/")
@app.get("/control-plane-next/subscription")
async def redirect_subscription_to_billing(request: Request):
    from fastapi.responses import RedirectResponse
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"https://control.veklom.com/billing/{query_str}", status_code=307)


@app.get("/arena")
@app.get("/arena/")
async def serve_arena_page():
    index_path = ARENA_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Arena build not found.")


_mount_static()


# ---------------------------------------------------------------------------
# Protected route guards — enforce auth BEFORE serving static pages
# These run as route handlers registered BEFORE the static mounts
# ---------------------------------------------------------------------------
_OWNER_ROLES = {"OWNER", "SUPER_ADMIN", "owner", "super_admin"}
_PAID_PLANS = {"sovereign", "pro", "founding", "standard", "regulated", "enterprise"}
_PAID_ROLES = {"OWNER", "SUPER_ADMIN", "ADMIN", "owner", "super_admin", "admin"}


async def _get_user_from_request(request):
    """Extract and verify JWT from Authorization header or cookie, then fetch user."""
    from backend.core.security.auth import verify_token
    from backend.core.database.database import get_db_session
    from sqlalchemy import select
    from backend.db.models.user import User
    from backend.core.services.entitlements import get_workspace_plan
    
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
        user_id = payload.get("sub")
        if not user_id:
            return None
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return None
            plan = "free"
            industry = "generic"
            if user.workspace_id:
                from backend.db.models.workspace import Workspace
                ws_result = await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))
                workspace = ws_result.scalar_one_or_none()
                if workspace:
                    industry = workspace.industry or "generic"
                
                plan_val = await get_workspace_plan(db, user.workspace_id)
                if plan_val:
                    plan = plan_val.lower()
                    normalization = {
                        "community": "free",
                        "founding": "starter",
                        "standard": "pro",
                        "regulated": "sovereign",
                        "enterprise": "enterprise"
                    }
                    plan = normalization.get(plan, plan)
            return {
                "id": user.id,
                "role": (user.role or "").upper(),
                "is_superuser": bool(user.is_superuser),
                "plan": plan,
                "status": user.status,
                "workspace_id": user.workspace_id,
                "industry": industry
            }
    except Exception:
        return None

@app.middleware("http")
async def force_https(request, call_next):
    if request.url.path in {"/health", "/health/", "/api/health", "/api/v1/health"}:
        return await call_next(request)
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if settings.APP_ENV == "production" and proto != "https":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=str(request.url.replace(scheme="https")),
            status_code=308
        )
    return await call_next(request)

@app.middleware("http")
async def enforce_route_access(request, call_next):
    """Enforce access control on protected static routes."""
    path = request.url.path

    if path.startswith("/command-center"):
        user = await _get_user_from_request(request)
        allowed = False
        if user:
            # Command Center only loads for platform superusers
            allowed = user.get("is_superuser") and user.get("role") == "SUPER_ADMIN"
        if not allowed:
            html = '<html><head><meta http-equiv="refresh" content="0;url=/workspace/#/overview"></head>'\
                   '<body>Platform access required. <a href="/workspace/#/overview">Go to workspace</a></body></html>'
            from starlette.responses import HTMLResponse
            return HTMLResponse(html, status_code=403)

    if path.startswith("/control-plane-next") and not path.endswith(".js") and not path.endswith(".css"):
        if "/login" not in path and "/signup" not in path:
            user = await _get_user_from_request(request)
            if user:
                from starlette.responses import HTMLResponse
                if user.get("status") == "pending_verification":
                    html = '''
                    <html><head><title>Verify Email</title>
                    <style>
                    body { font-family: Inter, sans-serif; background: #0f0f13; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                    .card { background: #1e293b; padding: 40px; border-radius: 12px; text-align: center; max-width: 400px; }
                    button { background: #7c3aed; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; margin-top: 20px; }
                    </style>
                    <script>
                    async function resend() {
                        const res = await fetch("/api/v1/auth/resend-verification", {method: "POST"});
                        if (res.ok) alert("Email resent!"); else alert("Error resending");
                    }
                    </script>
                    </head><body>
                    <div class="card">
                        <h2>Check Your Email</h2>
                        <p style="color:#94a3b8">We sent a verification link to your email. You must verify your email before accessing the dashboard.</p>
                        <button onclick="resend()">Resend Verification Email</button>
                        <br><br><a href="/api/v1/auth/logout" style="color:#7c3aed">Logout</a>
                    </div>
                    <script>
                    setInterval(async () => {
                        const res = await fetch("/api/v1/auth/me");
                        if (res.ok) {
                            const data = await res.json();
                            if (data.status === "active") window.location.reload();
                        }
                    }, 5000);
                    </script>
                    </body></html>
                    '''
                    return HTMLResponse(html)
                
                if user.get("industry") == "generic":
                    html = '''
                    <html><head><title>Workspace Setup</title>
                    <style>
                    body { font-family: Inter, sans-serif; background: #0f0f13; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                    .card { background: #1e293b; padding: 40px; border-radius: 12px; max-width: 450px; width: 100%; }
                    select, button { width: 100%; padding: 12px; border-radius: 6px; margin-top: 10px; box-sizing: border-box; }
                    select { background: #0f0f13; color: white; border: 1px solid #334155; }
                    button { background: #7c3aed; color: white; border: none; cursor: pointer; margin-top: 20px; font-weight: bold; }
                    </style>
                    </head><body>
                    <div class="card">
                        <h2>Workspace Setup</h2>
                        <p style="color:#94a3b8">Select your industry vertical to configure compliance rules and available AI tools.</p>
                        <form id="setupForm" onsubmit="event.preventDefault(); submitForm();">
                            <label>Industry Vertical</label>
                            <select id="industry">
                                <option value="general">General / Technology</option>
                                <option value="bank">Banking / Finance</option>
                                <option value="hospital">Healthcare / Life Sciences</option>
                                <option value="government">Government / Public Sector</option>
                            </select>
                            <button type="submit">Complete Setup</button>
                        </form>
                    </div>
                    <script>
                    async function submitForm() {
                        const ind = document.getElementById("industry").value;
                        const res = await fetch("/api/v1/workspace/config", {
                            method: "POST",
                            headers: {"Content-Type": "application/json"},
                            body: JSON.stringify({industry: ind})
                        });
                        if (res.ok) window.location.href = "https://control.veklom.com/";
                        else alert("Error saving config");
                    }
                    </script>
                    </body></html>
                    '''
                    return HTMLResponse(html)

    # GPC — paid plan required (sovereign / pro / enterprise)
    if path.startswith("/gpc") or path.startswith("/gpc-engine"):
        if path.startswith("/gpc/assets") or path.startswith("/gpc-engine/assets") or request.query_params.get("public_demo") == "1":
            return await call_next(request)
        user = await _get_user_from_request(request)
        allowed = False
        if user:
            plan = user.get("plan", "")
            allowed = plan in _PAID_PLANS
        if not allowed:
            html = '<html><head><meta http-equiv="refresh" content="0;url=/workspace/#/billing"></head>'\
                   '<body>Paid plan required. <a href="/workspace/#/billing">Upgrade your plan</a></body></html>'
            from starlette.responses import HTMLResponse
            return HTMLResponse(html, status_code=403)

    host = request.headers.get("host", "")
    if host and ("gpc.veklom.com" in host or "www.gpc.veklom.com" in host):
        query_str = f"?{request.url.query}" if request.url.query else ""
        from starlette.responses import RedirectResponse
        return RedirectResponse(url=f"https://control.veklom.com/gpc{query_str}", status_code=307)

    response = await call_next(request)

    return response


@app.get("/.well-known/x402.json")
async def get_x402_well_known():
    return {
        "protocol": "x402",
        "version": "1.0",
        "capabilities": ["settlement", "evidence"],
        "endpoints": {
            "staking_state": "/api/v1/x402/staking/state"
        }
    }


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
        return RedirectResponse(url="/workspace#/discovery/ls_co2router", status_code=301)
    if "lockerphycer.veklom.com" in host:
        lockerphycer_index = FRONTEND_DIR / "lockerphycer" / "index.html"
        if lockerphycer_index.exists():
            return FileResponse(str(lockerphycer_index))
        return JSONResponse(status_code=404, content={"detail": "Lockerphycer page not found"})
    if "status.veklom.com" in host:
        from backend.apps.api.status_page import _status_html
        from datetime import datetime, timezone
        status_data = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat().split('.')[0] + "Z",
            "version": "1.0.0"
        }
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=_status_html(status_data), status_code=200)
        
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=_fallback_html(), status_code=200)

@app.get("/workspace")
@app.get("/login")
@app.get("/signup")
async def frontend_redirects(request: Request):
    from fastapi.responses import RedirectResponse
    path = request.url.path
    return RedirectResponse(url=f"https://control.veklom.com{path}", status_code=302)


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


@app.get("/agent-duel")
async def agent_duel_page():
    path = LANDING_DIR / "agent-duel.html"
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


@app.get("/legal/license")
async def legal_license():
    path = LANDING_DIR / "license.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.get("/legal/vendor-agreement")
async def legal_vendor_agreement():
    path = LANDING_DIR / "vendor-agreement.html"
    if path.exists():
        return FileResponse(str(path))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


# Canonical redirects for .html aliases and shorthand legal paths
@app.get("/legal/license.html")
@app.get("/license")
async def legal_license_alias():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/legal/license", status_code=301)


@app.get("/legal/vendor-agreement.html")
@app.get("/vendor-agreement")
async def legal_vendor_agreement_alias():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/legal/vendor-agreement", status_code=301)


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
  <url><loc>https://veklom.com/legal/license</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://veklom.com/legal/vendor-agreement</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
</urlset>"""
    return HTMLResponse(content=content, media_type="application/xml")


@app.post("/api/v1/feedback")
@app.post("/api/v1/feedback/")
async def submit_feedback(
    request: Request,
    category: str = Query(None),
    subject: str = Query(None),
    body: str = Query(None)
):
    from typing import Optional
    from fastapi import Query
    from fastapi.responses import JSONResponse
    
    json_data = {}
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            json_data = await request.json()
    except Exception:
        pass

    cat = (category or json_data.get("category") or "feedback").strip()[:64]
    subj = (subject or json_data.get("subject") or "No Subject").strip()[:255]
    feedback_body = (body or json_data.get("body") or "").strip()[:4096]

    if not feedback_body:
        return JSONResponse(status_code=422, content={"detail": "body is required"})

    print(f"[feedback] category={cat} subject={subj!r} body={feedback_body[:80]!r}")

    # Send email notification to Admin/Founder via Resend
    from backend.core.utils.email import send_email_via_resend
    from backend.core.config.settings import settings

    admin_email = settings.ADMIN_EMAIL or "founder@veklom.com"
    email_subject = f"[Veklom Feedback] {cat.upper()}: {subj}"
    email_html = f"""
    <h3>New Feedback Received</h3>
    <p><strong>Category:</strong> {cat}</p>
    <p><strong>Subject:</strong> {subj}</p>
    <p><strong>Message:</strong></p>
    <div style="background:#f4f4f4;padding:15px;border-radius:5px;white-space:pre-wrap;">{feedback_body}</div>
    <br>
    <hr>
    <p style="font-size:0.8em;color:#777;">Sent automatically by Veklom Sovereign AI Hub backend.</p>
    """
    await send_email_via_resend(to_email=admin_email, subject=email_subject, html_content=email_html)

    return {"submitted": True, "message": "Thank you for your feedback."}


# ---------------------------------------------------------------------------
# Contact form — routes landing page "Talk to Sales" / contact submissions
# ---------------------------------------------------------------------------

@app.post("/api/v1/contact")
@app.post("/api/v1/contact/")
async def submit_contact(request: Request):
    """Handle contact/sales inquiry form submissions from the landing page.
    Emails sales@veklom.com and sends a confirmation to the submitter.
    """
    from fastapi.responses import JSONResponse
    from backend.core.utils.email import send_email_via_resend
    from backend.core.config.settings import settings

    json_data = {}
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            json_data = await request.json()
        else:
            form = await request.form()
            json_data = dict(form)
    except Exception:
        pass

    name = (json_data.get("name") or "").strip()[:128]
    email = (json_data.get("email") or "").strip()[:255]
    company = (json_data.get("company") or "").strip()[:128]
    message = (json_data.get("message") or "").strip()[:4096]
    inquiry_type = (json_data.get("type") or json_data.get("inquiry_type") or "general").strip()[:64]

    if not email or "@" not in email:
        return JSONResponse(status_code=422, content={"detail": "A valid email address is required."})
    if not message:
        return JSONResponse(status_code=422, content={"detail": "Message is required."})

    print(f"[contact] from={email!r} name={name!r} company={company!r} type={inquiry_type!r}")

    # --- Notify sales@veklom.com ---
    sales_email = "sales@veklom.com"
    sales_html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:640px;margin:0 auto;background:#0f0f13;color:#e2e8f0;padding:40px;border-radius:12px;">
      <div style="text-align:center;margin-bottom:28px;">
        <span style="font-size:22px;font-weight:700;background:linear-gradient(135deg,#7c3aed,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Veklom</span>
        <span style="color:#64748b;font-size:13px;display:block;margin-top:4px;">New Sales Inquiry</span>
      </div>
      <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
        <tr><td style="padding:8px 0;color:#94a3b8;width:110px;">Name</td><td style="padding:8px 0;color:#f8fafc;font-weight:600;">{name or "—"}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8;">Email</td><td style="padding:8px 0;"><a href="mailto:{email}" style="color:#a78bfa;">{email}</a></td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8;">Company</td><td style="padding:8px 0;color:#f8fafc;">{company or "—"}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8;">Type</td><td style="padding:8px 0;color:#a78bfa;text-transform:capitalize;">{inquiry_type}</td></tr>
      </table>
      <div style="background:#1e293b;border-radius:8px;padding:20px;margin-bottom:24px;">
        <p style="color:#94a3b8;font-size:13px;margin:0 0 8px;">Message:</p>
        <p style="color:#e2e8f0;line-height:1.7;white-space:pre-wrap;margin:0;">{message}</p>
      </div>
      <p style="color:#475569;font-size:12px;text-align:center;">Received via veklom.com contact form</p>
    </div>
    """
    await send_email_via_resend(
        to_email=sales_email,
        subject=f"[Sales Inquiry] {inquiry_type.title()} from {name or email}",
        html_content=sales_html,
    )

    # --- Send confirmation to submitter ---
    confirm_html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#0f0f13;color:#e2e8f0;padding:40px;border-radius:12px;">
      <div style="text-align:center;margin-bottom:32px;">
        <span style="font-size:24px;font-weight:700;background:linear-gradient(135deg,#7c3aed,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Veklom</span>
      </div>
      <h2 style="color:#f8fafc;font-size:20px;margin-bottom:8px;">We received your message</h2>
      <p style="color:#94a3b8;line-height:1.7;">
        Hi {name or "there"},<br><br>
        Thanks for reaching out! Our team will review your inquiry and get back to you within 1&ndash;2 business days.
      </p>
      <div style="background:#1e293b;border-radius:8px;padding:18px;margin:24px 0;">
        <p style="color:#64748b;font-size:12px;margin:0 0 6px;">Your message:</p>
        <p style="color:#cbd5e1;font-size:14px;line-height:1.6;white-space:pre-wrap;margin:0;">{message[:500]}{"..." if len(message) > 500 else ""}</p>
      </div>
      <p style="color:#94a3b8;line-height:1.7;">In the meantime, you can <a href="https://veklom.com/signup" style="color:#a78bfa;">create a free account</a> and explore the platform.</p>
      <hr style="border:none;border-top:1px solid #1e293b;margin:28px 0;">
      <p style="color:#475569;font-size:12px;text-align:center;">Veklom &mdash; Sovereign AI Runtime Infrastructure &bull; <a href="mailto:sales@veklom.com" style="color:#7c3aed;">sales@veklom.com</a></p>
    </div>
    """
    import asyncio
    asyncio.create_task(
        send_email_via_resend(
            to_email=email,
            subject="We received your Veklom inquiry",
            html_content=confirm_html,
        )
    )

    return {"submitted": True, "message": "Thank you! We'll be in touch within 1-2 business days."}


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
    path = LANDING_DIR / "status.html"
    if path.exists():
        return FileResponse(str(path))
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content="<html><body><h1>System Status: All Systems Operational</h1><p>Status page stub for testing.</p></body></html>")

import httpx

@app.post("/api/run-sample")
@app.post("/api/v1/terminal/run")
async def run_sample_unified(request: Request, db: AsyncSession = Depends(get_db)):
    """
    THE GOVERNED TERMINAL ENDPOINT.
    Refactored to enforce Fail-Closed PGL validation via cAPI.
    """
    from backend.apps.api.routers.capi import ExecutionIntent, evaluate_intent_governed, governed_execution_intercept

    body = await request.json()
    intent_prompt = body.get("intent", "Execute default quantum instruction")
    
    # 1. Wrap the terminal command in a Governed Intent Envelope
    # In a real scenario, the terminal (frontend) would sign this.
    # Here we simulate the signed intent for the fast terminal transition.
    intent = ExecutionIntent(
        agent_id=body.get("agent_id", "quantum_terminal_agent"),
        pgl_id=body.get("pgl_id", "terminal-demo-pgl-id"),
        target_protocol="local_tool",
        action="terminal.execute",
        payload={"command": intent_prompt}
    )
    
    # 2. Execute via the governed interceptor (The 9-Phase Gate)
    # This ensures that even "fast" terminal commands are audited and policy-checked.
    try:
        receipt = await governed_execution_intercept(intent, db, None)
        return receipt
    except HTTPException as e:
        # Re-raise the VETO from cAPI
        raise e
    except Exception as e:
        print(f"[terminal] Governed execution failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e), "detail": "cAPI Execution Error"})
@app.get("/status")
async def status_page():
    path = LANDING_DIR / "status.html"
    if path.exists():
        return FileResponse(str(path))
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content="<html><body><h1>System Status: All Systems Operational</h1><p>Status page stub for testing.</p></body></html>")


# The /terminal path is now mounted directly as a static directory serving the built React app from agent-control-need-pgl


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
@app.get("/discovery")
async def discovery_info():
    return {
        "platform": "Veklom",
        "description": "discovery products built for governed execution",
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
                "type": "discovery Product",
                "description": "A Veklom discovery product for controlled, governed execution workflows.",
                "url": "https://lockerphycer-git-main-dksummers-projects.vercel.app/"
            }
        ]
    }

@app.get("/discovery/lockerphycer")
async def discovery_lockerphycer():
    return {
        "id": "lockerphycer",
        "name": "Lockerphycer",
        "type": "discovery Product",
        "description": "A Veklom discovery product for controlled, governed execution workflows.",
        "demo_url": "https://lockerphycer-git-main-dksummers-projects.vercel.app/",
        "status": "Available in Veklom ecosystem"
    }

@app.get("/discovery/py03-irongrid")
async def discovery_py03():
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
@app.get("/gpc/")
@app.get("/pipelines")
@app.get("/pipelines/")
async def redirect_gpc(request: Request):
    from fastapi.responses import RedirectResponse
    query_str = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(url=f"https://control.veklom.com/gpc{query_str}", status_code=307)


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
<title>Veklom API</title>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-KCZM27WWX7"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied'
  });
  gtag('js', new Date());
  gtag('config', 'G-KCZM27WWX7');
</script>
<style>
  body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
  .container { text-align: center; }
  h1 { font-size: 2rem; font-weight: 600; margin-bottom: 0.5rem; }
  p { color: #888; }
</style>
</head>
<body>
<div class="container">
  <h1>Veklom API</h1>
  <p>System Operational.</p>
</div>
</body>
</html>"""


def _gpc_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GPC — Governed Plan Compiler | Veklom</title>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-KCZM27WWX7"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied'
  });
  gtag('js', new Date());
  gtag('config', 'G-KCZM27WWX7');
</script>
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


# Well-known manifests (no prefix)
app.include_router(well_known.router)

# Status Page (Mounted on root and /status)
from backend.apps.api import status_page
app.include_router(status_page.router)

# Authority - Runtime Authority Pack
app.include_router(authority.router, prefix="/api/v1")
app.include_router(authority_runs.router, prefix="/api/v1")

# PGL Adapter - Agent Management
from backend.apps.api.routers import identity_rag
app.include_router(identity_rag.router)
app.include_router(copilot.router, prefix="/api/v1")
app.include_router(workspace.router, prefix="/api/v1")
app.include_router(discovery_api.router, prefix="/api/v1/discovery")
app.include_router(pgl.router, prefix="/api/v1")
app.include_router(pgl_adapter.router, prefix="/api/v1")
app.include_router(pgl_onboarding.router, prefix="/api/v1")
app.include_router(onboarding_demo.router, prefix="/api/v1")
app.include_router(onboarding_dashboard.router)
app.include_router(governed.router, prefix="/api/v1")

# CAPPO - Internal Execution Authority
app.include_router(cappo_edge.router, prefix="/api/v1")
app.include_router(cappo_inside.router, prefix="/api/v1")

# Evidence - Evidence Pack System
app.include_router(evidence.router, prefix="/api/v1")
app.include_router(evidence_pack.router, prefix="/api/v1")

# Agent Arena - AuthorityRun Integration
app.include_router(agent_arena.router, prefix="/api/v1")

# Build & Release - Governed Deployment Pipeline
app.include_router(build_release.router, prefix="/api/v1")

# Referral system
app.include_router(referrals.router, prefix="/api/v1")

# Pricing tiers
app.include_router(pricing.router, prefix="/api/v1")

# AI Agents Stack 2026 - Six-Layer Architecture
# Layer 2: Protocols and Tools (MCP Support)
app.include_router(mcp.router, prefix="/api/v1")

# Layer 3: Memory and Context
app.include_router(agent_memory.router, prefix="/api/v1")
app.include_router(conversation_memory.router, prefix="/api/v1")

# Generative Pipeline Compiler (GPC)
# from backend.apps.gpc import routes as gpc_routes
# app.include_router(gpc_routes.router, prefix="/api/v1")

# Layer 5: Ev

app.add_middleware(CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-VNP-Stake-Result", "X-VNP-Signature", "X-Veklom-Receipt-ID"]
)
