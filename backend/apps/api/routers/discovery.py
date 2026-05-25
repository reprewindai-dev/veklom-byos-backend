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

VEKLOM_USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base
VEKLOM_TREASURY    = "0x0000000000000000000000000000000000000001"  # replace with real treasury
VEKLOM_NETWORK     = "base"
VEKLOM_BASE_URL    = "https://veklom.com"       # main site (workspace, landing, pricing)
VEKLOM_API_BASE    = "https://api.veklom.com/api/v1"  # machine-facing API surface
VEKLOM_AGENT_BASE  = "https://api.veklom.com"   # where .well-known, mcp/sse, openapi.json live


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
Pricing:          https://veklom.com/pricing

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
