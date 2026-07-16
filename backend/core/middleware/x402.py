"""
x402 Payment Protocol Middleware for Veklom.

Flow:
  1. Request arrives at a paid route
  2. Check for valid Bearer JWT with operating reserve balance
  3. If authenticated + sufficient balance → execute, deduct, return receipt
  4. If unauthenticated or no balance → return 402 with x402 headers
  5. If X-Payment header present → verify payment, execute, return receipt

Every paid response is wrapped with receipt headers.
"""

import json
import uuid
import time
import hashlib
import hmac
import os
import logging
import re
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone, timedelta
from typing import Optional
import asyncio
from backend.core.services.settlement_service import SettlementService

async def _persist_vnp_stake_async(workspace_id: str, path: str, stake_amount: float, latency: float, result: str):
    try:
        from backend.core.database.database import async_session
        from backend.db.models.security import VnpStakeLog
        async with async_session() as db:
            log = VnpStakeLog(
                workspace_id=workspace_id,
                api_route=path,
                stake_amount_usdc=stake_amount,
                latency_ms=latency,
                result=result
            )
            db.add(log)
            await db.commit()
    except Exception as e:
        logger.error(f"[VNP Stakes] Failed to persist stake log: {e}")

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing table (mirrors discovery.py — kept in sync)
# ---------------------------------------------------------------------------
_PAID_ROUTES: dict[str, dict] = {
    # --- Standard / Backward Compatible Fallbacks ---
    "/api/v1/ai/inference":        {"price_usdc": 0.008, "name": "AI Inference",       "free_daily": 5},
    "/api/v1/ai/chat":             {"price_usdc": 0.005, "name": "AI Chat",            "free_daily": 5},
    "/api/v1/gpc/compile":         {"price_usdc": 0.015, "name": "GPC Compile",        "free_daily": 3},
    "/api/v1/gpc/intent-to-plan":  {"price_usdc": 0.010, "name": "GPC Intent-to-Plan", "free_daily": 3},
    "/api/v1/gpc/runs":            {"price_usdc": 0.020, "name": "GPC Run",            "free_daily": 0},
    "/api/v1/pipelines/trigger":   {"price_usdc": 0.025, "name": "Pipeline Trigger",   "free_daily": 0},
    "/api/v1/runtime/jobs":        {"price_usdc": 0.020, "name": "Runtime Job",        "free_daily": 0},
    "/api/v1/evidence/export":     {"price_usdc": 0.005, "name": "Evidence Export",    "free_daily": 2},
    "/api/v1/compliance/report":   {"price_usdc": 0.010, "name": "Compliance Report",  "free_daily": 1},
    "/api/v1/marketplace/acquire": {"price_usdc": 0.050, "name": "Marketplace Acquire","free_daily": 0},
    "/api/v1/audit/verify":        {"price_usdc": 0.003, "name": "Audit Verify",       "free_daily": 5},
    "/api/v1/x402/protected-test": {"price_usdc": 0.025, "name": "Protected Test Route", "free_daily": 0},
    "/api/v1/x402/search":         {"price_usdc": 0.10,  "name": "Machine Search",       "free_daily": 0},
    "/api/v1/x402/evaluate":       {"price_usdc": 0.10,  "name": "Machine Evaluate",     "free_daily": 0},
    "/api/v1/x402/governance":     {"price_usdc": 0.10,  "name": "Machine Governance",   "free_daily": 0},
    "/api/v1/x402/score":          {"price_usdc": 0.10,  "name": "Machine Score",        "free_daily": 0},
    "/api/v1/x402/verify":         {"price_usdc": 0.002, "name": "Machine Verify",       "free_daily": 0},

    # --- Method-Aware Niche Compliance APIs (PayAPI Catalog) ---
    
    # Category A: The GPC (Governed Plan Compiler) Pipeline (7 Endpoints)
    "POST:/api/v1/gpc/intent-to-plan":  {"price_usdc": 0.02,   "name": "Messy Intent-To-Plan Compiler", "free_daily": 3, "category": "A", "unit": "per plan"},
    "POST:/api/v1/gpc/plans":           {"price_usdc": 0.005,  "name": "GPC Plan Saver", "free_daily": 0, "category": "A", "unit": "per plan"},
    "GET:/api/v1/gpc/plans":            {"price_usdc": 0.001,  "name": "GPC Plans List", "free_daily": 0, "category": "A", "unit": "per list"},
    "POST:/api/v1/gpc/runs":            {"price_usdc": 0.02,   "name": "GPC Background Dispatcher", "free_daily": 0, "category": "A", "unit": "per run"},
    "GET:/api/v1/gpc/runs":             {"price_usdc": 0.002,  "name": "GPC Runs List", "free_daily": 0, "category": "A", "unit": "per list"},
    "GET:/api/v1/gpc/events":           {"price_usdc": 0.001,  "name": "GPC Real-Time Status Signals", "free_daily": 0, "category": "A", "unit": "per stream"},
    "GET:/api/v1/gpc/bootstrap":        {"price_usdc": 0.001,  "name": "GPC System Core Bootstrap", "free_daily": 0, "category": "A", "unit": "per bootstrap"},

    # Category B: The cAPI (Constitutional API) 9-Phase Hard Gate (9 Endpoints)
    "POST:/api/v1/capi/execute":                         {"price_usdc": 0.05,  "name": "Governed Execution Interception Gateway", "free_daily": 0, "category": "B", "unit": "per execution"},
    "GET:/api/v1/capi/quarantine":                       {"price_usdc": 0.005, "name": "Human-in-the-Loop Quarantine Fetcher", "free_daily": 0, "category": "B", "unit": "per fetch"},
    "POST:/api/v1/capi/quarantine/{quarantine_id}/resolve": {"price_usdc": 0.01,  "name": "Quarantine Intent Resolver", "free_daily": 0, "category": "B", "unit": "per resolution"},
    "GET:/api/v1/authority/runs":                        {"price_usdc": 0.002, "name": "Active Authority Runs", "free_daily": 0, "category": "B", "unit": "per list"},
    "GET:/api/v1/authority/runs/{run_id}/decisions":     {"price_usdc": 0.003, "name": "Authority Run Detail & Decisions", "free_daily": 0, "category": "B", "unit": "per lookup"},
    "GET:/api/v1/authority/bundles":                     {"price_usdc": 0.002, "name": "Dynamic Policy Bundle Manifest", "free_daily": 0, "category": "B", "unit": "per manifest"},
    "GET:/api/v1/authority/context":                     {"price_usdc": 0.001, "name": "Active Authority Context", "free_daily": 0, "category": "B", "unit": "per lookup"},
    "POST:/api/v1/autonomous":                           {"price_usdc": 0.01,  "name": "Sovereign Autonomous Interrogator", "free_daily": 0, "category": "B", "unit": "per query"},
    "POST:/api/v1/governed/capi/compile":                {"price_usdc": 50.00, "name": "Governed cAPI Immutable Compiler", "free_daily": 0, "category": "B", "unit": "per compilation"},

    # Category C: PGL Identity & Sovereign Workforce (10 Endpoints)
    "POST:/api/v1/pgl/identity-rag/resolve":            {"price_usdc": 0.01,  "name": "IdentityRAG Cross-Cluster Resolver", "free_daily": 0, "category": "C", "unit": "per resolution"},
    "GET:/api/v1/pgl/{agent_id}/genealogy":             {"price_usdc": 0.01,  "name": "Merkle Genealogy DNA Proof", "free_daily": 0, "category": "C", "unit": "per proof"},
    "POST:/api/v1/pgl/{agent_id}/quarantine":            {"price_usdc": 0.01,  "name": "Dynamic RLS Decoy Quarantine", "free_daily": 0, "category": "C", "unit": "per quarantine"},
    "GET:/api/v1/agents/law":                            {"price_usdc": 0.001, "name": "Agent Constitutional Law Ingress", "free_daily": 0, "category": "C", "unit": "per query"},
    "GET:/api/v1/agents/registry":                       {"price_usdc": 0.002, "name": "Workforce Registry Directory", "free_daily": 0, "category": "C", "unit": "per directory"},
    "GET:/api/v1/agents/fleet":                          {"price_usdc": 0.005, "name": "Workspace Workforce Aggregator", "free_daily": 0, "category": "C", "unit": "per fleet"},
    "GET:/api/v1/agents/registry/{agent_number}":        {"price_usdc": 0.001, "name": "Individual Agent Detail Inspector", "free_daily": 0, "category": "C", "unit": "per inspect"},
    "GET:/api/v1/agents/skills":                         {"price_usdc": 0.002, "name": "Active Workforce Capabilities", "free_daily": 0, "category": "C", "unit": "per listing"},
    "POST:/api/v1/pgl/identity/renew":                   {"price_usdc": 0.10,  "name": "PGL Operator Identity Renewal", "free_daily": 0, "category": "C", "unit": "per renewal"},
    "POST:/api/v1/agents/{agent_id}/renew":              {"price_usdc": 0.10,  "name": "PGL Agent Birth Certificate Renewal", "free_daily": 0, "category": "C", "unit": "per renewal"},

    # Category D: Dynamic Guardrails & Memory Interceptors (8 Endpoints)
    "POST:/api/v1/agent-guardrails/{agent_id}/guardrails":         {"price_usdc": 0.01,  "name": "Live Guardrail Injector", "free_daily": 0, "category": "D", "unit": "per injection"},
    "POST:/api/v1/agent-guardrails/{agent_id}/evaluate-input":     {"price_usdc": 0.01,  "name": "Pre-Reasoning Input Interceptor", "free_daily": 0, "category": "D", "unit": "per input"},
    "POST:/api/v1/agent-guardrails/{agent_id}/evaluate-output":    {"price_usdc": 0.01,  "name": "Post-Reasoning Egress Interceptor", "free_daily": 0, "category": "D", "unit": "per output"},
    "POST:/api/v1/agent-guardrails/{agent_id}/evaluate-tool-call":  {"price_usdc": 0.015, "name": "Dynamic Tool-Call Schema Moat", "free_daily": 0, "category": "D", "unit": "per check"},
    "POST:/api/v1/agent-memory/{agent_id}/memory/store":           {"price_usdc": 0.005, "name": "Ephemeral Vector Memory Writer", "free_daily": 0, "category": "D", "unit": "per write"},
    "GET:/api/v1/agent-memory/{agent_id}/memory/search":           {"price_usdc": 0.004, "name": "Semantic Memory Search", "free_daily": 0, "category": "D", "unit": "per search"},
    "POST:/api/v1/agent-memory/{agent_id}/context/{context_id}/update": {"price_usdc": 0.005, "name": "Live Prompt Context Mutator", "free_daily": 0, "category": "D", "unit": "per mutation"},
    "DELETE:/api/v1/agent-memory/{agent_id}/memory/{memory_id}":    {"price_usdc": 0.002, "name": "Memory Erasure Compliance Hook", "free_daily": 0, "category": "D", "unit": "per delete"},

    # Category E: On-Chain Settlement & VNP Staking State (11 Endpoints)
    "POST:/api/v1/x402/register-api":                   {"price_usdc": 0.01,  "name": "Dynamic API Gateway Self-Registration", "free_daily": 0, "category": "E", "unit": "per registration"},
    "POST:/api/v1/x402/verify":                         {"price_usdc": 0.002, "name": "Offline EVM Signed Receipt Validator", "free_daily": 0, "category": "E", "unit": "per verification"},
    "POST:/api/v1/x402/flash-loan":                      {"price_usdc": 0.05,  "name": "Trustless Compute Credit Flash Loans", "free_daily": 0, "category": "E", "unit": "per loan"},
    "POST:/api/v1/agents/skills/{skill_id}/invoke":     {"price_usdc": 0.02,  "name": "Dynamic Paid Skill Invocation", "free_daily": 0, "category": "E", "unit": "per invocation"},
    "POST:/api/v1/vnp/bounty/submit-proof":              {"price_usdc": 0.01,  "name": "VNP SLA Performance Bond Slasher", "free_daily": 0, "category": "E", "unit": "per submission"},
    "POST:/api/v1/vnp/beacon":                          {"price_usdc": 0.001, "name": "Heartbeat SLA Beacon Broadcaster", "free_daily": 0, "category": "E", "unit": "per beacon"},
    "GET:/api/v1/billing/ledger":                       {"price_usdc": 0.002, "name": "Institutional Ledger Billing History", "free_daily": 0, "category": "E", "unit": "per query"},
    "GET:/api/v1/vnp/stakes":                           {"price_usdc": 0.002, "name": "SLA Validator Stakes Escrow", "free_daily": 0, "category": "E", "unit": "per lookup"},
    "GET:/api/v1/billing/receipts/{receipt_id}":        {"price_usdc": 0.001, "name": "Audit Invoice Query", "free_daily": 0, "category": "E", "unit": "per query"},
    "GET:/api/v1/benchmarks/staking/state":             {"price_usdc": 0.002, "name": "VNP Stakes & Staking State Engine", "free_daily": 0, "category": "E", "unit": "per query"},
    "GET:/api/v1/benchmarks/leaderboard":               {"price_usdc": 0.002, "name": "VNP Leaderboard & API Trust Rankings", "free_daily": 0, "category": "E", "unit": "per query"},

    # Category F: Audit-Trails & Legal Compliance (9 Endpoints)
    "POST:/api/v1/compliance/check":                     {"price_usdc": 0.01,  "name": "Automated Compliance Audit Engine", "free_daily": 0, "category": "F", "unit": "per check"},
    "GET:/api/v1/compliance/frameworks":                 {"price_usdc": 0.002, "name": "SOC2 & ISO42001 Compliance Frameworks Registry", "free_daily": 0, "category": "F", "unit": "per registry"},
    "POST:/api/v1/privacy/detect-pii":                   {"price_usdc": 0.005, "name": "Token PII Scanner", "free_daily": 0, "category": "F", "unit": "per scan"},
    "POST:/api/v1/privacy/mask-pii":                     {"price_usdc": 0.005, "name": "Context-based PII Masker", "free_daily": 0, "category": "F", "unit": "per mask"},
    "POST:/api/v1/content-safety/scan":                  {"price_usdc": 0.005, "name": "Toxicity Alignment Checker", "free_daily": 0, "category": "F", "unit": "per scan"},
    "GET:/api/v1/audit/verify/{log_id}":                 {"price_usdc": 0.01,  "name": "SHA-256 Audit Chain Integrity Verifier", "free_daily": 0, "category": "F", "unit": "per verify"},
    "GET:/api/v1/audit/logs":                            {"price_usdc": 0.002, "name": "Consolidated Tenant Logs Stream", "free_daily": 0, "category": "F", "unit": "per query"},
    "GET:/api/v1/audit/logs/{log_id}":                   {"price_usdc": 0.001, "name": "Audit Entry Inspector", "free_daily": 0, "category": "F", "unit": "per lookup"},
    "GET:/api/v1/compliance/evidence/{framework_id}/export": {"price_usdc": 0.02,  "name": "Dynamic UACP Evidence Export", "free_daily": 0, "category": "F", "unit": "per export"},

    # Category G: Self-Learning Feedback & Observability (11 Endpoints)
    "GET:/api/v1/gpc/stats":                            {"price_usdc": 0.005, "name": "UACP Core Pressure Estimator", "free_daily": 0, "category": "G", "unit": "per stats"},
    "GET:/api/v1/explain/routing/{decision_id}":        {"price_usdc": 0.005, "name": "Explanatory Weight Router Resolver", "free_daily": 0, "category": "G", "unit": "per explanation"},
    "GET:/api/v1/explain/cost/{prediction_id}":         {"price_usdc": 0.005, "name": "Budget Risk Predictor", "free_daily": 0, "category": "G", "unit": "per prediction"},
    "GET:/api/v1/gpc/ssrn-signals":                     {"price_usdc": 0.002, "name": "Academic SSRN Research Feed Signals", "free_daily": 0, "category": "G", "unit": "per stream"},
    "GET:/api/v1/gpc/observability/signals":            {"price_usdc": 0.002, "name": "Dynamic Observability Telemetry", "free_daily": 0, "category": "G", "unit": "per signals"},
    "POST:/api/v1/onboarding/register":                 {"price_usdc": 0.01,  "name": "Institutional Profile Onboarding Register", "free_daily": 0, "category": "G", "unit": "per register"},
    "POST:/api/v1/playground/evaluate":                 {"price_usdc": 0.01,  "name": "Sandbox Evaluation Engine", "free_daily": 0, "category": "G", "unit": "per evaluation"},
    "POST:/api/v1/copilot/explain":                     {"price_usdc": 0.01,  "name": "Generative Code Risk Explanation", "free_daily": 0, "category": "G", "unit": "per explanation"},
    "POST:/api/v1/terminal/command":                    {"price_usdc": 0.02,  "name": "Sandboxed Terminal Commander", "free_daily": 0, "category": "G", "unit": "per command"},
    "GET:/api/v1/forensics/replay":                     {"price_usdc": 0.02,  "name": "Forensics Black Box Replayer", "free_daily": 0, "category": "G", "unit": "per replay"},
    "GET:/api/v1/onboarding/metrics":                   {"price_usdc": 0.002, "name": "Onboarding Compliance Metrics", "free_daily": 0, "category": "G", "unit": "per metrics"},

    # Category H: Mission Lock, Behavioral Governance & Conformance Analytics (7 Endpoints)
    "POST:/api/v1/mission-lock/agents/{agent_id}/act":     {"price_usdc": 0.015, "name": "Agent Conformance Action Step", "free_daily": 0, "category": "H", "unit": "per action"},
    "POST:/api/v1/mission-lock/agents/{agent_id}/update":  {"price_usdc": 0.01,  "name": "Behavioral Reward Signal Update", "free_daily": 0, "category": "H", "unit": "per reward"},
    "GET:/api/v1/mission-lock/agents/{agent_id}/state":    {"price_usdc": 0.002, "name": "Lock State and Parameter Queries", "free_daily": 0, "category": "H", "unit": "per query"},
    "POST:/api/v1/mission-lock/agents/{agent_id}/adjust":  {"price_usdc": 0.01,  "name": "Rigidity Adjustment Dispatcher", "free_daily": 0, "category": "H", "unit": "per adjustment"},
    "GET:/api/v1/mission-lock/teams/{team_id}/coordinate": {"price_usdc": 0.005, "name": "Team Coordination Snapshot", "free_daily": 0, "category": "H", "unit": "per snapshot"},
    "GET:/api/v1/mission-lock/agents/{agent_id}/trace":    {"price_usdc": 0.003, "name": "Forensics Action Trace Reader", "free_daily": 0, "category": "H", "unit": "per trace"},
    "GET:/api/v1/mission-lock/agents/{agent_id}/metrics":  {"price_usdc": 0.002, "name": "Conformance and Recovery Metrics Cache", "free_daily": 0, "category": "H", "unit": "per metrics"},

    # Plural/Singular Aliases for Category H Robustness
    "POST:/api/v1/mission-lock/agent/{agent_id}/act":     {"price_usdc": 0.015, "name": "Agent Conformance Action Step", "free_daily": 0, "category": "H", "unit": "per action"},
    "POST:/api/v1/mission-lock/agent/{agent_id}/update":  {"price_usdc": 0.01,  "name": "Behavioral Reward Signal Update", "free_daily": 0, "category": "H", "unit": "per reward"},
    "GET:/api/v1/mission-lock/agent/{agent_id}/state":    {"price_usdc": 0.002, "name": "Lock State and Parameter Queries", "free_daily": 0, "category": "H", "unit": "per query"},
    "POST:/api/v1/mission-lock/agent/{agent_id}/adjust":  {"price_usdc": 0.01,  "name": "Rigidity Adjustment Dispatcher", "free_daily": 0, "category": "H", "unit": "per adjustment"},
    "GET:/api/v1/mission-lock/team/{team_id}/coordinate": {"price_usdc": 0.005, "name": "Team Coordination Snapshot", "free_daily": 0, "category": "H", "unit": "per snapshot"},
    "GET:/api/v1/mission-lock/agent/{agent_id}/trace":    {"price_usdc": 0.003, "name": "Forensics Action Trace Reader", "free_daily": 0, "category": "H", "unit": "per trace"},
    "GET:/api/v1/mission-lock/agent/{agent_id}/metrics":  {"price_usdc": 0.002, "name": "Conformance and Recovery Metrics Cache", "free_daily": 0, "category": "H", "unit": "per metrics"},
}

_FREE_ROUTES_PREFIX = (
    "/health", "/_ping", "/status", "/openapi.json", "/.well-known",
    "/llms.txt", "/pricing", "/robots.txt", "/docs", "/redoc",
    "/api/v1/ai/models", "/api/v1/workspace/providers",
    "/api/v1/auth/", "/api/v1/platform/pulse",
    "/api/v1/pricing", "/api/v1/sdk/", "/api/v1/agent-use-cases",
    "/agent-use-cases", "/sdk/examples",
    "/mcp/", "/static/", "/assets/", "/favicon",
    "/api/v1/openapi.json", "/v1/openapi.json",
    "/api/v1/sys/health", "/api/v1/sys/gpu",
    "/api/v1/copilot/registry", "/api/v1/copilot/recent-decisions",
    "/api/v1/integrations/", "/api/v1/receipts", "/api/v1/evidence/verify",
    "/api/v1/x402/config",
    "/api/v1/benchmarks/leaderboard", "/api/v1/benchmarks/card/",
    "/api/benchmarks/card/", "/api/v1/benchmarks/staking/state"
)

VEKLOM_API_BASE   = "https://veklom.com/api/v1"
VEKLOM_USDC_ADDR  = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base

def _price_decimal(route_config: dict) -> Decimal:
    return Decimal(str(route_config["price_usdc"]))

def _price_usdc_string(route_config: dict) -> str:
    normalized = _price_decimal(route_config).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
    text = format(normalized, "f").rstrip("0").rstrip(".")
    if "." not in text:
        return f"{text}.00"
    whole, fractional = text.split(".", 1)
    if len(fractional) == 1:
        return f"{whole}.{fractional}0"
    return text

def _price_micro_usdc(route_config: dict) -> int:
    return int((_price_decimal(route_config) * Decimal("1000000")).to_integral_value(rounding=ROUND_DOWN))


def is_valid_evm_address(addr: str) -> bool:
    return bool(re.match(r"^0x[a-fA-F0-9]{40}$", addr))

_basename_cache = {}

def resolve_basename(name: str) -> str:
    name_lower = name.strip().lower()
    if not (name_lower.endswith(".base.eth") or name_lower.endswith(".base")):
        return ""
        
    if name_lower in _basename_cache:
        return _basename_cache[name_lower]
        
    if settings.X402_TEST_PROOF_MODE and (name_lower == "veklom.base.eth" or name_lower == "veklom.base"):
        return settings.VEKLOM_TREASURY_ADDRESS

    label = name_lower.split(".")[0]
    try:
        from web3 import Web3
        token_id = int.from_bytes(Web3.keccak(text=label), byteorder="big")
        
        contract_address = "0x03c4738ee98ae44591e1a4a4f3cab6641d95dd9a"
        abi = [{
            "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
            "name": "ownerOf",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }]
        
        rpc_url = settings.FLASHBLOCKS_RPC_URL or "https://mainnet.base.org"
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
        owner = contract.functions.ownerOf(token_id).call()
        if owner and is_valid_evm_address(owner):
            _basename_cache[name_lower] = owner
            return owner
    except Exception as e:
        logger.warning(f"Basename resolution failed for {name}: {e}")
        if name_lower == "veklom.base.eth" or name_lower == "veklom.base":
            return settings.VEKLOM_TREASURY_ADDRESS
        
    return ""

def get_treasury_address() -> str:
    raw = os.getenv("VEKLOM_TREASURY_ADDRESS", settings.VEKLOM_TREASURY_ADDRESS).strip()
    if not raw or raw == "0x0000000000000000000000000000000000000001":
        return ""
    if is_valid_evm_address(raw):
        return raw
    if raw.endswith(".base.eth") or raw.endswith(".base"):
        resolved = resolve_basename(raw)
        if resolved and is_valid_evm_address(resolved):
            return resolved
    return ""

# In-memory free-trial counter: { ip_day_key → count }
_free_usage: dict[str, int] = {}


def _today_key(ip: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{ip}:{day}"


_compiled_patterns = {}

def _match_route(path: str, pattern: str) -> bool:
    if pattern not in _compiled_patterns:
        # Build regex string by splitting on `{...}` placeholders
        parts = []
        last_idx = 0
        for match in re.finditer(r'\{[^}]+\}', pattern):
            parts.append(re.escape(pattern[last_idx:match.start()]))
            parts.append(r'[^/]+')
            last_idx = match.end()
        parts.append(re.escape(pattern[last_idx:]))
        regex_str = "".join(parts)
        _compiled_patterns[pattern] = re.compile(f"^{regex_str}(?:/|$)")
    return bool(_compiled_patterns[pattern].match(path))


def _get_route_config(path: str, method: str) -> Optional[dict]:
    method = method.upper()
    
    # 1. Method-specific exact match (e.g. POST:/api/v1/gpc/plans)
    method_exact_key = f"{method}:{path}"
    if method_exact_key in _PAID_ROUTES:
        return _PAID_ROUTES[method_exact_key]
        
    # 2. Path-only exact match (for legacy/backward compatible keys)
    if path in _PAID_ROUTES:
        return _PAID_ROUTES[path]
        
    # 3. Method-specific pattern matching
    for pattern, cfg in _PAID_ROUTES.items():
        if ":" in pattern:
            parts = pattern.split(":", 1)
            if parts[0] in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                pattern_method = parts[0]
                pattern_path = parts[1]
                if pattern_method == method and _match_route(path, pattern_path):
                    return cfg
                    
    # 4. Path-only pattern matching
    for pattern, cfg in _PAID_ROUTES.items():
        if ":" in pattern:
            parts = pattern.split(":", 1)
            if parts[0] in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                continue
        if _match_route(path, pattern):
            return cfg
            
    return None


def _is_free_route(path: str) -> bool:
    for prefix in _FREE_ROUTES_PREFIX:
        if path.startswith(prefix):
            return True
    return False


async def create_and_persist_receipt(
    request: Request,
    route_path: str,
    method: str,
    price_usdc: float,
    tx_hash: str,
    db_session
) -> dict:
    """Generates a cryptographic receipt for audit verification and attempts database persistence."""
    receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    challenge_id = request.headers.get("X-Payment-Challenge-ID") or f"chal_{uuid.uuid4().hex[:16]}"
    
    proof_hash = hashlib.sha256(tx_hash.encode()).hexdigest()
    
    # Calculate a unique evidence hash seal
    evidence_content = f"{receipt_id}:{request_id}:{tx_hash}:{route_path}"
    evidence_hash = hashlib.sha256(evidence_content.encode()).hexdigest()
    
    receipt = {
        "receipt_id": receipt_id,
        "request_id": request_id,
        "challenge_id": challenge_id,
        "route": route_path,
        "method": method,
        "amount": price_usdc,
        "currency": "USDC",
        "network": "base",
        "chain_id": 8453,
        "payer": request.client.host if request.client else "unknown",
        "pay_to": get_treasury_address(),
        "proof_hash": proof_hash,
        "tx_hash": tx_hash,
        "policy_decision": "passed",
        "execution_status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_hash": evidence_hash,
        "receipt_signature": f"sig_{hashlib.sha256((receipt_id + evidence_hash + settings.SECRET_KEY).encode()).hexdigest()[:24]}",
        "persistence_status": "not_configured"
    }

    if db_session:
        try:
            from backend.db.models.security import AuditLog
            receipt["persistence_status"] = "persisted"
            log = AuditLog(
                workspace_id="default",
                action="x402.receipt.create",
                resource_type="x402_receipt",
                resource_id=receipt_id,
                details=receipt
            )
            db_session.add(log)
            await db_session.commit()
        except Exception as exc:
            logger.error(f"Failed to persist x402 receipt: {exc}")
            receipt["persistence_status"] = "failed"
            receipt["warnings"] = [f"Database error during persistence: {exc}"]
            
    return receipt


def _build_402_response(path: str, method: str, route_config: dict, detail: Optional[str] = None) -> JSONResponse:
    import base64
    challenge_id = f"chal_{uuid.uuid4().hex[:16]}"
    nonce = f"nonce_{uuid.uuid4().hex[:16]}"
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
    price_usdc = _price_usdc_string(route_config)
    amount_micro_usdc = _price_micro_usdc(route_config)
    
    # Construct standard CDP x402 v2 payment required payload object
    v2_payload_obj = {
        "x402Version": 2,
        "resource": {
            "url": f"https://api.veklom.com{path}",
            "description": route_config.get("name", "Veklom Protected API Endpoint")
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": "eip155:8453",
                "amount": str(amount_micro_usdc),
                "asset": VEKLOM_USDC_ADDR,
                "payTo": get_treasury_address(),
                "maxTimeoutSeconds": 86400,
                "extra": {
                    "name": "USD Coin",
                    "version": "2"
                }
            }
        ]
    }
    v2_payload_str = json.dumps(v2_payload_obj)
    v2_base64 = base64.b64encode(v2_payload_str.encode("utf-8")).decode("utf-8")

    payload = {
        "error": "payment_required",
        "x402_version": 2,
        "challenge_id": challenge_id,
        "nonce": nonce,
        "amount": price_usdc,
        "amount_usdc": price_usdc,
        "currency": "USDC",
        "network": "base",
        "chain_id": 8453,
        "pay_to": get_treasury_address(),
        "route": path,
        "method": method,
        "expires_at": expires_at,
        "proof_header_name": "X-PAYMENT",
        "payment_requirements": {
            "asset_contract": VEKLOM_USDC_ADDR,
            "destination": get_treasury_address(),
            "minimum_amount_micro_usdc": amount_micro_usdc,
            "amount_usdc": price_usdc,
        },
        "replay_protection": {
            "nonce_required": True,
            "nonce_ttl_seconds": 300,
            "challenge_ttl_seconds": 300
        },
        "receipt_expected": True,
        "payment_required_base64": v2_base64
    }
    if detail:
        payload["detail"] = detail
        
    headers = {
        "payment-required": v2_base64,
        "Payment-Required": v2_base64,
        "X-Payment-Required": "true",
        "X-Payment-Challenge-ID": challenge_id,
        "X-Payment-Nonce": nonce,
        "X-Payment-Price-USDC": price_usdc,
        "X-Payment-Network": "base",
        "X-Payment-Asset": VEKLOM_USDC_ADDR,
        "X-Payment-Address": get_treasury_address(),
        "X-Payment-Scheme": "x402",
        "X-Veklom-Upgrade": "https://veklom.com/pricing",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "payment-required,Payment-Required,X-Payment-Required,X-Payment-Price-USDC,X-Payment-Network,X-Payment-Asset,X-Payment-Challenge-ID,X-Payment-Nonce",
    }
    return JSONResponse(payload, status_code=402, headers=headers)


async def _verify_workspace_auth(request: Request) -> Optional[dict]:
    """Check Bearer JWT and return user payload if valid."""
    try:
        from backend.core.security.auth import verify_token
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            token = request.cookies.get("access_token") or request.cookies.get("token")
        else:
            token = auth[7:]
        if not token:
            return None
        return verify_token(token)
    except Exception:
        return None


async def _verify_x402_payment(request: Request, route_config: dict) -> bool:
    """
    Verifies the x402 payment proof header with standard Base Mainnet checks or Dev Test proof bypass.
    Prevent double-spend replay attacks using Redis (fails closed in prod if Redis goes offline).
    """
    import httpx
    from backend.core.database.redis_client import redis_client

    proof = (
        request.headers.get("x-payment") or 
        request.headers.get("X-Payment") or 
        request.headers.get("X-PAYMENT") or 
        request.headers.get("payment-signature") or 
        request.headers.get("Payment-Signature") or 
        request.headers.get("X-Payment-Proof")
    )
    if not proof:
        request.state.x402_error = "missing_payment_proof"
        return False

    proof_str = proof.strip()

    # B1. Base Commerce Payments Integration (Shopify-aligned)
    if proof_str.startswith("xpay_"):
        try:
            from sqlalchemy import select
            from backend.core.database.database import get_db_session
            from backend.db.models.security import AuditLog

            async with get_db_session() as db:
                result = await db.execute(
                    select(AuditLog).where(
                        AuditLog.resource_type == "x402_payment",
                        AuditLog.resource_id == proof_str
                    )
                )
                log_entry = result.scalar_one_or_none()
                if log_entry:
                    details = log_entry.details or {}
                    status = details.get("status")
                    if status in ("authorized", "captured", "charged"):
                        # Replay protection check
                        redis_key = f"x402_tx:{proof_str}"
                        if settings.APP_ENV == "production" and redis_client.is_fallback:
                            request.state.x402_error = "replay_storage_unavailable"
                            return False
                        
                        already_used = await redis_client.get(redis_key)
                        if already_used:
                            request.state.x402_error = "replay_detected"
                            return False
                        
                        required_amount = route_config["price_usdc"]
                        authorized_amount = details.get("amount", 0.0)
                        if authorized_amount >= required_amount:
                            await redis_client.set(redis_key, "used", ex=604800)
                            logger.info(f"[x402] Multi-stage payment {proof_str} verified successfully!")
                            return True
                        else:
                            request.state.x402_error = "insufficient_payment"
                            return False
                    else:
                        request.state.x402_error = "invalid_transaction"
                        return False
        except Exception as exc:
            logger.error(f"[x402] Error verifying multi-stage payment: {exc}")
            request.state.x402_error = "replay_storage_unavailable"
            return False

        request.state.x402_error = "invalid_transaction"
        return False

    # A. Test Proof Mode (Only active if enabled by environment settings)
    if settings.X402_TEST_PROOF_MODE:
        if proof_str.startswith("test_proof_"):
            if "invalid" in proof_str or "fail" in proof_str:
                request.state.x402_error = "invalid_transaction"
                return False
            
            # Replay protection check
            redis_key = f"x402_tx:{proof_str}"
            if settings.APP_ENV == "production" and redis_client.is_fallback:
                request.state.x402_error = "replay_storage_unavailable"
                return False
            
            already_used = await redis_client.get(redis_key)
            if already_used:
                request.state.x402_error = "replay_detected"
                return False
            
            # Lock test proof hash
            await redis_client.set(redis_key, "used", ex=300)
            request.state.test_proof_mode = True
            return True

    # Validate standard transaction hash format
    if not (proof_str.startswith("0x") and len(proof_str) == 66):
        logger.warning(f"[x402] Invalid transaction hash format: {proof_str}")
        request.state.x402_error = "invalid_transaction"
        return False

    # B. Replay Protection - check if the transaction hash was used before
    redis_key = f"x402_tx:{proof_str}"
    
    # In production, if Redis is down (is_fallback is True), fail closed.
    if settings.APP_ENV == "production" and redis_client.is_fallback:
        logger.error("[x402] Replay storage Redis is offline. Failing closed for security.")
        request.state.x402_error = "replay_storage_unavailable"
        return False

    already_used = await redis_client.get(redis_key)
    if already_used:
        logger.warning(f"[x402] Replay attack detected. Tx hash {proof_str} already used.")
        request.state.x402_error = "replay_detected"
        return False

    # C. Mainnet JSON-RPC on Base (incorporating Flashblocks-aware RPC first)
    rpc_endpoints = [settings.FLASHBLOCKS_RPC_URL] if getattr(settings, "FLASHBLOCKS_RPC_URL", "") else []
    rpc_endpoints.extend([
        "https://mainnet.base.org",
        "https://base.llamarpc.com",
        "https://base-rpc.publicnode.com"
    ])

    tx_receipt = None
    rpc_url_used = None
    async with httpx.AsyncClient(timeout=5.0) as client:
        for rpc_url in rpc_endpoints:
            try:
                rpc_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [proof_str],
                    "id": 1
                }
                res = await client.post(rpc_url, json=rpc_payload)
                if res.status_code == 200:
                    data = res.json()
                    if "result" in data and data["result"] is not None:
                        tx_receipt = data["result"]
                        rpc_url_used = rpc_url
                        break
            except Exception as e:
                logger.warning(f"[x402] RPC check failed on {rpc_url}: {e}")
                continue

    if not tx_receipt:
        logger.warning(f"[x402] Could not fetch receipt for transaction hash: {proof_str}")
        request.state.x402_error = "invalid_transaction"
        return False

    # Check transaction status (0x1 = success)
    status = tx_receipt.get("status")
    if status != "0x1":
        logger.warning(f"[x402] Transaction {proof_str} failed or status is not 0x1: {status}")
        request.state.x402_error = "invalid_transaction"
        return False

    # D. Configurable required confirmations - default to 1 in production, 0 in dev if not specified
    default_confirmations = 1 if settings.APP_ENV == "production" else 0
    required_confirmations = int(os.environ.get("X402_REQUIRED_CONFIRMATIONS", str(default_confirmations)))
    
    if settings.APP_ENV == "production" and required_confirmations < 1:
        logger.error("[SECURITY WARNING] required_confirmations < 1 in PRODUCTION. Enforcing minimum of 1.")
        required_confirmations = 1

    confirmations = 0
    if tx_receipt.get("blockNumber") and rpc_url_used:
        try:
            tx_block = int(tx_receipt["blockNumber"], 16) if isinstance(tx_receipt["blockNumber"], str) else int(tx_receipt["blockNumber"])
            
            # Fetch the block to check its timestamp for transaction freshness
            async with httpx.AsyncClient(timeout=3.0) as block_client:
                # 1. Fetch block data for timestamp
                block_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": [hex(tx_block), False],
                    "id": 3
                }
                block_res = await block_client.post(rpc_url_used, json=block_payload)
                if block_res.status_code == 200:
                    block_data = block_res.json().get("result")
                    if block_data and "timestamp" in block_data:
                        block_time = int(block_data["timestamp"], 16) if isinstance(block_data["timestamp"], str) else int(block_data["timestamp"])
                        import time
                        now_time = int(time.time())
                        # Enforce 15-minute maximum age (900 seconds)
                        if abs(now_time - block_time) > 900:
                            logger.warning(f"[x402] Transaction is too old: block_time={block_time}, now={now_time}")
                            request.state.x402_error = "invalid_transaction"
                            return False

                # 2. Fetch latest block for confirmation count
                rpc_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 2
                }
                res = await block_client.post(rpc_url_used, json=rpc_payload)
                latest_block = 0
                if res.status_code == 200:
                    data = res.json()
                    if "result" in data:
                        latest_block = int(data["result"], 16) if isinstance(data["result"], str) else int(data["result"])
                        
            if latest_block >= tx_block:
                confirmations = latest_block - tx_block
        except Exception as block_err:
            logger.warning(f"[x402] Failed to verify block age or confirmations: {block_err}")
            confirmations = 0
            
    if confirmations < required_confirmations:
        logger.warning(f"[x402] Insufficient confirmations: expected={required_confirmations}, found={confirmations}")
        request.state.x402_error = "invalid_transaction"
        return False

    # Parse transfer logs to verify destination and amount in USDC on Base
    usdc_contract = VEKLOM_USDC_ADDR.lower()
    transfer_event_sig = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    expected_amount = int(route_config["price_usdc"] * 1_000_000)
    treasury_addr = get_treasury_address().lower().strip()

    logs = tx_receipt.get("logs", [])
    actual_amount = 0

    for log in logs:
        log_address = log.get("address", "").lower()
        if log_address != usdc_contract:
            continue

        topics = log.get("topics", [])
        if not topics or topics[0].lower() != transfer_event_sig:
            continue

        if len(topics) < 3:
            continue

        to_topic = topics[2].lower()
        expected_padded = treasury_addr.replace("0x", "").zfill(64)
        if expected_padded not in to_topic:
            continue

        log_data = log.get("data", "")
        if not log_data or log_data == "0x":
            continue

        try:
            val = int(log_data, 16)
            actual_amount += val
        except ValueError:
            continue

    if actual_amount >= expected_amount:
        # Lock hash in redis to prevent double-spend
        await redis_client.set(redis_key, "used", ex=604800)
        logger.info(f"[x402] On-chain payment verified successfully! Tx: {proof_str}")
        return True
    else:
        logger.warning(f"[x402] Payment amount insufficient. Expected={expected_amount}, Found={actual_amount}")
        request.state.x402_error = "insufficient_payment"
        return False


class X402PaymentMiddleware(BaseHTTPMiddleware):
    """x402 payment enforcement middleware."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method
        
        # VNP Stakes Engine: Capture Micro-Stake
        vnp_stake = request.headers.get("X-VNP-Stake")
        vnp_start_time = time.perf_counter()

        # Test-mode bypass — set X402_DISABLED=true to skip all payment enforcement
        if os.environ.get("X402_DISABLED", "").lower() in ("1", "true", "yes"):
            if settings.APP_ENV == "production" or os.getenv("ENVIRONMENT") == "production":
                logger.error("[SECURITY PANIC] X402_DISABLED bypass attempted in PRODUCTION environment. This is forbidden!")
                return JSONResponse(status_code=500, content={"error": "Server misconfiguration. X402 payment enforcement cannot be disabled in production."})
            else:
                return await call_next(request)

        # Skip OPTIONS and free routes
        if method == "OPTIONS" or _is_free_route(path):
            return await call_next(request)

        route_cfg = _get_route_config(path, method)
        if route_cfg is None:
            return await call_next(request)

        current_treasury = get_treasury_address()
        if not current_treasury:
            return _build_402_response(path, method, route_cfg, detail="treasury_configuration_invalid")

        request.state.x402_error = "missing_payment_proof"

        # A. Replay protection challenge-level check
        nonce = request.headers.get("X-Payment-Nonce")
        if nonce:
            from backend.core.database.redis_client import redis_client
            redis_key = f"x402_nonce:{nonce}"
            
            if settings.APP_ENV == "production" and redis_client.is_fallback:
                return _build_402_response(path, method, route_cfg, detail="replay_storage_unavailable")
                
            nonce_exists = await redis_client.get(redis_key)
            if nonce_exists:
                return _build_402_response(path, method, route_cfg, detail="replay_detected")
            await redis_client.set(redis_key, "1", ex=300)

        # B. Data sanitisation filter
        if method in ("POST", "PUT", "PATCH"):
            import re
            try:
                body_bytes = await request.body()
                body_str = body_bytes.decode("utf-8", errors="ignore")
                if re.search(r"api_key=|token=|secret=|sk-proj", body_str, re.IGNORECASE):
                    logger.warning("[x402 PII Filter] Sensitive credentials detected in request body.")
                    return JSONResponse(status_code=400, content={"error": "Sensitive data detected"})
                
                async def receive():
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                request._receive = receive
            except Exception as pii_err:
                logger.error(f"[x402 PII Filter] Error parsing body: {pii_err}")

        # C. Upstream paid gateway trust check
        gateway_secret = request.headers.get("X-Gateway-Secret", "")
        rapidapi_secret = request.headers.get("X-RapidAPI-Proxy-Secret", "")
        
        if gateway_secret or rapidapi_secret:
            configured_secret = settings.UPSTREAM_GATEWAY_SECRET.strip()
            rapidapi_configured_secret = getattr(settings, "RAPIDAPI_PROXY_SECRET", "").strip()
            
            is_valid_gateway = configured_secret and gateway_secret == configured_secret
            is_valid_rapidapi = rapidapi_configured_secret and rapidapi_secret == rapidapi_configured_secret
            
            if is_valid_gateway or is_valid_rapidapi:
                request.state.x402_paid = True
                response = await call_next(request)
                
                # Create and persist a real receipt
                from backend.core.database.database import async_session
                async with async_session() as db:
                    receipt = await create_and_persist_receipt(
                        request, path, method, route_cfg["price_usdc"], "gateway_payment", db
                    )
                
                response.headers["X-Veklom-Receipt-ID"] = receipt["receipt_id"]
                response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
                response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_hash"]
                response.headers["X-Veklom-Cost-USDC"] = str(receipt["amount"])
                response.headers["X-Veklom-Policy-Result"] = receipt["policy_decision"]
                response.headers["X-Veklom-Receipt-URL"] = f"{VEKLOM_API_BASE}/receipts/{receipt['receipt_id']}"
                response.headers["X-Payment-Verified"] = "gateway"
                
                # VNP Stakes Engine Execution: A402 Atomic Service Channel (ASC) release
                if vnp_stake:
                    latency_ms = (time.perf_counter() - vnp_start_time) * 1000
                    response.headers["X-VNP-Latency-Ms"] = f"{latency_ms:.2f}"

                    # Deterministic SLA Threshold (e.g. 800ms)
                    is_passing = (latency_ms <= 800.0)
                    stake_result = "yield" if is_passing else "slashed"
                    response.headers["X-VNP-Stake-Result"] = stake_result
                    
                    try:
                        amt_minor = int((Decimal(str(vnp_stake)) * Decimal("1000000")).to_integral_value(rounding=ROUND_DOWN))
                        # Release ASC settlement via real service
                        from backend.core.database.database import async_session
                        async with async_session() as db:
                            # Use receipt_id as execution_hash for binding
                            await SettlementService.release_settlement(
                                db,
                                uuid.UUID(receipt["receipt_id"].replace("rcpt_", "")),
                                receipt["evidence_hash"],
                                amt_minor if is_passing else 0
                            )
                    except Exception as asc_err:
                        logger.error(f"[ASC] Failed to release settlement: {asc_err}")

                    asyncio.create_task(_persist_vnp_stake_async("default", path, float(vnp_stake), latency_ms, stake_result))
                        
                return response

        # D. JWT verification bypass
        user_payload = await _verify_workspace_auth(request)
        if user_payload:
            user_id = user_payload.get("sub")
            if user_id:
                from sqlalchemy import select, func
                from backend.core.database.database import get_db_session
                from backend.db.models.user import User
                from backend.db.models.workspace import Workspace
                from backend.db.models.ai import ExecutionLog
                from backend.db.models.billing import Subscription, BudgetRule, WalletTransaction
                from backend.db.models.security import KillSwitchState

                async with get_db_session() as db:
                    user_res = await db.execute(select(User).where(User.id == user_id))
                    db_user = user_res.scalar_one_or_none()
                    
                    if db_user:
                        ws_id = db_user.workspace_id or ""

                        # ── OWNER BYPASS ──────────────────────────────────────────────────
                        # The platform owner gets unlimited, unrestricted access to every
                        # paid route with zero gates, zero deductions, zero kill-switch
                        # checks. Nobody else gets this — not even other admins.
                        _owner_email = (
                            os.getenv("PLATFORM_OWNER_EMAIL", "").strip()
                            or settings.PLATFORM_OWNER_EMAIL.strip()
                            or settings.ADMIN_EMAIL.strip()
                        )
                        _is_platform_owner = (
                            (db_user.email or "").lower() == _owner_email.lower()
                        )
                        if _is_platform_owner:
                            logger.info(
                                f"[OWNER BYPASS] {db_user.email} ({db_user.role}) — "
                                f"unrestricted pass-through for {method} {path}"
                            )
                            response = await call_next(request)
                            response.headers["X-Veklom-Owner-Bypass"] = "true"
                            return response
                        # ── END OWNER BYPASS ──────────────────────────────────────────────

                        ks_res = await db.execute(
                            select(KillSwitchState).where(
                                KillSwitchState.workspace_id == ws_id,
                                KillSwitchState.is_active == True
                            )
                        )
                        kill_switch = ks_res.scalar_one_or_none()
                        if kill_switch:
                            return JSONResponse(
                                status_code=402,
                                content={
                                    "detail": f"Emergency halt active: {kill_switch.reason or 'Runaway usage detected'}",
                                    "kill_switch_active": True,
                                    "reason": kill_switch.reason or "Runaway usage detected",
                                    "activated_at": kill_switch.activated_at.isoformat() if kill_switch.activated_at else None
                                }
                            )

                        # Budget constraints verification
                        budget_res = await db.execute(
                            select(BudgetRule).where(
                                BudgetRule.workspace_id == ws_id,
                                BudgetRule.is_active == True
                            )
                        )
                        budget_rules = budget_res.scalars().all()
                        for rule in budget_rules:
                            if rule.current_spend >= rule.limit_usd:
                                # Automatically trigger Cost Kill Switch
                                ks_check = await db.execute(
                                    select(KillSwitchState).where(
                                        KillSwitchState.workspace_id == ws_id,
                                        KillSwitchState.is_active == True
                                    )
                                )
                                if not ks_check.scalar_one_or_none():
                                    new_ks = KillSwitchState(
                                        workspace_id=ws_id,
                                        is_active=True,
                                        reason=f"Automatic halt: Budget rule breached ({rule.name})",
                                        activated_by="system"
                                    )
                                    db.add(new_ks)
                                    await db.commit()
                                
                                return JSONResponse(
                                    status_code=402,
                                    content={
                                        "detail": f"Budget rule breached: {rule.name} limit reached ({rule.current_spend}/{rule.limit_usd} USD).",
                                        "kill_switch_active": True,
                                        "reason": f"Automatic halt: Budget rule breached ({rule.name})"
                                    }
                                )

                        ws_res = await db.execute(select(Workspace).where(Workspace.id == ws_id))
                        db_ws = ws_res.scalar_one_or_none()
                        plan = db_ws.license_tier.lower() if db_ws and db_ws.license_tier else "free"
                        
                        # 1. Community / Free Tier Constraints (Evaluation Mode)
                        if plan in ("free", "community", "none", None):
                            runs_count = await db.scalar(
                                select(func.count(ExecutionLog.id)).where(ExecutionLog.workspace_id == ws_id)
                            ) or 0
                            if runs_count >= 15:
                                return _build_402_response(path, method, route_cfg, detail="free_runs_exhausted")
                            
                            # Gate advanced features for Community users (Pipelines, Deployments, Custom GPC Runs, Marketplace)
                            free_restricted = (
                                "/api/v1/gpc/runs", "/api/v1/pipelines/trigger",
                                "/api/v1/runtime/jobs", "/api/v1/marketplace/acquire",
                                "/api/v1/compliance/report", "/api/v1/evidence/export"
                            )
                            if any(path.startswith(rf) for rf in free_restricted):
                                return JSONResponse(
                                    status_code=403,
                                    content={
                                        "detail": f"The '{route_cfg.get('name', 'advanced feature')}' requires a Growth plan or higher. Please upgrade at /workspace/#/billing.",
                                        "required_tier": "growth",
                                        "workspace_tier": plan
                                    }
                                )
                        
                        # 2. Growth Tier Constraints
                        elif plan == "growth":
                            # Gate heavy enterprise compliance tools (continuous compliance, raw evidence packages)
                            growth_restricted = ("/api/v1/compliance/report", "/api/v1/evidence/export")
                            if any(path.startswith(sf) for sf in growth_restricted):
                                return JSONResponse(
                                    status_code=403,
                                    content={
                                        "detail": f"Tamper-evident Compliance Reporting & Evidence Export require a Sovereign plan or higher. Please upgrade at /workspace/#/billing.",
                                        "required_tier": "sovereign",
                                        "workspace_tier": plan
                                    }
                                )
                        
                        # 3. Process the Reserve, Execute, and Deduct/Refund
                        # Calculate current operating reserve balance from WalletTransactions
                        topups = await db.scalar(
                            select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
                            .where(
                                WalletTransaction.workspace_id == ws_id,
                                WalletTransaction.tx_type.in_(["topup", "activation", "credit"]),
                            )
                        ) or 0.0
                        debits = await db.scalar(
                            select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
                            .where(
                                WalletTransaction.workspace_id == ws_id,
                                WalletTransaction.tx_type == "debit",
                            )
                        ) or 0.0
                        balance = float(Decimal(str(topups)) - abs(Decimal(str(debits))))
                        
                        price_usdc = route_cfg["price_usdc"]
                        
                        # Only check balance if they aren't on a free/community plan with free runs remaining (handled above)
                        if plan not in ("free", "community", "none", None) and balance < price_usdc:
                            return _build_402_response(path, method, route_cfg, detail=f"Insufficient funds in operating reserve. Balance: {balance} USD.")

                        # Atomic Reserve: Create the debit transaction BEFORE execution
                        debit_txn = None
                        if plan not in ("free", "community", "none", None):
                            debit_txn = WalletTransaction(
                                user_id=user_id,
                                workspace_id=ws_id,
                                amount=price_usdc,
                                tx_type="debit",
                                description=f"Reserved {price_usdc} USD for {route_cfg.get('name', 'API Call')} at {path}"
                            )
                            db.add(debit_txn)
                            await db.commit()

                        try:
                            # Process response
                            response = await call_next(request)
                            
                            # If the request failed, refund the reservation
                            if response.status_code >= 400:
                                if debit_txn:
                                    refund_txn = WalletTransaction(
                                        user_id=user_id,
                                        workspace_id=ws_id,
                                        amount=price_usdc,
                                        tx_type="credit",
                                        description=f"Refunded {price_usdc} USD for failed {route_cfg.get('name', 'API Call')} at {path} (Status {response.status_code})"
                                    )
                                    db.add(refund_txn)
                                    await db.commit()
                            else:
                                # Success - Log execution
                                new_log = ExecutionLog(
                                    workspace_id=ws_id,
                                    user_id=user_id,
                                    model=route_cfg.get("name", "Governed Action"),
                                    provider="ollama:qwen2.5:3b",
                                    cost=price_usdc,
                                    status="completed"
                                )
                                db.add(new_log)
                                if debit_txn:
                                    # Update description to reflect settled charge
                                    debit_txn.description = f"Charged {price_usdc} USD for {route_cfg.get('name', 'API Call')} at {path}"
                                await db.commit()
                        except Exception as e:
                            # Refund on exception
                            if debit_txn:
                                refund_txn = WalletTransaction(
                                    user_id=user_id,
                                    workspace_id=ws_id,
                                    amount=price_usdc,
                                    tx_type="credit",
                                    description=f"Refunded {price_usdc} USD for excepted {route_cfg.get('name', 'API Call')} at {path}: {str(e)}"
                                )
                                db.add(refund_txn)
                                await db.commit()
                            raise
                            
                        # Generate receipt
                        async with get_db_session() as db_receipt:
                            receipt = await create_and_persist_receipt(
                                request, path, method, route_cfg["price_usdc"], "jwt_reserve", db_receipt
                            )
                        response.headers["X-Veklom-Receipt-ID"] = receipt["receipt_id"]
                        response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
                        response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_hash"]
                        response.headers["X-Veklom-Cost-USDC"] = str(receipt["amount"])
                        response.headers["X-Veklom-Policy-Result"] = receipt["policy_decision"]
                        response.headers["X-Veklom-Receipt-URL"] = f"{VEKLOM_API_BASE}/receipts/{receipt['receipt_id']}"
                        
                        # VNP Stakes Engine Execution
                        if vnp_stake:
                            latency_ms = (time.perf_counter() - vnp_start_time) * 1000
                            response.headers["X-VNP-Latency-Ms"] = f"{latency_ms:.2f}"
                            if latency_ms > 800.0:
                                response.headers["X-VNP-Stake-Result"] = "slashed"
                                stake_result = "slashed"
                            else:
                                response.headers["X-VNP-Stake-Result"] = "yield"
                                stake_result = "yield"
                                
                            try:
                                amt = float(vnp_stake)
                            except:
                                amt = 0.001
                            asyncio.create_task(_persist_vnp_stake_async(ws_id if 'ws_id' in locals() else "default", path, amt, latency_ms, stake_result))
                                
                        return response

        # E. Verify X-Payment-Proof
        if await _verify_x402_payment(request, route_cfg):
            request.state.x402_paid = True
            response = await call_next(request)
            
            tx_hash = (
                request.headers.get("x-payment") or 
                request.headers.get("X-Payment") or 
                request.headers.get("X-PAYMENT") or 
                request.headers.get("payment-signature") or 
                request.headers.get("Payment-Signature") or 
                request.headers.get("X-Payment-Proof") or 
                "test_tx"
            )
            from backend.core.database.database import get_db_session
            async with get_db_session() as db:
                receipt = await create_and_persist_receipt(
                    request, path, method, route_cfg["price_usdc"], tx_hash, db
                )
            
            # Record real settlement mapping in PostgreSQL
            try:
                from backend.db.models.ledger import SettlementLedger, SettlementStatus
                import uuid
                
                subject_id = "default"
                if method in ("POST", "PUT", "PATCH"):
                    body_bytes = await request.body()
                    if body_bytes:
                        body_json = json.loads(body_bytes.decode("utf-8"))
                        subject_id = body_json.get("tenant_id") or body_json.get("provider_slug") or body_json.get("subject") or "default"
                
                async with get_db_session() as db:
                    is_real_tx = tx_hash.startswith("0x") and len(tx_hash) == 66
                    is_test_proof = getattr(request.state, "test_proof_mode", False)
                    if is_real_tx or is_test_proof:
                        ledger_entry = SettlementLedger(
                            id=uuid.uuid4(),
                            tenant_id=subject_id,
                            provider="veklom-gateway",
                            fee_type="x402_payment",
                            amount=int(route_cfg["price_usdc"] * 1000000),
                            currency="USDC",
                            status=SettlementStatus.SETTLED,
                            idempotency_key=f"pay_{tx_hash}",
                            settlement_tx_hash=tx_hash
                        )
                        db.add(ledger_entry)
                        await db.commit()
                        logger.info(f"[x402] Settlement Ledger recorded successfully for tenant '{subject_id}'")
            except Exception as db_err:
                logger.error(f"[x402] Failed to write SettlementLedger entry: {db_err}")
            
            response.headers["X-Veklom-Receipt-ID"] = receipt["receipt_id"]
            response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
            response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_hash"]
            response.headers["X-Veklom-Cost-USDC"] = str(receipt["amount"])
            response.headers["X-Veklom-Policy-Result"] = receipt["policy_decision"]
            response.headers["X-Veklom-Receipt-URL"] = f"{VEKLOM_API_BASE}/receipts/{receipt['receipt_id']}"
            response.headers["X-Payment-Verified"] = "true"
            if getattr(request.state, "test_proof_mode", False):
                response.headers["X-Payment-Test-Mode"] = "true"
                
            # VNP Stakes Engine Execution
            if vnp_stake:
                latency_ms = (time.perf_counter() - vnp_start_time) * 1000
                response.headers["X-VNP-Latency-Ms"] = f"{latency_ms:.2f}"
                if latency_ms > 800.0:
                    response.headers["X-VNP-Stake-Result"] = "slashed"
                    stake_result = "slashed"
                else:
                    response.headers["X-VNP-Stake-Result"] = "yield"
                    stake_result = "yield"
                    
                try:
                    amt = float(vnp_stake)
                except:
                    amt = 0.001
                asyncio.create_task(_persist_vnp_stake_async("default", path, amt, latency_ms, stake_result))
                    
            return response

        # F. Free tier IP daily quota check
        client_ip = request.client.host if request.client else "unknown"
        day_key = _today_key(client_ip)
        daily_limit = route_cfg.get("free_daily", 0)
        used = _free_usage.get(day_key, 0)

        # Skip free daily trial if missing EDGE_API_KEY / fails closed or if route doesn't support it
        if daily_limit > 0 and used < daily_limit:
            _free_usage[day_key] = used + 1
            request.state.x402_paid = True
            response = await call_next(request)
            
            from backend.core.database.database import get_db_session
            async with get_db_session() as db:
                receipt = await create_and_persist_receipt(
                    request, path, method, route_cfg["price_usdc"], "free_trial", db
                )
                
            response.headers["X-Veklom-Free-Trial"] = "true"
            response.headers["X-Veklom-Free-Remaining"] = str(daily_limit - used - 1)
            response.headers["X-Veklom-Receipt-ID"] = receipt["receipt_id"]
            response.headers["X-Veklom-Request-ID"] = receipt["request_id"]
            response.headers["X-Veklom-Evidence-ID"] = receipt["evidence_hash"]
            return response

        # G. Fail with 402 challenge
        return _build_402_response(path, method, route_cfg, detail=request.state.x402_error)
