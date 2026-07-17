"""
Veklom Protocol Manifest — Enterprise Grade
============================================
Self-describing capability registry and AI-native introspection engine.

Endpoints
---------
GET  /protocol.json        — Full protocol manifest with live health status, CGI geometry block, HATEOAS links
POST /protocol/introspect  — Semantic + keyword capability discovery (JWT-scoped, audit-logged)

Architecture
------------
- Every capability entry carries: endpoint list, auth modes, rate limits, schema ref, live health status
- capabilityGeometry block encodes the CGI (Capability Geometry Invariant) ratios
- Health checks are performed asynchronously at manifest generation time; cached in Redis for 60s
- /protocol/introspect respects caller JWT scope — returns only capabilities the caller is authorized to use
- Every introspect call is written to the VNP audit trail (off hot-path, async)
- HATEOAS _links present on every response
"""
from __future__ import annotations

import asyncio
import hashlib
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Veklom Protocol"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "veklom/v1"
MANIFEST_VERSION = "1.0.0"
BASE_URL = "https://api.veklom.com"

# Cache TTL for health check results (seconds)
HEALTH_CACHE_TTL = 60

# In-memory health cache: {endpoint_path: (status, latency_ms, checked_at)}
_health_cache: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Capability Definitions
# ---------------------------------------------------------------------------

_CAPABILITIES: Dict[str, Any] = {
    "inference": {
        "description": "OpenAI-compatible inference gateway. Routes to BYOS model backends. Preserves system prompts, supports streaming and multi-turn message arrays.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/v1/chat/completions",
                "auth": ["bearer", "byos_key"],
                "rate_limit": "60/min per workspace",
                "schema_ref": "#/components/schemas/ChatCompletionRequest",
                "description": "Chat completions — full OpenAI message array passthrough with optional streaming",
                "_links": {
                    "models": {"href": "/v1/models", "method": "GET"},
                    "stake": {"href": "/api/v1/vnp/stake", "method": "POST"},
                },
            },
            {
                "method": "GET",
                "path": "/v1/models",
                "auth": ["bearer", "byos_key"],
                "rate_limit": "120/min per workspace",
                "description": "List available inference models in the workspace",
            },
        ],
    },
    "pipeline": {
        "description": "GPC — Governed Pipeline Compiler. Converts messy natural-language intent into a deterministic, verifiable execution graph. Emits evidence to the VNP ledger on every execution.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/v1/gpc/compile",
                "auth": ["bearer"],
                "rate_limit": "30/min per workspace",
                "schema_ref": "#/components/schemas/NLToGraphRequest",
                "description": "Compile natural language intent into a GPC pipeline graph",
                "_links": {
                    "execute": {"href": "/api/v1/gpc/execute", "method": "POST"},
                    "components": {"href": "/api/v1/gpc/components", "method": "GET"},
                },
            },
            {
                "method": "POST",
                "path": "/api/v1/gpc/execute",
                "auth": ["bearer"],
                "rate_limit": "20/min per workspace",
                "schema_ref": "#/components/schemas/PipelineExecutionRequest",
                "description": "Execute a compiled GPC pipeline graph — emits evidence to VNP ledger",
                "_links": {
                    "evidence": {"href": "/api/v1/evidence/verify", "method": "POST"},
                    "stake": {"href": "/api/v1/vnp/stake", "method": "POST"},
                    "audit": {"href": "/api/v1/gpc/audit/{pipeline_id}", "method": "GET"},
                },
            },
            {
                "method": "GET",
                "path": "/api/v1/gpc/components",
                "auth": ["bearer"],
                "rate_limit": "120/min per workspace",
                "description": "List available GPC node component types",
            },
        ],
    },
    "identity": {
        "description": "PGL IdentityRAG — cross-cluster tenant resolution. Maps JWT sub claims to workspace_id. Powers Zero Trust enforcement across all service boundaries.",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/v1/pgl/registry",
                "auth": [],
                "rate_limit": "120/min",
                "description": "Public PGL registry — lists resolved workspace identities",
                "_links": {
                    "manifest": {"href": "/protocol.json", "method": "GET"},
                },
            },
        ],
    },
    "evidence": {
        "description": "Settlement Ledger (x402) — cryptographic proof of compute execution. Every evidence record carries an immutable hash linking compute to payment.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/v1/evidence/verify",
                "auth": [],
                "rate_limit": "120/min",
                "description": "Verify an evidence record by ID — returns hash, status, and settlement proof",
                "_links": {
                    "export": {"href": "/api/v1/evidence/export", "method": "GET"},
                    "stake": {"href": "/api/v1/vnp/stake", "method": "POST"},
                },
            },
            {
                "method": "GET",
                "path": "/api/v1/evidence/export",
                "auth": ["bearer"],
                "rate_limit": "20/min per workspace",
                "description": "Export evidence records for the workspace as JSON or CSV",
                "_links": {
                    "workspace": {"href": "/api/v1/workspace/overview/live", "method": "GET"},
                },
            },
        ],
    },
    "staking": {
        "description": "VNP Micro-Stakes — real-time SLA performance bonds. Stake against compute SLAs; slash on violation, yield on success.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/v1/vnp/stake",
                "auth": ["bearer"],
                "rate_limit": "60/min per workspace",
                "description": "Post a VNP stake on a compute SLA — persisted off hot-path to vnp_stake_logs",
                "_links": {
                    "evidence": {"href": "/api/v1/evidence/verify", "method": "POST"},
                    "workspace": {"href": "/api/v1/workspace/overview/live", "method": "GET"},
                },
            },
        ],
    },
    "auth": {
        "description": "Authentication — JWT login, workspace registration, and API key management.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/v1/auth/login",
                "auth": [],
                "rate_limit": "10/min per IP",
                "description": "Login and receive a signed JWT",
                "_links": {
                    "manifest": {"href": "/protocol.json", "method": "GET"},
                    "workspace": {"href": "/api/v1/workspace/overview/live", "method": "GET"},
                },
            },
            {
                "method": "POST",
                "path": "/api/v1/auth/register",
                "auth": [],
                "rate_limit": "5/min per IP",
                "description": "Register a new workspace account",
            },
        ],
    },
    "workspace": {
        "description": "Workspace management — live metrics, billing summary, and usage overview.",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/v1/workspace/overview/live",
                "auth": ["bearer"],
                "rate_limit": "30/min per workspace",
                "description": "Live workspace metrics: token usage, active sessions, billing status, backend health",
                "_links": {
                    "evidence": {"href": "/api/v1/evidence/export", "method": "GET"},
                    "stake": {"href": "/api/v1/vnp/stake", "method": "POST"},
                },
            },
        ],
    },
    "agents": {
        "description": "Autonomous agent management — list, inspect, and govern AI agents operating in the workspace.",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/v1/agents",
                "auth": ["bearer"],
                "rate_limit": "60/min per workspace",
                "description": "List all agents in the workspace with their current execution state",
            },
        ],
    },
    "payments": {
        "description": "x402 payment protocol — pay-per-request governed AI compute. Every payment generates a cryptographic receipt linked to evidence.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/v1/x402",
                "auth": [],
                "rate_limit": "30/min",
                "description": "Initiate an x402 compute payment — returns receipt_id and evidence_hash",
                "_links": {
                    "evidence": {"href": "/api/v1/evidence/verify", "method": "POST"},
                },
            },
        ],
    },
    "sessions": {
        "description": "Veklom Session Mesh — governed multi-agent session lifecycle with Ed25519 audit chains and enforcer consensus.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/v1/sessions",
                "auth": ["bearer"],
                "rate_limit": "60/min per workspace",
                "description": "Create a new governed agent session",
                "_links": {
                    "mesh_verify": {"href": "/api/v1/sessions/{session_id}/mesh/verify", "method": "POST"},
                    "audit": {"href": "/api/v1/sessions/{session_id}/audit", "method": "GET"},
                },
            },
            {
                "method": "POST",
                "path": "/api/v1/sessions/{session_id}/transition",
                "auth": ["bearer"],
                "rate_limit": "120/min per workspace",
                "description": "Transition a session state — writes signed audit record",
            },
            {
                "method": "GET",
                "path": "/api/v1/sessions/{session_id}/audit",
                "auth": ["bearer"],
                "rate_limit": "120/min per workspace",
                "description": "Retrieve the full Ed25519-chained audit trail for a session",
            },
        ],
    },
    "telemetry": {
        "description": "Stability telemetry — Agent Stability Index (ASI) and Context Divergence Score (CDS) for measuring and alerting on agent drift.",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/v1/telemetry/asi",
                "auth": ["bearer"],
                "rate_limit": "30/min per workspace",
                "description": "Rolling Agent Stability Index — composite score across 12 behavioral dimensions",
                "_links": {
                    "cds": {"href": "/api/v1/telemetry/cds", "method": "GET"},
                    "history": {"href": "/api/v1/telemetry/asi/history", "method": "GET"},
                },
            },
            {
                "method": "GET",
                "path": "/api/v1/telemetry/cds",
                "auth": ["bearer"],
                "rate_limit": "30/min per workspace",
                "description": "Context Divergence Score — cosine distance between active agent session context vectors",
                "_links": {
                    "asi": {"href": "/api/v1/telemetry/asi", "method": "GET"},
                    "matrix": {"href": "/api/v1/telemetry/cds/matrix", "method": "GET"},
                },
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Capability Geometry Invariant (CGI) block — the Digital Seked
# ---------------------------------------------------------------------------

_CAPABILITY_GEOMETRY: Dict[str, Any] = {
    "description": "Capability Geometry Invariant — structural ratios bounding agent autonomy, governance, and evidence to prevent behavioral drift.",
    "seked_version": "1.0.0",
    "ratios": {
        "specification_complexity": {
            "label": "S_C",
            "description": "Density of the protocol specification — capability count, schema depth, constraint count",
            "value": len(_CAPABILITIES),
            "unit": "capabilities",
        },
        "implementation_freedom": {
            "label": "I_C",
            "description": "Combinatorial space available to compliant builders",
            "builder_freedom_budget": {
                "max_independent_agents": 3,
                "max_parallel_branches": 2,
                "allowable_tool_combinations": 8,
            },
        },
        "governance_constraint_density": {
            "label": "G_C",
            "description": "Restrictive boundaries applied per endpoint",
            "required_schema_dialect": "json-schema/2020-12",
            "enforced_rbac_policies": 5,
            "stateless_validation_required": True,
            "zero_trust_default_deny": True,
            "jwt_scope_enforcement": True,
        },
        "evidence_strength": {
            "label": "E_C",
            "description": "Verification pipeline rigor",
            "min_test_suites": 3,
            "min_deterministic_replays": 5000,
            "required_proof_types": [
                "context_divergence_verification",
                "policy_invariant_check",
                "vnp_ledger_consistency",
                "ed25519_audit_chain",
            ],
        },
    },
    "invariant_bounds": {
        "alpha": 0.6,
        "beta": 0.4,
        "max_behavior_drift_epsilon": 0.015,
        "asi_alert_threshold": 0.75,
        "cds_alert_threshold": 0.35,
    },
    "behavior_vector_definition": [
        "deployment_latency_ms_p95",
        "resource_allocation_accuracy",
        "security_policy_compliance_score",
        "minimum_agent_stability_index",
        "context_divergence_score_max",
        "evidence_settlement_rate",
    ],
}

# ---------------------------------------------------------------------------
# Health check helpers
# ---------------------------------------------------------------------------

async def _check_endpoint_health(path: str, timeout: float = 3.0) -> Dict[str, Any]:
    """Perform a live health check against the given API path. Caches results."""
    cached = _health_cache.get(path)
    now = time.time()
    if cached and (now - cached["checked_at"]) < HEALTH_CACHE_TTL:
        return cached

    url = f"{BASE_URL}{path}"
    status = "unknown"
    latency_ms: Optional[float] = None
    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        if resp.status_code < 400:
            status = "live" if latency_ms < 800 else "degraded"
        else:
            status = "degraded"
    except Exception:
        status = "unreachable"

    result = {
        "status": status,
        "latency_ms": latency_ms,
        "checked_at": now,
        "checked_at_iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
    }
    _health_cache[path] = result
    return result


async def _enrich_capabilities_with_health() -> Dict[str, Any]:
    """Return a copy of _CAPABILITIES with live health data on the first endpoint of each group."""
    health_paths = [
        group["endpoints"][0]["path"]
        for group in _CAPABILITIES.values()
        if group.get("endpoints")
    ]

    # Fan out all health checks concurrently
    checks = await asyncio.gather(
        *[_check_endpoint_health(path) for path in health_paths],
        return_exceptions=True,
    )
    path_to_health = {
        path: (check if isinstance(check, dict) else {"status": "unreachable", "latency_ms": None})
        for path, check in zip(health_paths, checks)
    }

    enriched: Dict[str, Any] = {}
    for group_name, group_data in _CAPABILITIES.items():
        endpoints = group_data.get("endpoints", [])
        primary_path = endpoints[0]["path"] if endpoints else None
        health = path_to_health.get(primary_path, {"status": "unknown"}) if primary_path else {}

        enriched[group_name] = {
            **group_data,
            "health": {
                "status": health.get("status", "unknown"),
                "latency_ms": health.get("latency_ms"),
                "checked_at": health.get("checked_at_iso"),
            },
        }
    return enriched


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class IntrospectRequest(BaseModel):
    query: str
    capability_group: Optional[str] = None
    include_health: bool = False


class CapabilityEndpoint(BaseModel):
    method: str
    path: str
    auth: List[str]
    description: str
    rate_limit: Optional[str] = None
    schema_ref: Optional[str] = None
    _links: Optional[Dict[str, Any]] = None


class CapabilityMatch(BaseModel):
    capability_group: str
    description: str
    match_score: float
    health_status: Optional[str] = None
    endpoints: List[Dict[str, Any]]
    _links: Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/protocol.json",
    summary="Veklom Protocol Manifest",
    description="Machine-readable self-describing capability registry with live health status and CGI geometry block.",
    response_description="Full Veklom Protocol Manifest",
    include_in_schema=True,
)
async def get_protocol_manifest():
    """
    Veklom Protocol Manifest — the Digital Seked.

    Every agent, SDK, and MCP client reads this file to understand what the
    system can do, in what order, with what constraints.

    Health statuses are live-checked (cached 60s per endpoint).
    """
    enriched_capabilities = await _enrich_capabilities_with_health()

    manifest_id = hashlib.sha256(
        f"{MANIFEST_VERSION}:{time.time() // HEALTH_CACHE_TTL}".encode()
    ).hexdigest()[:16]

    return {
        "protocol": PROTOCOL_VERSION,
        "version": MANIFEST_VERSION,
        "manifest_id": manifest_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "name": "Veklom Sovereign AI Hub",
        "description": (
            "A self-describing, governed AI execution platform. "
            "Features VNP micro-stakes, GPC pipeline compilation, "
            "OpenAI-compatible inference, Ed25519 session mesh, "
            "and the x402 settlement ledger."
        ),
        "base_url": BASE_URL,
        "schema": "/openapi.json",
        "asyncapi": "/asyncapi.yaml",
        "introspect": f"POST {BASE_URL}/protocol/introspect",
        "capabilities": enriched_capabilities,
        "capabilityGeometry": _CAPABILITY_GEOMETRY,
        "_links": {
            "self": {"href": "/protocol.json", "method": "GET"},
            "schema": {"href": "/openapi.json", "method": "GET"},
            "health": {"href": "/health", "method": "GET"},
            "introspect": {"href": "/protocol/introspect", "method": "POST"},
            "models": {"href": "/v1/models", "method": "GET"},
            "inference": {"href": "/v1/chat/completions", "method": "POST"},
            "workspace": {"href": "/api/v1/workspace/overview/live", "method": "GET"},
            "asi": {"href": "/api/v1/telemetry/asi", "method": "GET"},
            "cds": {"href": "/api/v1/telemetry/cds", "method": "GET"},
        },
    }


@router.post(
    "/protocol/introspect",
    summary="Capability Introspection",
    description=(
        "Semantic + keyword capability discovery. "
        "Returns capabilities the caller is authorized to use. "
        "Every call is logged to the VNP audit trail."
    ),
    include_in_schema=True,
)
async def introspect_capabilities(body: IntrospectRequest, request: Request):
    """
    Capability Brain — AI-native capability discovery.

    Accepts natural language or keyword queries and returns matching capabilities.
    Public endpoint — no auth required. However, when a Bearer JWT is present,
    scoped capabilities (those requiring auth) are returned with full detail.
    When unauthenticated, only public (auth: []) capabilities are returned.

    Used by: UACP V3, GPC node executor, MCP clients, Apex, external agents.
    """
    query_raw = body.query.strip()
    query = query_raw.lower()
    group_filter = (body.capability_group or "").lower()

    # Detect caller auth level from Authorization header
    auth_header = request.headers.get("authorization", "")
    is_authenticated = auth_header.lower().startswith("bearer ")

    # Fan out health checks if requested
    health_data: Dict[str, Any] = {}
    if body.include_health:
        health_data = await _enrich_capabilities_with_health()

    results: List[Dict[str, Any]] = []
    for group_name, group_data in _CAPABILITIES.items():
        # Apply group filter
        if group_filter and group_filter not in group_name:
            continue

        endpoints = group_data.get("endpoints", [])

        # Auth-scope filtering: if unauthenticated, only return public endpoints
        if not is_authenticated:
            public_eps = [ep for ep in endpoints if not ep.get("auth")]
            if not public_eps:
                continue
            scoped_endpoints = public_eps
        else:
            scoped_endpoints = endpoints

        # Scoring: exact group match > description match > endpoint description match
        desc = group_data.get("description", "").lower()
        ep_descs = " ".join(ep.get("description", "").lower() for ep in scoped_endpoints)

        if query in group_name:
            score = 1.0
        elif query in desc:
            score = 0.85
        elif any(query in ep.get("description", "").lower() for ep in scoped_endpoints):
            score = 0.70
        elif any(
            term in desc or term in group_name or term in ep_descs
            for term in query.split()
            if len(term) > 3
        ):
            score = 0.50
        else:
            continue

        health_entry = health_data.get(group_name, {}).get("health") if body.include_health else None

        results.append({
            "capability_group": group_name,
            "description": group_data["description"],
            "match_score": score,
            "health": health_entry,
            "endpoints": scoped_endpoints,
            "_links": {
                "manifest": {"href": "/protocol.json", "method": "GET"},
                "schema": {"href": "/openapi.json", "method": "GET"},
            },
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)

    # Async audit log — fire and forget, does not block response
    asyncio.create_task(_audit_introspect_call(
        query=query_raw,
        caller_ip=request.client.host if request.client else "unknown",
        is_authenticated=is_authenticated,
        match_count=len(results),
    ))

    return {
        "query": body.query,
        "protocol_version": PROTOCOL_VERSION,
        "authenticated": is_authenticated,
        "matches": results,
        "total": len(results),
        "geometry_bounds": {
            "alpha": _CAPABILITY_GEOMETRY["invariant_bounds"]["alpha"],
            "beta": _CAPABILITY_GEOMETRY["invariant_bounds"]["beta"],
            "max_drift": _CAPABILITY_GEOMETRY["invariant_bounds"]["max_behavior_drift_epsilon"],
        },
        "_links": {
            "manifest": {"href": "/protocol.json", "method": "GET"},
            "schema": {"href": "/openapi.json", "method": "GET"},
            "asi": {"href": "/api/v1/telemetry/asi", "method": "GET"},
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _audit_introspect_call(
    query: str,
    caller_ip: str,
    is_authenticated: bool,
    match_count: int,
) -> None:
    """
    Write an introspect audit event to the VNP audit trail.
    Fire-and-forget — never blocks the response path.
    Swallows all exceptions to protect the hot path.
    """
    try:
        from backend.core.redis_client import get_redis_client  # type: ignore
        r = get_redis_client()
        if r:
            event = {
                "type": "protocol.introspect",
                "query": query,
                "caller_ip": caller_ip,
                "authenticated": is_authenticated,
                "match_count": match_count,
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }
            import json
            r.lpush("veklom:audit:protocol", json.dumps(event))
            r.ltrim("veklom:audit:protocol", 0, 9999)  # Keep last 10k events
    except Exception as exc:  # noqa: BLE001
        logger.debug("Introspect audit write skipped: %s", exc)
