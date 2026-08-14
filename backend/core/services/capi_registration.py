"""Fail-soft BYOS self-registration with cAPI."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from backend.core.config.settings import Settings, settings

logger = logging.getLogger(__name__)
REGISTRATION_TIMEOUT_SECONDS = 2.0
RETRY_SECONDS = 5.0
DEFAULT_REGISTRY_TTL_MS = 300_000


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


def _heartbeat_interval_seconds(current_settings: Settings) -> float:
    raw_ttl = getattr(
        current_settings,
        "CAPI_REGISTRY_TTL_MS",
        os.getenv("CAPI_REGISTRY_TTL_MS", DEFAULT_REGISTRY_TTL_MS),
    )
    try:
        ttl_ms = int(raw_ttl)
    except (TypeError, ValueError):
        ttl_ms = DEFAULT_REGISTRY_TTL_MS
    if ttl_ms <= 0:
        ttl_ms = DEFAULT_REGISTRY_TTL_MS
    return max(ttl_ms / 1_000 * 0.8, 0.001)


async def _wait_for_stop(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        pass


def _headers(current_settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {current_settings.CAPI_REGISTRY_TOKEN.strip()}"}


async def register_with_capi(
    current_settings: Settings = settings, transport: httpx.AsyncBaseTransport | None = None
) -> bool:
    capi_url = current_settings.CAPI_BACKEND_URL.strip()
    token = current_settings.CAPI_REGISTRY_TOKEN.strip()
    if not capi_url or not token:
        logger.info("BYOS cAPI registration skipped: CAPI_BACKEND_URL or CAPI_REGISTRY_TOKEN is not configured")
        return False

    try:
        async with httpx.AsyncClient(timeout=REGISTRATION_TIMEOUT_SECONDS, transport=transport) as client:
            response = await client.post(
                f"{capi_url.rstrip('/')}/api/v1/registry/register",
                json=build_registration_payload(),
                headers=_headers(current_settings),
            )
            response.raise_for_status()
        logger.info("BYOS registered executable capabilities with cAPI")
        return True
    except Exception as exc:  # noqa: BLE001 - registration must not block startup
        logger.warning("BYOS cAPI registration failed (%s); continuing without registration", type(exc).__name__)
        return False


async def heartbeat_until_missing(
    current_settings: Settings,
    stop: asyncio.Event,
    transport: httpx.AsyncBaseTransport | None = None,
) -> bool:
    """Refresh BYOS registration until cAPI reports it missing or shutdown begins."""
    capi_url = current_settings.CAPI_BACKEND_URL.strip()
    if not capi_url:
        return False

    while not stop.is_set():
        await _wait_for_stop(stop, _heartbeat_interval_seconds(current_settings))
        if stop.is_set():
            return False
        try:
            async with httpx.AsyncClient(timeout=REGISTRATION_TIMEOUT_SECONDS, transport=transport) as client:
                response = await client.post(
                    f"{capi_url.rstrip('/')}/api/v1/registry/heartbeat",
                    json={"service_name": "byos"},
                    headers=_headers(current_settings),
                )
        except httpx.HTTPError as exc:
            logger.warning("BYOS cAPI heartbeat failed (%s)", type(exc).__name__)
            continue

        if 200 <= response.status_code < 300:
            continue
        if response.status_code == 404:
            logger.info("BYOS cAPI registration is missing; re-registering")
            return True
        logger.warning("BYOS cAPI heartbeat rejected with status %s", response.status_code)
    return False


async def maintain_capi_registration(
    current_settings: Settings, stop: asyncio.Event, transport: httpx.AsyncBaseTransport | None = None
) -> None:
    """Keep BYOS registered without treating transport health as authority."""
    while not stop.is_set():
        if await register_with_capi(current_settings, transport):
            await heartbeat_until_missing(current_settings, stop, transport)
        else:
            await _wait_for_stop(stop, RETRY_SECONDS)
