import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, func, select

from backend.core.database.database import async_session
from backend.core.security.vnp_security import VNPEventVerifier, VNPSecurityError
from backend.db.models.vnp import VnpMetric, VnpNode, VnpNodeHeartbeat, VnpNodeKey, VnpObservation

logger = logging.getLogger(__name__)

VNP_TARGETS = [
    {"id": "openai", "url": "https://api.openai.com/v1/models"},
    {"id": "anthropic", "url": "https://api.anthropic.com/v1/models"},
    {"id": "stripe", "url": "https://api.stripe.com/v1/charges"},
]

VNP_EDGE_NODES = [
    {
        "name": "Ashburn Node",
        "region_code": "us-ashburn",
        "physical_location": "Ashburn, Virginia, United States",
        "macro_region": "North America",
        "jurisdiction": "US",
        "gdpr_zone": False,
        "url": "http://87.99.154.166:8002/probe/ping",
    },
    {
        "name": "Hillsboro Node",
        "region_code": "us-hillsboro",
        "physical_location": "Hillsboro, Oregon, United States",
        "macro_region": "North America",
        "jurisdiction": "US",
        "gdpr_zone": False,
        "url": "http://vnp-probe-us-hillsboro:8000/probe/ping",
    },
    {
        "name": "Nuremberg Node",
        "region_code": "de-nuremberg",
        "physical_location": "Nuremberg, Germany",
        "macro_region": "Europe",
        "jurisdiction": "DE",
        "gdpr_zone": True,
        "url": "http://91.98.78.218:8002/probe/ping",
    },
    {
        "name": "Falkenstein Node",
        "region_code": "de-falkenstein",
        "physical_location": "Falkenstein, Germany",
        "macro_region": "Europe",
        "jurisdiction": "DE",
        "gdpr_zone": True,
        "url": "http://167.233.202.195:8002/probe/ping",
    },
    {
        "name": "Singapore Node",
        "region_code": "sg-singapore",
        "physical_location": "Singapore",
        "macro_region": "Asia Pacific",
        "jurisdiction": "SG",
        "gdpr_zone": False,
        "url": "http://5.223.90.12:8002/probe/ping",
    },
]

EDGE_SOFTWARE_VERSION = "vnp-edge-probe:v1.1"
VNP_PROBE_INTERVAL_SECONDS = 10
VNP_PROBE_CYCLE_TIMEOUT_SECONDS = 30
VNP_METRIC_RETENTION_DAYS = 7


def configured_edge_nodes() -> list[dict]:
    raw = os.getenv("VNP_EDGE_PROBES_JSON")
    if not raw:
        return VNP_EDGE_NODES
    try:
        nodes = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("[VNP Probe Swarm] invalid VNP_EDGE_PROBES_JSON: %s", exc)
        return VNP_EDGE_NODES
    if not isinstance(nodes, list):
        logger.warning("[VNP Probe Swarm] VNP_EDGE_PROBES_JSON must be a list")
        return VNP_EDGE_NODES
    return nodes


def signed_payload_is_valid(payload: dict) -> bool:
    signature = payload.get("signature") if isinstance(payload, dict) else None
    public_key = signature.get("public_key") if isinstance(signature, dict) else None
    if not public_key:
        return False
    try:
        VNPEventVerifier.verify_event_signature(payload, public_key)
        return True
    except VNPSecurityError:
        return False


async def ping_target(client: httpx.AsyncClient, target: dict) -> tuple[str, int, bool]:
    start_time = time.monotonic()
    is_up = False

    try:
        response = await client.get(target["url"], timeout=5.0)
        is_up = response.status_code in (200, 401, 403)
    except Exception as exc:
        logger.warning("[VNP Probe] Failed to ping %s: %s", target["id"], exc)

    latency_ms = int((time.monotonic() - start_time) * 1000)
    return target["id"], latency_ms, is_up


async def ping_edge_node(client: httpx.AsyncClient, edge: dict, hub_secret: str) -> dict:
    started_at = datetime.now(timezone.utc)
    start_time = time.monotonic()
    status_code = None
    error_code = None
    response_fingerprint = None
    is_up = False
    identity = None
    probe_payload = None
    edge_total_ms = None

    try:
        identity_response = await client.get(
            edge["url"].replace("/probe/ping", "/identity"),
            headers={"x-veklom-hub-key": hub_secret},
            timeout=10.0,
        )
        if identity_response.status_code == 200:
            candidate_identity = identity_response.json()
            if signed_payload_is_valid(candidate_identity):
                identity = candidate_identity

        response = await client.post(
            edge["url"],
            json={"target_url": "https://api.veklom.com/health"},
            headers={"x-veklom-hub-key": hub_secret},
            timeout=10.0,
        )
        status_code = response.status_code
        if response.status_code == 200:
            candidate_payload = response.json()
            if signed_payload_is_valid(candidate_payload):
                probe_payload = candidate_payload
                measurement = candidate_payload.get("measurement") or {}
                edge_total_ms = measurement.get("total_ms")
                response_fingerprint = measurement.get("response_fingerprint")
                is_up = bool(measurement.get("success"))
                status_code = measurement.get("status_code") or status_code
            else:
                error_code = "invalid_signature"
        if response_fingerprint is None:
            response_fingerprint = hashlib.sha256(response.content[:512]).hexdigest()
    except Exception as exc:
        error_code = type(exc).__name__
        logger.warning("[VNP Probe Swarm] edge ping failed for %s: %s", edge.get("region_code"), exc)

    completed_at = datetime.now(timezone.utc)
    hub_roundtrip_ms = int((time.monotonic() - start_time) * 1000)
    total_ms = int(edge_total_ms) if isinstance(edge_total_ms, int) else hub_roundtrip_ms
    return {
        "edge": edge,
        "started_at": started_at,
        "completed_at": completed_at,
        "total_ms": total_ms,
        "hub_roundtrip_ms": hub_roundtrip_ms,
        "status_code": status_code,
        "error_code": error_code,
        "response_fingerprint": response_fingerprint,
        "is_up": is_up,
        "identity": identity,
        "probe_payload": probe_payload,
    }


async def upsert_edge_observations(edge_results: list[dict], hub_secret: str) -> None:
    if not edge_results:
        return

    now = datetime.now(timezone.utc)
    async with async_session() as db:
        for result in edge_results:
            edge = result["edge"]
            region_code = edge["region_code"]
            node = (
                await db.execute(select(VnpNode).where(VnpNode.region_code == region_code))
            ).scalar_one_or_none()
            if node is None:
                node = VnpNode(
                    name=edge["name"],
                    physical_location=edge["physical_location"],
                    region_code=region_code,
                    macro_region=edge["macro_region"],
                    jurisdiction=edge["jurisdiction"],
                    gdpr_zone=bool(edge["gdpr_zone"]),
                    software_version=EDGE_SOFTWARE_VERSION,
                    health_state="unknown",
                    registration_status="registered",
                )
                db.add(node)
                await db.flush()
            else:
                node.name = edge["name"]
                node.physical_location = edge["physical_location"]
                node.macro_region = edge["macro_region"]
                node.jurisdiction = edge["jurisdiction"]
                node.gdpr_zone = bool(edge["gdpr_zone"])
                node.software_version = (
                    (result.get("identity") or {}).get("software_version")
                    or (result.get("probe_payload") or {}).get("software_version")
                    or EDGE_SOFTWARE_VERSION
                )

            if result["is_up"]:
                node.last_seen_at = result["completed_at"]
                node.health_state = "reachable"
            else:
                node.health_state = "unreachable"

            identity = result.get("identity") or {}
            identity_sig = identity.get("signature") or {}
            public_key = identity_sig.get("public_key")
            signature_key_id = identity_sig.get("key_id") or f"unregistered:{region_code}"
            if public_key and signature_key_id:
                existing_key = (
                    await db.execute(select(VnpNodeKey).where(VnpNodeKey.key_id == signature_key_id))
                ).scalar_one_or_none()
                if existing_key is None:
                    db.add(
                        VnpNodeKey(
                            node_id=node.id,
                            key_id=signature_key_id,
                            public_key=public_key,
                            active=True,
                            created_at=now,
                        )
                    )
                else:
                    existing_key.node_id = node.id
                    existing_key.public_key = public_key
                    existing_key.active = True
                    existing_key.revoked_at = None

            probe_payload = result.get("probe_payload") or {}
            probe_sig = probe_payload.get("signature") or {}
            heartbeat_signature = identity_sig.get("sig") or probe_sig.get("sig") or ""
            db.add(
                VnpNodeHeartbeat(
                    heartbeat_id=probe_payload.get("heartbeat_id") or uuid.uuid4().hex,
                    node_id=node.id,
                    timestamp=result["completed_at"],
                    software_version=node.software_version or EDGE_SOFTWARE_VERSION,
                    signature_key_id=signature_key_id,
                    signature=heartbeat_signature,
                    created_at=now,
                )
            )

            sequence = (
                await db.execute(
                    select(func.count(VnpObservation.id)).where(VnpObservation.node_id == node.id)
                )
            ).scalar_one() + 1
            previous_signature = (
                await db.execute(
                    select(VnpObservation.signature)
                    .where(VnpObservation.node_id == node.id)
                    .order_by(VnpObservation.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            observation_id = probe_payload.get("observation_id") or f"{region_code}:{int(result['completed_at'].timestamp() * 1000)}:{uuid.uuid4().hex[:8]}"
            measurement = probe_payload.get("measurement") or {}
            db.add(
                VnpObservation(
                    observation_id=observation_id,
                    node_id=node.id,
                    region=region_code,
                    physical_location=edge["physical_location"],
                    target_id=probe_payload.get("target_url") or "https://api.veklom.com/health",
                    measurement_profile="edge-target-http",
                    measurement_version="vnp-methodology-v1.0",
                    started_at=datetime.fromisoformat(probe_payload["started_at"]) if probe_payload.get("started_at") else result["started_at"],
                    completed_at=datetime.fromisoformat(probe_payload["completed_at"]) if probe_payload.get("completed_at") else result["completed_at"],
                    total_ms=result["total_ms"],
                    http_status=measurement.get("status_code") or result["status_code"],
                    response_fingerprint=result["response_fingerprint"],
                    error_code=measurement.get("error_code") or result["error_code"],
                    sequence=int(sequence),
                    previous_observation_hash=previous_signature,
                    signature_key_id=signature_key_id,
                    signature=probe_sig.get("sig") or "",
                    created_at=now,
                )
            )

        await db.commit()


async def run_vnp_probes() -> None:
    """Persist live physical probe latency for the public VNP directory/status."""
    logger.info("[VNP Probe Swarm] Initialized physical edge probes.")
    print("[VNP Probe Swarm] Initialized physical edge probes.", flush=True)

    interval = float(os.getenv("VNP_PROBE_INTERVAL_SECONDS", str(VNP_PROBE_INTERVAL_SECONDS)))
    cycle_timeout = float(
        os.getenv("VNP_PROBE_CYCLE_TIMEOUT_SECONDS", str(VNP_PROBE_CYCLE_TIMEOUT_SECONDS))
    )
    retention_days = int(
        os.getenv("VNP_METRIC_RETENTION_DAYS", str(VNP_METRIC_RETENTION_DAYS))
    )

    async def run_cycle(client: httpx.AsyncClient) -> None:
        tasks = [ping_target(client, target) for target in VNP_TARGETS]
        edge_secret = os.getenv("VNP_HUB_SECRET_KEY") or os.getenv("HUB_SECRET_KEY")
        edge_tasks = []
        if edge_secret:
            edge_tasks = [
                ping_edge_node(client, edge, edge_secret)
                for edge in configured_edge_nodes()
            ]
        else:
            logger.warning(
                "[VNP Probe Swarm] edge heartbeat polling skipped; "
                "VNP_HUB_SECRET_KEY is not configured"
            )

        results = await asyncio.gather(*tasks)
        edge_results = await asyncio.gather(*edge_tasks) if edge_tasks else []

        now = datetime.now(timezone.utc)
        async with async_session() as db:
            for api_name, latency_ms, is_up in results:
                db.add(
                    VnpMetric(
                        api_name=api_name,
                        latency_ms=latency_ms,
                        is_up=is_up,
                        measured_at=now,
                    )
                )
            cutoff = now - timedelta(days=retention_days)
            await db.execute(delete(VnpMetric).where(VnpMetric.measured_at < cutoff))
            await db.commit()
        if edge_secret:
            await upsert_edge_observations(edge_results, edge_secret)

        summary = ", ".join(
            f"{api_name}={latency_ms}ms/{'up' if is_up else 'down'}"
            for api_name, latency_ms, is_up in results
        )
        if edge_results:
            edge_summary = ", ".join(
                f"{r['edge']['region_code']}={r['total_ms']}ms/{'up' if r['is_up'] else 'down'}"
                for r in edge_results
            )
            summary = f"{summary}; edges: {edge_summary}"
        logger.info("[VNP Probe Swarm] recorded physical probes: %s", summary)
        print(f"[VNP Probe Swarm] recorded physical probes: {summary}", flush=True)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                await asyncio.wait_for(run_cycle(client), timeout=cycle_timeout)
                await asyncio.sleep(interval)
            except asyncio.TimeoutError:
                logger.warning(
                    "[VNP Probe Swarm] probe cycle timed out after %.1fs",
                    cycle_timeout,
                )
                await asyncio.sleep(min(interval * 2, 60))
            except Exception as exc:
                logger.warning("[VNP Probe Swarm] probe cycle failed: %s", exc)
                print(f"[VNP Probe Swarm] probe cycle failed: {type(exc).__name__}: {exc}", flush=True)
                await asyncio.sleep(min(interval * 2, 60))
