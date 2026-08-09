"""Fail-soft BYOS self-registration with cAPI."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.core.config.settings import settings

logger = logging.getLogger(__name__)
REGISTRATION_TIMEOUT_SECONDS = 2.0


def build_registration_payload() -> dict[str, Any]:
    """Build the executable BYOS capability registration payload."""
    return {
        "service_name": "byos",
        "base_url": "https://api.veklom.com",
        "telemetry_supported": True,
        "capabilities": [
            {
                "name": "governed_execution",
                "description": "Submit an intent to BYOS's governed cAPI execution boundary.",
                "endpoint": "https://api.veklom.com/api/v1/capi/execute",
                "input_schema": {
                    "type": "object",
                    "required": ["agent_id", "pgl_id", "target_protocol", "action", "payload"],
                    "properties": {
                        "action": {"type": "string"},
                        "agent_id": {"type": "string"},
                        "pgl_id": {"type": "string"},
                        "target_protocol": {"type": "string"},
                        "payload": {"type": "object"},
                        "mission_id": {"type": "string"},
                        "delegation_chain": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "category": "service",
                "risk_level": "high",
                "requires_approval": True,
            },
            {
                "name": "build_evidence_packs",
                "description": "Build a sealed evidence pack for an authority run.",
                "endpoint": "https://api.veklom.com/api/v1/evidence/build",
                "input_schema": {
                    "type": "object",
                    "required": ["authority_run_id"],
                    "properties": {
                        "authority_run_id": {"type": "string"},
                        "workspace_id": {"type": "string"},
                        "agent_id": {"type": "string"},
                    },
                },
                "category": "service",
                "risk_level": "medium",
                "requires_approval": True,
            },
            {
                "name": "compile_governed_plans",
                "description": "Compile a governed plan from an existing pipeline.",
                "endpoint": "https://api.veklom.com/api/v1/gpc/compile",
                "input_schema": {
                    "type": "object",
                    "required": ["pipeline_id"],
                    "properties": {"pipeline_id": {"type": "string"}},
                },
                "category": "service",
                "risk_level": "high",
                "requires_approval": True,
            },
        ],
        "metadata": {
            "protocol": "veklom-service-registration-v1",
            "manifest": "https://api.veklom.com/protocol.json",
        },
    }


async def register_with_capi() -> bool:
    capi_url = settings.CAPI_BACKEND_URL.strip()
    token = settings.CAPI_REGISTRY_TOKEN.strip()
    if not capi_url or not token:
        logger.info("BYOS cAPI registration skipped: CAPI_BACKEND_URL or CAPI_REGISTRY_TOKEN is not configured")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=REGISTRATION_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{capi_url.rstrip('/')}/api/v1/registry/register",
                json=build_registration_payload(),
                headers=headers,
            )
            response.raise_for_status()
        logger.info("BYOS registered executable capabilities with cAPI")
        return True
    except Exception as exc:  # noqa: BLE001 - registration must not block startup
        logger.warning("BYOS cAPI registration failed (%s); continuing without registration", type(exc).__name__)
        return False
