"""Deterministic AI infrastructure contract.

This module is intentionally static and side-effect free. It is the backend
source contract for how Veklom, UACP, GPC, and py03-irongrid divide ownership.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


STACK_CONTRACT: dict[str, Any] = {
    "category": "deterministic_ai_infrastructure",
    "thesis": (
        "The bottleneck is routing, orchestration, governance, memory movement, "
        "verification, latency, and infrastructure economics; not the model alone."
    ),
    "repos": {
        "veklom-byos-backend": {
            "role": "sovereign_runtime_infrastructure",
            "owns": [
                "tenant isolated AI execution",
                "billing and wallet enforcement",
                "runtime route contracts",
                "audit and evidence APIs",
                "buyer deploy package",
                "private model provider integration",
            ],
            "must_not_own": [
                "constitutional policy authorship",
                "agent council governance semantics",
                "low-level packet or mesh transport",
            ],
        },
        "uacp": {
            "role": "constitutional_coordination_layer",
            "owns": [
                "operator hierarchy",
                "constitutional gates",
                "worker escalation doctrine",
                "cross-agent coordination policy",
                "evidence-gated autonomous cycles",
            ],
            "must_not_own": [
                "buyer runtime billing",
                "tenant data plane storage",
                "provider execution credentials",
            ],
        },
        "gpc": {
            "role": "deterministic_planning_execution_compiler",
            "owns": [
                "intent to governed execution graph compilation",
                "policy gate ordering",
                "step-level execution state",
                "plan replay surface",
            ],
            "must_not_own": [
                "constitutional veto authority",
                "network substrate selection",
                "billing ledger finality",
            ],
        },
        "py03-irongrid": {
            "role": "deterministic_routing_mesh",
            "owns": [
                "route scoring",
                "latency and pressure topology",
                "mesh path selection",
                "data movement economics",
                "execution substrate telemetry",
            ],
            "must_not_own": [
                "tenant auth",
                "billing policy",
                "constitutional governance",
            ],
        },
    },
    "non_negotiables": [
        "all revenue-impacting execution is authenticated",
        "all paid access is entitlement-gated",
        "all autonomous actions are auditable",
        "regulated workloads require evidence gates before execution",
        "routing decisions must be replayable from request facts and policy version",
        "private runtime paths are preferred for sovereign or regulated workloads",
    ],
}


ROUTING_POLICY_VERSION = "2026-05-22.det-ai-infra.v1"


ROUTING_TOPOLOGY: dict[str, Any] = {
    "policy_version": ROUTING_POLICY_VERSION,
    "substrate": "py03-irongrid",
    "route_classes": {
        "sovereign_private": {
            "description": "Private runtime path for regulated or data-sovereign workloads.",
            "providers": ["vllm", "ollama", "openai-compatible-private"],
            "required_controls": ["workspace_isolation", "audit_hash", "evidence_capture"],
        },
        "cost_optimized": {
            "description": "Low-cost execution path for non-regulated workloads with flexible latency.",
            "providers": ["groq", "huggingface", "gemini", "openai"],
            "required_controls": ["wallet_debit", "usage_metering", "audit_hash"],
        },
        "latency_critical": {
            "description": "Fast path for interactive workloads with strict latency limits.",
            "providers": ["groq", "openai", "private-edge"],
            "required_controls": ["rate_limit", "wallet_debit", "audit_hash"],
        },
        "verification_heavy": {
            "description": "Multi-step path for high-risk output requiring policy checks and replay.",
            "providers": ["private-primary", "openai-fallback", "anthropic-fallback"],
            "required_controls": ["policy_gate", "evidence_capture", "human_review_if_high_risk"],
        },
    },
    "decision_inputs": [
        "workspace_entitlement",
        "estimated_tokens",
        "compliance_tags",
        "sovereignty_region",
        "max_latency_ms",
        "budget_remaining_usd",
        "route_pressure",
        "provider_health",
    ],
}


ECONOMIC_PRESSURE_MODEL: dict[str, Any] = {
    "objective": "minimize token waste, egress waste, latency variance, and verification rework",
    "risk_factors": {
        "o_n2_agent_mesh": "Naive all-to-all agent chatter creates token and latency explosion.",
        "public_internet_variance": "Uncontrolled routing creates nondeterministic latency and replay gaps.",
        "context_duplication": "Repeated prompt payloads increase spend without increasing state quality.",
        "ungoverned_chains": "Unverified agent chains amplify hallucinations and audit cost.",
    },
    "controls": [
        "compile plans before execution",
        "route by workload class and policy tags",
        "capture evidence at execution boundaries",
        "prefer sovereign runtime for regulated data",
        "meter usage before and after execution",
    ],
}


def get_stack_contract() -> dict[str, Any]:
    return deepcopy(STACK_CONTRACT)


def get_routing_topology() -> dict[str, Any]:
    return deepcopy(ROUTING_TOPOLOGY)


def get_economic_pressure_model() -> dict[str, Any]:
    return deepcopy(ECONOMIC_PRESSURE_MODEL)


def classify_route(
    *,
    compliance_tags: list[str],
    max_latency_ms: int | None,
    estimated_tokens: int,
    sovereignty_region: str | None,
) -> tuple[str, list[str]]:
    tags = {tag.lower() for tag in compliance_tags}
    reasons: list[str] = []

    regulated_tags = {"hipaa", "gdpr", "soc2", "pci", "phi", "pii", "regulated"}
    if tags & regulated_tags or sovereignty_region:
        reasons.append("regulated_or_sovereign_workload")
        return "sovereign_private", reasons

    if max_latency_ms is not None and max_latency_ms <= 1500:
        reasons.append("strict_latency_budget")
        return "latency_critical", reasons

    if "verification" in tags or "high-risk" in tags or "audit-heavy" in tags:
        reasons.append("verification_required")
        return "verification_heavy", reasons

    if estimated_tokens >= 32000:
        reasons.append("large_context_cost_pressure")
        return "cost_optimized", reasons

    reasons.append("default_cost_quality_path")
    return "cost_optimized", reasons
