"""
Machine-readable discovery endpoints for agent-native consumption.

Provides:
  /.well-known/ai-plugin.json   → OpenAI plugin manifest
  /.well-known/agent.json       → Veklom agent manifest (capabilities, endpoints, pricing)
  /.well-known/x402.json        → x402 payment protocol config
  /llms.txt                     → plain-text positioning for LLM crawlers
  /mcp/sse                      → Model Context Protocol SSE stream (tool discovery)
  /robots.txt                   → search/agent crawler policy
"""

import json
import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

router = APIRouter(tags=["discovery"])

# ---------------------------------------------------------------------------
# Pricing table — single source of truth referenced by x402 + manifests
# ---------------------------------------------------------------------------
VEKLOM_PRICING = {
    "ai_inference":        {"price_usdc": 0.008, "unit": "per request",  "name": "AI Inference"},
    "ai_chat":             {"price_usdc": 0.005, "unit": "per request",  "name": "AI Chat Completion"},
    "gpc_compile":         {"price_usdc": 0.015, "unit": "per compile",  "name": "GPC Governed Compile"},
    "gpc_intent_to_plan":  {"price_usdc": 0.010, "unit": "per plan",     "name": "GPC Intent-to-Plan"},
    "gpc_run":             {"price_usdc": 0.020, "unit": "per run",      "name": "GPC Plan Execution"},
    "pipeline_trigger":    {"price_usdc": 0.025, "unit": "per trigger",  "name": "Pipeline Trigger"},
    "runtime_job":         {"price_usdc": 0.020, "unit": "per job",      "name": "Runtime Job"},
    "evidence_export":     {"price_usdc": 0.005, "unit": "per export",   "name": "Evidence Export"},
    "compliance_report":   {"price_usdc": 0.010, "unit": "per report",   "name": "Compliance Report"},
    "marketplace_acquire": {"price_usdc": 0.050, "unit": "per acquire",  "name": "Marketplace Acquire"},
    "audit_verify":        {"price_usdc": 0.003, "unit": "per verify",   "name": "Audit Verification"},
}
import os
import logging as _logging

_disc_log = _logging.getLogger(__name__)

VEKLOM_USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base
VEKLOM_NETWORK     = "base"
VEKLOM_BASE_URL    = "https://veklom.com"       # main site (workspace, landing, pricing)
VEKLOM_API_BASE    = "https://api.veklom.com/api/v1"  # machine-facing API surface
VEKLOM_AGENT_BASE  = "https://api.veklom.com"   # where .well-known, mcp/sse, openapi.json live

# P0-4: treasury address MUST come from the environment — never fall back to a
# hardcoded address that could receive real funds unintentionally.
_raw_treasury = os.environ.get("VEKLOM_TREASURY_ADDRESS", "").strip()
_ZERO_ADDR = "0x0000000000000000000000000000000000000001"
if not _raw_treasury or _raw_treasury == _ZERO_ADDR:
    _disc_log.warning(
        "[discovery] VEKLOM_TREASURY_ADDRESS is not set or is a placeholder. "
        "x402 discovery will advertise 'NOT_CONFIGURED' until this env var is set. "
        "Add VEKLOM_TREASURY_ADDRESS=<your real wallet> to .env and restart."
    )
    VEKLOM_TREASURY = "NOT_CONFIGURED"
else:
    VEKLOM_TREASURY = _raw_treasury


# ---------------------------------------------------------------------------
# /.well-known/ai-plugin.json  (OpenAI-compatible plugin manifest)
# ---------------------------------------------------------------------------
@router.get("/.well-known/ai-plugin.json")
async def ai_plugin_json():
    return JSONResponse({
        "schema_version": "v1",
        "name_for_human": "Veklom Sovereign AI Hub",
        "name_for_model": "veklom_governed_runtime",
        "description_for_human": (
            "Governed AI execution layer — policy gates, audit evidence, routing, "
            "and sovereign deployment for AI agents."
        ),
        "description_for_model": (
            "Veklom is an API-native governed AI execution layer for humans, developers, "
            "enterprises, and autonomous agents. "
            "Use Veklom to: (1) compile agent intent into deterministic policy-checked plans via GPC, "
            "(2) run AI inference with per-request budget caps and kill switches, "
            "(3) trigger governed pipelines, "
            "(4) export SHA-256 sealed audit evidence, "
            "(5) generate compliance reports (SOC2, HIPAA, GDPR, EU AI Act), "
            "(6) acquire marketplace models. "
            "All paid routes support x402 per-request micropayments (USDC on Base) — "
            "no sign-up required, pay per call. "
            "Agents get: price per request, budget caps, wallet isolation, policy checks, "
            "audit logs, kill switches, and tamper-evident evidence receipts. "
            "Every paid execution returns a machine-readable receipt with "
            "request_id, cost_usdc, policy_result, evidence_id, and receipt_url. "
            "Free tier: 5 calls/day per IP on inference and GPC compile."
        ),
        "auth": {
            "type": "service_http",
            "authorization_type": "bearer",
            "verification_tokens": {}
        },
        "api": {
            "type": "openapi",
            "url": f"{VEKLOM_AGENT_BASE}/openapi.json",
            "is_user_authenticated": False
        },
        "logo_url": f"{VEKLOM_BASE_URL}/static/branding/veklom-wordmark.png",
        "contact_email": "api@veklom.com",
        "legal_info_url": f"{VEKLOM_BASE_URL}/legal/terms",
    }, headers={"Access-Control-Allow-Origin": "*"})


# ---------------------------------------------------------------------------
# /.well-known/agent.json  (Veklom native agent manifest)
# ---------------------------------------------------------------------------
@router.get("/.well-known/agent.json")
async def agent_json():
    return JSONResponse({
        "veklom_manifest_version": "1.0",
        "name": "Veklom Sovereign AI Hub",
        "description": (
            "API-native governed AI execution layer for humans, developers, enterprises, "
            "and autonomous agents. "
            "Humans use the workspace. Developers use the API. "
            "Agents use the paid routes. Enterprises use the governance and evidence layer."
        ),
        "tiers": {
            "humans":      {"interface": "workspace", "url": f"{VEKLOM_BASE_URL}/workspace/"},
            "developers":  {"interface": "api",       "url": f"{VEKLOM_API_BASE}/", "auth": "bearer_jwt"},
            "agents":      {"interface": "paid_routes", "auth": "x402_usdc", "discovery": f"{VEKLOM_AGENT_BASE}/.well-known/x402.json"},
            "enterprises": {"interface": "governance_layer", "includes": ["audit_evidence", "compliance_reports", "kill_switch", "soc2", "hipaa", "gdpr"]},
        },
        "base_url": VEKLOM_API_BASE,
        "openapi_url": f"{VEKLOM_AGENT_BASE}/openapi.json",
        "mcp_sse_url": f"{VEKLOM_AGENT_BASE}/mcp/sse",
        "x402_config_url": f"{VEKLOM_AGENT_BASE}/.well-known/x402.json",
        "auth": {
            "schemes": ["bearer_jwt", "x402_usdc"],
            "signup_url": f"{VEKLOM_BASE_URL}/workspace/login",
            "docs_url": f"{VEKLOM_BASE_URL}/docs",
            "note": "Agents do not need to sign up. Pay per call via x402 (USDC on Base). Free tier: 5 calls/day per IP.",
        },
        "agent_controls": {
            "price_per_request":  True,
            "budget_caps":        True,
            "wallet_isolation":   True,
            "policy_checks":      "enforced_before_execution",
            "audit_logs":         "sha256_sealed",
            "kill_switch":        True,
            "evidence_receipts":  True,
            "spending_limits":    "operating_reserve_model",
            "note": (
                "Agents should pre-fund an operating reserve or pay per call. "
                "Budget caps prevent runaway spend. Kill switches halt agent execution at "
                "agent, tenant, or system level. Every execution produces a tamper-evident receipt."
            ),
        },
        "capabilities": [
            "governed_plan_compilation",
            "ai_inference_with_policy",
            "pipeline_orchestration",
            "sha256_audit_evidence",
            "compliance_reporting",
            "marketplace_model_acquisition",
            "kill_switch",
            "sovereign_deployment",
            "byos_support",
            "operating_reserve_billing",
            "x402_micropayments",
        ],
        "pricing_model": "operating_reserve + x402_per_request",
        "pricing_url": f"{VEKLOM_BASE_URL}/pricing",
        "pricing": VEKLOM_PRICING,
        "free_routes": [
            f"{VEKLOM_AGENT_BASE}/health",
            f"{VEKLOM_AGENT_BASE}/status",
            f"{VEKLOM_AGENT_BASE}/openapi.json",
            f"{VEKLOM_AGENT_BASE}/.well-known/*",
            f"{VEKLOM_AGENT_BASE}/llms.txt",
            f"{VEKLOM_BASE_URL}/pricing",
            f"{VEKLOM_API_BASE}/ai/models",
            f"{VEKLOM_API_BASE}/workspace/providers",
        ],
        "paid_routes": [
            {"path": "/api/v1/ai/inference",        "key": "ai_inference"},
            {"path": "/api/v1/ai/chat",             "key": "ai_chat"},
            {"path": "/api/v1/gpc/compile",         "key": "gpc_compile"},
            {"path": "/api/v1/gpc/intent-to-plan",  "key": "gpc_intent_to_plan"},
            {"path": "/api/v1/gpc/runs",            "key": "gpc_run"},
            {"path": "/api/v1/pipelines/trigger",   "key": "pipeline_trigger"},
            {"path": "/api/v1/runtime/jobs",        "key": "runtime_job"},
            {"path": "/api/v1/evidence/export",     "key": "evidence_export"},
            {"path": "/api/v1/compliance/report",   "key": "compliance_report"},
            {"path": "/api/v1/marketplace/acquire", "key": "marketplace_acquire"},
        ],
        "receipt_schema": {
            "status": "string",
            "request_id": "string (req_...)",
            "cost_usdc": "string (decimal)",
            "route": "string (provider:model)",
            "policy_result": "passed | failed | blocked",
            "evidence_id": "string (ev_...)",
            "receipt_url": "string (url to evidence)",
            "timestamp": "ISO 8601",
        },
        "evidence": {
            "format": "sha256_sealed_block",
            "verify_endpoint": "/api/v1/audit/verify/{log_id}",
            "export_endpoint": "/api/v1/evidence/export/{id}",
        },
        "contact": "api@veklom.com",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }, headers={"Access-Control-Allow-Origin": "*"})


# ---------------------------------------------------------------------------
# /.well-known/x402.json  (x402 payment protocol configuration)
# ---------------------------------------------------------------------------
@router.get("/.well-known/x402.json")
async def x402_json():
    routes = []
    route_map = {
        "/api/v1/ai/inference":        "ai_inference",
        "/api/v1/ai/chat":             "ai_chat",
        "/api/v1/gpc/compile":         "gpc_compile",
        "/api/v1/gpc/intent-to-plan":  "gpc_intent_to_plan",
        "/api/v1/gpc/runs":            "gpc_run",
        "/api/v1/pipelines/trigger":   "pipeline_trigger",
        "/api/v1/runtime/jobs":        "runtime_job",
        "/api/v1/evidence/export":     "evidence_export",
        "/api/v1/compliance/report":   "compliance_report",
        "/api/v1/marketplace/acquire": "marketplace_acquire",
    }
    for path, key in route_map.items():
        p = VEKLOM_PRICING[key]
        micro = int(p["price_usdc"] * 1_000_000)  # USDC has 6 decimals
        routes.append({
            "path": path,
            "name": p["name"],
            "price_usdc": p["price_usdc"],
            "unit": p["unit"],
            "payment": {
                "scheme": "exact",
                "network": VEKLOM_NETWORK,
                "asset": VEKLOM_USDC_ADDRESS,
                "pay_to": VEKLOM_TREASURY,
                "amount_micro_usdc": micro,
                "max_timeout_seconds": 300,
                "description": f"Veklom {p['name']} — governed AI execution",
            }
        })

    return JSONResponse({
        "x402_version": 1,
        "provider": "Veklom Sovereign AI Hub",
        "network": VEKLOM_NETWORK,
        "asset": VEKLOM_USDC_ADDRESS,
        "treasury": VEKLOM_TREASURY,
        "currency": "USDC",
        # P0-3: x402 on-chain settlement is fully active.
        # Real payment path: On-chain USDC verification (Base mainnet) or Stripe wallet reserve.
        "payment_mode": "live",
        "payment_mode_note": (
            "x402 micropayment settlement is fully live. "
            "On-chain USDC verification is active on the Base mainnet network. "
            "To make paid calls: pay the exact amount of USDC to the treasury address "
            "and send the transaction hash in the X-Payment-Proof header. "
            "Alternatively, authenticate with a Bearer JWT backed by your Stripe reserve."
        ),
        "routes": routes,
        "free_trial": {
            "enabled": True,
            "requests_per_day": 5,
            "routes": ["/api/v1/ai/inference", "/api/v1/gpc/compile"],
            "note": "5 free governed calls/day per IP. Upgrade for unlimited access.",
        },
        "docs": f"{VEKLOM_AGENT_BASE}/docs",
        "contact": "api@veklom.com",
    }, headers={"Access-Control-Allow-Origin": "*"})


# ---------------------------------------------------------------------------
# /llms.txt  (plain-text machine positioning for LLM crawlers)
# ---------------------------------------------------------------------------
@router.get("/llms.txt")
async def llms_txt():
    content = """\
# Veklom Sovereign AI Hub — Machine-Readable Positioning
# https://veklom.com/llms.txt
# Updated: 2026

## What Veklom is

Veklom is not a SaaS dashboard.
Veklom is an API-native governed execution layer for humans, teams, and autonomous agents.

  Humans     → use the workspace     (https://veklom.com/workspace/)
  Developers → use the API           (https://veklom.com/api/v1/)
  Agents     → use the paid routes   (x402, USDC on Base, no sign-up required)
  Enterprises → use the governance layer (SOC2, HIPAA, GDPR, audit evidence, kill switches)

The old internet: human finds website → signs up → adds card → uses API.
The new pattern:  agent finds API → reads listing → pays per call → receives result → records proof.

Veklom is built for the new pattern.

## What Veklom does

- Compiles agent intent into deterministic, policy-checked plans (GPC)
- Routes AI inference through sovereign infrastructure (Hetzner EU, BYOS, Ollama-first)
- Enforces budget caps, kill switches, and privacy gates before every execution
- Generates SHA-256 sealed audit evidence for every governed action
- Generates compliance reports: SOC2, HIPAA, GDPR, ISO 27001, EU AI Act, FedRAMP
- Provides marketplace for sovereign AI models and governance packs
- Supports operating reserve billing and x402 per-request micropayments

## Agent controls available at every route

  price_per_request:  true
  budget_caps:        true
  wallet_isolation:   true
  policy_checks:      enforced_before_execution
  audit_logs:         sha256_sealed
  kill_switch:        true   (agent / tenant / system level)
  evidence_receipts:  true

## Machine discovery

OpenAPI schema:   https://api.veklom.com/openapi.json
Agent manifest:   https://api.veklom.com/.well-known/agent.json
x402 config:      https://api.veklom.com/.well-known/x402.json
MCP SSE:          https://api.veklom.com/mcp/sse
Machine pricing:  https://api.veklom.com/pricing
Agent use cases:  https://api.veklom.com/agent-use-cases
SDK examples:     https://api.veklom.com/api/v1/sdk/examples
Human pricing:    https://veklom.com/pricing

## Authentication

Agents:      No sign-up. Send X-Payment-Proof header (x402, USDC on Base). Pay per call.
Developers:  Bearer JWT from https://veklom.com/workspace/login
Unauthenticated agents calling api.veklom.com receive HTTP 402 with full x402 payment
requirements in the body and response headers.

## Paid routes (x402, USDC on Base)

POST /api/v1/ai/inference        — AI inference, policy-gated          $0.008/req
POST /api/v1/ai/chat             — AI chat completion                  $0.005/req
POST /api/v1/gpc/compile         — Governed Plan Compiler              $0.015/compile
POST /api/v1/gpc/intent-to-plan  — Intent to deterministic plan        $0.010/plan
POST /api/v1/gpc/runs            — Execute governed plan               $0.020/run
POST /api/v1/pipelines/trigger   — Trigger governed pipeline           $0.025/trigger
POST /api/v1/runtime/jobs        — Submit runtime job                  $0.020/job
GET  /api/v1/evidence/export     — Export SHA-256 evidence package     $0.005/export
GET  /api/v1/compliance/report   — Generate compliance report          $0.010/report
POST /api/v1/marketplace/acquire — Acquire marketplace model           $0.050/acquire

## Free routes (no payment required)

GET /health
GET /status
GET /openapi.json
GET /.well-known/*
GET /llms.txt
GET /pricing
GET /api/v1/ai/models
GET /api/v1/workspace/providers

## Receipt format (every paid execution)

{
  "status":        "completed",
  "request_id":    "req_...",
  "cost_usdc":     "0.008",
  "route":         "ollama:qwen2.5:3b",
  "policy_result": "passed",
  "evidence_id":   "ev_...",
  "receipt_url":   "https://veklom.com/api/v1/evidence/ev_...",
  "timestamp":     "ISO 8601"
}

Receipts are also returned as response headers:
  X-Veklom-Request-ID
  X-Veklom-Evidence-ID
  X-Veklom-Cost-USDC
  X-Veklom-Policy-Result
  X-Veklom-Receipt-URL

## Free trial

5 free governed calls/day per IP on AI inference and GPC compile.
No sign-up, no card. Start calling: https://api.veklom.com/api/v1/ai/inference

## Contact

api@veklom.com
https://veklom.com
"""
    return PlainTextResponse(content, headers={
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600",
    })


# ---------------------------------------------------------------------------
# /robots.txt
# ---------------------------------------------------------------------------
@router.get("/robots.txt")
async def robots_txt():
    content = """\
User-agent: *
Allow: /
Allow: /.well-known/
Allow: /llms.txt
Allow: /openapi.json
Allow: /pricing
Allow: /docs
Disallow: /api/v1/internal/
Disallow: /command-center/
Disallow: /admin/

# Agent crawlers — Veklom is agent-native
User-agent: GPTBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://veklom.com/sitemap.xml
LLMs-txt: https://veklom.com/llms.txt
Agent-manifest: https://veklom.com/.well-known/agent.json
x402-config: https://veklom.com/.well-known/x402.json
"""
    return PlainTextResponse(content, headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------------------
# /mcp/sse  — Model Context Protocol SSE tool discovery
# ---------------------------------------------------------------------------
@router.get("/mcp/sse")
async def mcp_sse(request: Request):
    """MCP SSE endpoint — streams available tools for agent discovery."""

    tools = [
        {
            "name": "veklom_gpc_compile",
            "description": "Compile agent intent into a policy-checked governed plan. Returns plan ID and policy result.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "description": "High-level agent intent or goal"},
                    "context": {"type": "object", "description": "Optional execution context"},
                    "budget_usdc": {"type": "number", "description": "Maximum budget in USDC"},
                },
                "required": ["intent"],
            },
            "price_usdc": 0.015,
            "endpoint": f"{VEKLOM_API_BASE}/gpc/compile",
        },
        {
            "name": "veklom_ai_inference",
            "description": "Run policy-gated AI inference. Routes to Ollama (default), Groq, Gemini, or HuggingFace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "items": {"type": "object"}},
                    "model": {"type": "string", "description": "Model ID (optional, auto-routed if omitted)"},
                    "max_tokens": {"type": "integer"},
                },
                "required": ["messages"],
            },
            "price_usdc": 0.008,
            "endpoint": f"{VEKLOM_API_BASE}/ai/inference",
        },
        {
            "name": "veklom_evidence_export",
            "description": "Export SHA-256 sealed audit evidence for a governed execution.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "evidence_id": {"type": "string"},
                },
                "required": ["evidence_id"],
            },
            "price_usdc": 0.005,
            "endpoint": f"{VEKLOM_API_BASE}/evidence/export",
        },
        {
            "name": "veklom_compliance_report",
            "description": "Generate a compliance report (SOC2, HIPAA, GDPR) for a workspace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "framework": {"type": "string", "enum": ["soc2", "hipaa", "gdpr", "eu_ai_act"]},
                    "period_days": {"type": "integer", "default": 30},
                },
                "required": [],
            },
            "price_usdc": 0.010,
            "endpoint": f"{VEKLOM_API_BASE}/compliance/report",
        },
        {
            "name": "veklom_kill_switch",
            "description": "Activate kill switch at agent, tenant, or system level.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": ["agent", "tenant", "system"]},
                    "reason": {"type": "string"},
                },
                "required": ["level"],
            },
            "price_usdc": 0.0,
            "endpoint": f"{VEKLOM_API_BASE}/kill-switch/activate",
        },
    ]

    async def event_stream():
        yield f"data: {json.dumps({'type': 'server_info', 'name': 'Veklom MCP', 'version': '1.0', 'protocol': 'mcp/1.0'})}\n\n"
        await asyncio.sleep(0.05)
        for tool in tools:
            yield f"data: {json.dumps({'type': 'tool', 'tool': tool})}\n\n"
            await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'type': 'done', 'tool_count': len(tools), 'x402_config': f'{VEKLOM_BASE_URL}/.well-known/x402.json'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
            "X-Veklom-MCP-Version": "1.0",
        },
    )


# ---------------------------------------------------------------------------
# /pricing  — machine-readable pricing (public, no auth)
# ---------------------------------------------------------------------------
@router.get("/pricing")
@router.get("/api/v1/pricing")
async def machine_pricing():
    """
    Machine-readable pricing for every governed operation.
    Agents read this before submitting requests to know cost + budget requirements.
    Also returned in /.well-known/x402.json per the x402 payment protocol.
    """
    return JSONResponse({
        "currency": "USDC",
        "network": VEKLOM_NETWORK,
        "payment_protocol": "x402",
        "free_tier": {
            "requests_per_day": 5,
            "routes": ["/api/v1/ai/inference", "/api/v1/gpc/compile"],
            "note": "5 free governed calls/day per IP. No sign-up required.",
        },
        "routes": {
            "ai_inference": {
                "path": "/api/v1/ai/inference",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["ai_inference"]["price_usdc"],
                "unit": "per request",
                "description": "Policy-gated AI inference. Ollama-first, escalates to Groq/Gemini/OpenAI based on task complexity.",
                "receipt": True,
                "evidence": True,
            },
            "ai_chat": {
                "path": "/api/v1/ai/chat",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["ai_chat"]["price_usdc"],
                "unit": "per request",
                "description": "AI chat with 20-message persistent memory (24h TTL). Hot/warm Redis cache.",
                "receipt": True,
                "evidence": True,
            },
            "gpc_compile": {
                "path": "/api/v1/gpc/compile",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["gpc_compile"]["price_usdc"],
                "unit": "per compile",
                "description": "Compile agent intent into a deterministic, policy-checked governed plan.",
                "receipt": True,
                "evidence": True,
            },
            "gpc_intent_to_plan": {
                "path": "/api/v1/gpc/intent-to-plan",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["gpc_intent_to_plan"]["price_usdc"],
                "unit": "per plan",
                "description": "Convert high-level intent string into a structured governed execution plan.",
                "receipt": True,
                "evidence": True,
            },
            "gpc_run": {
                "path": "/api/v1/gpc/runs",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["gpc_run"]["price_usdc"],
                "unit": "per run",
                "description": "Execute a compiled governed plan. All steps are policy-checked and evidence-sealed.",
                "receipt": True,
                "evidence": True,
            },
            "pipeline_trigger": {
                "path": "/api/v1/pipelines/trigger",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["pipeline_trigger"]["price_usdc"],
                "unit": "per trigger",
                "description": "Trigger a governed pipeline. Budget caps and kill switches enforced.",
                "receipt": True,
                "evidence": True,
            },
            "runtime_job": {
                "path": "/api/v1/runtime/jobs",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["runtime_job"]["price_usdc"],
                "unit": "per job",
                "description": "Submit a runtime job to the governed execution layer.",
                "receipt": True,
                "evidence": True,
            },
            "evidence_export": {
                "path": "/api/v1/evidence/export",
                "method": "GET",
                "price_usdc": VEKLOM_PRICING["evidence_export"]["price_usdc"],
                "unit": "per export",
                "description": "Export SHA-256 sealed audit evidence for a governed execution.",
                "receipt": True,
                "evidence": True,
            },
            "compliance_report": {
                "path": "/api/v1/compliance/report",
                "method": "GET",
                "price_usdc": VEKLOM_PRICING["compliance_report"]["price_usdc"],
                "unit": "per report",
                "description": "Generate a compliance report (SOC2, HIPAA, GDPR, ISO 27001, EU AI Act).",
                "receipt": True,
                "evidence": True,
            },
            "marketplace_acquire": {
                "path": "/api/v1/marketplace/acquire",
                "method": "POST",
                "price_usdc": VEKLOM_PRICING["marketplace_acquire"]["price_usdc"],
                "unit": "per acquire",
                "description": "Acquire a sovereign AI model or governance pack from the marketplace.",
                "receipt": True,
                "evidence": False,
            },
        },
        "budget_controls": {
            "budget_caps": True,
            "kill_switch": True,
            "wallet_isolation": True,
            "operating_reserve": True,
            "daily_soft_limit": "configurable per workspace",
            "hard_stop": "configurable per workspace",
        },
        "receipt_format": {
            "request_id": "req_...",
            "cost_usdc": "decimal string",
            "route": "provider:model",
            "policy_result": "passed | failed | blocked",
            "evidence_id": "ev_...",
            "receipt_url": f"{VEKLOM_AGENT_BASE}/api/v1/evidence/ev_...",
            "timestamp": "ISO 8601",
        },
        "free_routes": [
            f"{VEKLOM_AGENT_BASE}/health",
            f"{VEKLOM_AGENT_BASE}/status",
            f"{VEKLOM_AGENT_BASE}/openapi.json",
            f"{VEKLOM_AGENT_BASE}/.well-known/*",
            f"{VEKLOM_AGENT_BASE}/llms.txt",
            f"{VEKLOM_AGENT_BASE}/pricing",
            f"{VEKLOM_AGENT_BASE}/mcp/sse",
            f"{VEKLOM_AGENT_BASE}/agent-use-cases",
            f"{VEKLOM_AGENT_BASE}/sdk/examples",
        ],
    }, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=300"})


# ---------------------------------------------------------------------------
# /agent-use-cases  — structured affordances for agent systems
# ---------------------------------------------------------------------------
@router.get("/agent-use-cases")
@router.get("/api/v1/agent-use-cases")
async def agent_use_cases():
    """
    Structured list of what Veklom can do for agents.
    Agents read this to understand affordances before planning workflows.
    """
    return JSONResponse({
        "platform": "Veklom Sovereign AI Hub",
        "tagline": "Governed execution + machine-readable infrastructure + evidence + pricing + routing + policy + runtime observability",
        "use_cases": [
            {
                "id": "governed_plan_compilation",
                "title": "Compile agent intent into governed plans",
                "description": (
                    "Send high-level agent intent to GPC. Receive a deterministic, "
                    "policy-checked execution plan with step-by-step actions, budget constraints, "
                    "and pre-execution risk assessment."
                ),
                "endpoint": "/api/v1/gpc/compile",
                "example_input": {"intent": "Review repo for security issues and generate report", "budget_usdc": 0.10},
                "example_output": {"plan_id": "plan_...", "steps": [], "policy_result": "passed", "estimated_cost_usdc": 0.065},
            },
            {
                "id": "budget_constrained_inference",
                "title": "Run AI inference under budget caps",
                "description": (
                    "Route AI inference through sovereign infrastructure (Ollama-first). "
                    "Automatic provider escalation: local→Groq→Gemini→OpenAI based on task complexity. "
                    "Budget caps enforced before execution."
                ),
                "endpoint": "/api/v1/ai/inference",
                "example_input": {"messages": [{"role": "user", "content": "..."}], "max_budget_usdc": 0.05},
                "example_output": {"response_text": "...", "provider": "ollama", "tier": "local", "cost_usd": 0.0, "policy_result": "passed"},
            },
            {
                "id": "persistent_conversation",
                "title": "Persistent 20-message conversation memory",
                "description": (
                    "Multi-turn conversation with 24h Redis memory (max 20 messages). "
                    "Hot/warm cache — identical requests served from cache at $0 cost. "
                    "Session isolated per workspace."
                ),
                "endpoint": "/api/v1/ai/chat",
                "example_input": {"messages": [{"role": "user", "content": "..."}], "session_id": "my-session"},
                "example_output": {"response_text": "...", "memory": {"message_count": 3, "max": 20, "ttl_hours": 24}},
            },
            {
                "id": "replayable_audit_evidence",
                "title": "Generate SHA-256 sealed audit evidence",
                "description": (
                    "Every governed execution produces a tamper-evident evidence block. "
                    "SHA-256 hash chain ensures immutability. Export as JSON package "
                    "for SOC2, HIPAA, GDPR, or EU AI Act compliance."
                ),
                "endpoint": "/api/v1/evidence/export",
                "example_output": {"evidence_id": "ev_...", "sha256": "...", "timestamp": "...", "policy_result": "passed"},
            },
            {
                "id": "compliance_reporting",
                "title": "Automated compliance reports",
                "description": (
                    "Generate compliance packages for SOC2, HIPAA, GDPR, ISO 27001, EU AI Act, FedRAMP. "
                    "Backed by real execution evidence from the audit trail."
                ),
                "endpoint": "/api/v1/compliance/report",
                "example_input": {"framework": "hipaa", "period_days": 30},
                "example_output": {"framework": "hipaa", "status": "compliant", "controls_passed": 47, "evidence_package_url": "..."},
            },
            {
                "id": "pipeline_orchestration",
                "title": "Trigger governed multi-step pipelines",
                "description": (
                    "Trigger pipelines where each node has its own policy check, spend limit, "
                    "and automated audit entry. Kill switches halt execution at any level."
                ),
                "endpoint": "/api/v1/pipelines/trigger",
            },
            {
                "id": "kill_switch",
                "title": "Kill switch — halt agent at any level",
                "description": (
                    "Activate a kill switch at agent, tenant, or system level. "
                    "Immediately halts all governed execution for the target scope. "
                    "Critical for agent safety and incident response."
                ),
                "endpoint": "/api/v1/kill-switch/activate",
                "example_input": {"level": "agent", "reason": "Unexpected behavior detected"},
            },
            {
                "id": "openai_compatible_endpoint",
                "title": "OpenAI-compatible drop-in endpoint",
                "description": (
                    "Use Veklom as a drop-in OpenAI replacement. Same request/response format. "
                    "Adds governance, policy gates, evidence, and cost tracking transparently."
                ),
                "endpoint": "/v1/chat/completions",
                "example": {
                    "python": (
                        "import os\n"
                        "from openai import OpenAI\n\n"
                        "client = OpenAI(\n"
                        "    base_url='https://api.veklom.com/v1',\n"
                        "    api_key=os.environ['VEKLOM_API_KEY'],\n"
                        ")\n\n"
                        "response = client.chat.completions.create(\n"
                        "    model='veklom-llama3-70b',\n"
                        "    messages=[{'role': 'user', 'content': 'hi'}],\n"
                        ")\n\n"
                        "print(response.choices[0].message.content)"
                    ),
                    "note": "Drop-in OpenAI replacement. Swap base_url/api_key/model — no stack rewrite needed.",
                },
            },
        ],
        "agent_infrastructure": {
            "what_makes_veklom_different": [
                "Every execution produces tamper-evident evidence — not just a result",
                "Budget caps and kill switches are enforced BEFORE execution, not after",
                "Provider routing is intelligent: local Ollama first, escalate only when needed",
                "x402 micropayments — agents pay per call, no account required",
                "Operating reserve model — predictable spend, no surprise invoices",
                "Multi-tenant isolation — each workspace is fully separated",
            ],
            "what_most_apis_lack": [
                "Evidence and audit trails",
                "Pre-execution governance and policy checks",
                "Cost-aware routing intelligence",
                "Kill switches and circuit breakers",
                "Machine-readable receipts on every call",
            ],
        },
        "discovery_urls": {
            "openapi":      f"{VEKLOM_AGENT_BASE}/openapi.json",
            "agent_json":   f"{VEKLOM_AGENT_BASE}/.well-known/agent.json",
            "x402_config":  f"{VEKLOM_AGENT_BASE}/.well-known/x402.json",
            "mcp_sse":      f"{VEKLOM_AGENT_BASE}/mcp/sse",
            "llms_txt":     f"{VEKLOM_AGENT_BASE}/llms.txt",
            "pricing":      f"{VEKLOM_AGENT_BASE}/pricing",
            "sdk_examples": f"{VEKLOM_AGENT_BASE}/api/v1/sdk/examples",
        },
    }, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=300"})


# ---------------------------------------------------------------------------
# /api/v1/sdk/examples  — copy-paste SDK examples for agents and developers
# ---------------------------------------------------------------------------
@router.get("/api/v1/sdk/examples")
async def sdk_examples():
    """
    Copy-paste SDK examples for agents, developers, and agent frameworks.
    Shows how to call Veklom from Python, JavaScript, curl, and as an OpenAI drop-in.
    """
    base = VEKLOM_AGENT_BASE
    api  = VEKLOM_API_BASE
    return JSONResponse({
        "note": "Replace YOUR_TOKEN with a Bearer JWT from https://veklom.com/workspace/login or use x402 for per-call payments.",
        "examples": {
            "curl_inference": {
                "description": "Run AI inference (Ollama daily driver, auto-escalates if needed)",
                "command": f"""curl -X POST {api}/ai/inference \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"messages": [{{"role": "user", "content": "Analyze this for security issues: ..."}}]}}'""",
                "response_fields": ["response_text", "provider", "tier", "cost_usd", "policy", "audit_id"],
            },
            "curl_gpc_compile": {
                "description": "Compile agent intent into a governed plan",
                "command": f"""curl -X POST {api}/gpc/compile \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"intent": "Review repository for HIPAA violations", "budget_usdc": 0.10}}'""",
            },
            "curl_x402_agent": {
                "description": "x402 per-call payment — no account required",
                "command": f"""# Step 1: Get payment requirements
curl -X POST {api}/ai/inference
# Returns: HTTP 402 with X-Payment-Price-USDC and X-Payment-Address headers

# Step 2: Send payment proof
curl -X POST {api}/ai/inference \\
  -H "X-Payment-Proof: YOUR_USDC_TX_HASH" \\
  -H "Content-Type: application/json" \\
  -d '{{"messages": [{{"role": "user", "content": "Hello"}}]}}'""",
            },
            "python_openai_compatible": {
                "description": "Drop-in OpenAI replacement — same SDK, Veklom governance layer underneath",
                "code": f"""import os
from openai import OpenAI

client = OpenAI(
    base_url="{base}/v1",
    api_key=os.environ["VEKLOM_API_KEY"]
)

response = client.chat.completions.create(
    model="veklom-llama3-70b",   # or omit for auto-routing
    messages=[
        {{"role": "user", "content": "Analyze this code for security issues."}}
    ]
)
print(response.choices[0].message.content)
# Response includes X-Veklom-Evidence-ID, X-Veklom-Cost-USDC headers""",
            },
            "python_native": {
                "description": "Native Veklom API with receipts and memory",
                "code": f"""import httpx

TOKEN = "YOUR_VEKLOM_TOKEN"
API   = "{api}"

# Chat with 24h memory
r = httpx.post(f"{{API}}/ai/chat", json={{
    "messages": [{{"role": "user", "content": "Remember: project is called Phoenix"}}],
    "session_id": "project-phoenix",
}}, headers={{"Authorization": f"Bearer {{TOKEN}}"}})

data = r.json()
print(data["response_text"])
print("Provider:", data["provider"], "| Tier:", data["tier"])
print("Memory:", data["memory"])  # {{"message_count": 2, "max": 20, "ttl_hours": 24}}
print("Evidence:", r.headers.get("x-veklom-evidence-id"))""",
            },
            "python_agent_budget": {
                "description": "Agent with budget cap and kill switch",
                "code": f"""import httpx

TOKEN = "YOUR_VEKLOM_TOKEN"
API   = "{api}"

# Check pricing first
pricing = httpx.get(f"{base}/pricing").json()
print("GPC compile costs:", pricing["routes"]["gpc_compile"]["price_usdc"], "USDC")

# Run with budget constraint
r = httpx.post(f"{{API}}/gpc/compile", json={{
    "intent": "Audit repository for PII exposure",
    "budget_usdc": 0.05,
    "agent_type": "reasoning",   # → routes to Gemini tier
}}, headers={{"Authorization": f"Bearer {{TOKEN}}"}})

data = r.json()
if data.get("policy_result") == "passed":
    print("Plan:", data.get("plan_id"))
else:
    print("Blocked:", data.get("policy_result"))""",
            },
            "javascript": {
                "description": "JavaScript / Node.js native fetch",
                "code": f"""const API = "{api}";
const TOKEN = "YOUR_VEKLOM_TOKEN";

const response = await fetch(`${{API}}/ai/inference`, {{
  method: "POST",
  headers: {{
    "Authorization": `Bearer ${{TOKEN}}`,
    "Content-Type": "application/json",
  }},
  body: JSON.stringify({{
    messages: [{{ role: "user", content: "Summarize this document..." }}],
  }}),
}});

const data = await response.json();
console.log(data.response_text);
console.log("Provider:", data.provider, "| Cost:", data.cost_usd);
console.log("Evidence:", response.headers.get("x-veklom-evidence-id"));""",
            },
            "mcp_agent": {
                "description": "Discover Veklom tools via MCP SSE",
                "code": f"""import httpx

# Discover available tools
with httpx.stream("GET", "{base}/mcp/sse") as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            import json
            event = json.loads(line[6:])
            if event["type"] == "tool":
                print(event["tool"]["name"], "-", event["tool"]["price_usdc"], "USDC")""",
            },
        },
        "sdk_links": {
            "openapi_json":     f"{base}/openapi.json",
            "postman_import":   f"{base}/openapi.json",
            "pricing":          f"{base}/pricing",
            "agent_use_cases":  f"{base}/agent-use-cases",
            "mcp_sse":          f"{base}/mcp/sse",
        },
    }, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=3600"})
