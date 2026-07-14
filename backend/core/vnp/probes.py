import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select

from backend.core.database.database import async_session
from backend.db.models.vnp import VnpMetric, VnpNode, VnpNodeHeartbeat, VnpObservation

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
        "url": "http://10.0.0.1:8002/probe/ping",
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

EDGE_SOFTWARE_VERSION = "vnp-edge-probe:v1.0"


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


def sign_edge_payload(secret: str, payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), encoded, hashlib.sha256).hexdigest()


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

    try:
        response = await client.post(
            edge["url"],
            json={"target_url": "https://api.veklom.com/health"},
            headers={"x-veklom-hub-key": hub_secret},
            timeout=10.0,
        )
        status_code = response.status_code
        is_up = response.status_code == 200
        response_fingerprint = hashlib.sha256(response.content[:512]).hexdigest()
    except Exception as exc:
        error_code = type(exc).__name__
        logger.warning("[VNP Probe Swarm] edge ping failed for %s: %s", edge.get("region_code"), exc)

    completed_at = datetime.now(timezone.utc)
    total_ms = int((time.monotonic() - start_time) * 1000)
    return {
        "edge": edge,
        "started_at": started_at,
        "completed_at": completed_at,
        "total_ms": total_ms,
        "status_code": status_code,
        "error_code": error_code,
        "response_fingerprint": response_fingerprint,
        "is_up": is_up,
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
                node.software_version = EDGE_SOFTWARE_VERSION

            if result["is_up"]:
                node.last_seen_at = result["completed_at"]
                node.health_state = "reachable"
            else:
                node.health_state = "unreachable"

            signature_key_id = f"hub-hmac:{region_code}"
            heartbeat_payload = {
                "node_id": str(node.id),
                "region_code": region_code,
                "timestamp": result["completed_at"].isoformat(),
                "software_version": EDGE_SOFTWARE_VERSION,
                "status_code": result["status_code"],
            }
            db.add(
                VnpNodeHeartbeat(
                    node_id=node.id,
                    timestamp=result["completed_at"],
                    software_version=EDGE_SOFTWARE_VERSION,
                    signature_key_id=signature_key_id,
                    signature=sign_edge_payload(hub_secret, heartbeat_payload),
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
            observation_id = f"{region_code}:{int(result['completed_at'].timestamp() * 1000)}:{uuid.uuid4().hex[:8]}"
            observation_payload = {
                "observation_id": observation_id,
                "node_id": str(node.id),
                "region_code": region_code,
                "started_at": result["started_at"].isoformat(),
                "completed_at": result["completed_at"].isoformat(),
                "total_ms": result["total_ms"],
                "http_status": result["status_code"],
                "sequence": int(sequence),
                "previous_observation_hash": previous_signature,
            }
            db.add(
                VnpObservation(
                    observation_id=observation_id,
                    node_id=node.id,
                    region=region_code,
                    physical_location=edge["physical_location"],
                    target_id="vnp-edge-probe:/probe/ping",
                    measurement_profile="wireguard-edge-heartbeat",
                    measurement_version="vnp-methodology-v1.0",
                    started_at=result["started_at"],
                    completed_at=result["completed_at"],
                    total_ms=result["total_ms"],
                    http_status=result["status_code"],
                    response_fingerprint=result["response_fingerprint"],
                    error_code=result["error_code"],
                    sequence=int(sequence),
                    previous_observation_hash=previous_signature,
                    signature_key_id=signature_key_id,
                    signature=sign_edge_payload(hub_secret, observation_payload),
                    created_at=now,
                )
            )

        await db.commit()


async def run_vnp_probes() -> None:
    """Persist live physical probe latency for the public VNP directory/status."""
    logger.info("[VNP Probe Swarm] Initialized physical edge probes.")
    print("[VNP Probe Swarm] Initialized physical edge probes.", flush=True)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                tasks = [ping_target(client, target) for target in VNP_TARGETS]
                edge_secret = os.getenv("VNP_HUB_SECRET_KEY") or os.getenv("HUB_SECRET_KEY")
                edge_tasks = []
                if edge_secret:
                    edge_tasks = [ping_edge_node(client, edge, edge_secret) for edge in configured_edge_nodes()]
                else:
                    logger.warning("[VNP Probe Swarm] edge heartbeat polling skipped; VNP_HUB_SECRET_KEY is not configured")

                results = await asyncio.gather(*tasks)
                edge_results = await asyncio.gather(*edge_tasks) if edge_tasks else []

                async with async_session() as db:
                    for api_name, latency_ms, is_up in results:
                        db.add(
                            VnpMetric(
                                api_name=api_name,
                                latency_ms=latency_ms,
                                is_up=is_up,
                                measured_at=datetime.now(timezone.utc),
                            )
                        )
                    await db.commit()
                await upsert_edge_observations(edge_results, edge_secret) if edge_secret else None
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
            except Exception as exc:
                logger.exception("[VNP Probe Swarm] probe cycle failed: %s", exc)
                print(f"[VNP Probe Swarm] probe cycle failed: {type(exc).__name__}: {exc}", flush=True)

            await asyncio.sleep(10)
