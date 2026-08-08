import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.core.database.database import async_session
from backend.core.security.vnp_security import VNPEventVerifier, VNPSecurityError
from backend.db.models.vnp import Api, VnpMetric, VnpNode, VnpNodeHeartbeat, VnpNodeKey, VnpObservation

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

EDGE_SOFTWARE_VERSION = "vnp-edge-probe:v1.1"
VNP_PROBE_INTERVAL_SECONDS = 10
VNP_PROBE_CYCLE_TIMEOUT_SECONDS = 120
VNP_METRIC_RETENTION_DAYS = 7
VNP_PROBE_ADVISORY_LOCK_ID = 610_402_501
VNP_EDGE_DEFAULT_TARGET = "https://api.veklom.com/health"


def configured_edge_nodes() -> list[dict]:
    raw = os.getenv("VNP_EDGE_PROBES_JSON")
    if not raw:
        logger.warning("[VNP Probe Swarm] VNP_EDGE_PROBES_JSON is not configured, skipping edge probes (no fallback)")
        return []
    try:
        nodes = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("[VNP Probe Swarm] invalid VNP_EDGE_PROBES_JSON: %s, skipping edge probes (no fallback)", exc)
        return []
    if not isinstance(nodes, list):
        logger.warning("[VNP Probe Swarm] VNP_EDGE_PROBES_JSON must be a list, skipping edge probes (no fallback)")
        return []
    return nodes


async def edge_target_urls() -> list[str]:
    targets = {VNP_EDGE_DEFAULT_TARGET}
    async with async_session() as db:
        rows = (await db.execute(select(Api.base_url, Api.health_path))).all()
    for base_url, health_path in rows:
        if not base_url:
            continue
        normalized_base = str(base_url).rstrip("/")
        if not normalized_base.startswith("https://api.veklom.com/"):
            continue
        path = health_path or "/health"
        if not path.startswith("/"):
            path = f"/{path}"
        targets.add(f"{normalized_base}{path}")
    return sorted(targets)


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
        response = await client.get(target["url"], timeout=2.0)
        is_up = response.status_code in (200, 401, 403)
    except Exception as exc:
        logger.warning("[VNP Probe] Failed to ping %s: %s", target["id"], exc)

    latency_ms = int((time.monotonic() - start_time) * 1000)
    return target["id"], latency_ms, is_up


async def ping_edge_node(client: httpx.AsyncClient, edge: dict, hub_secret: str, target_url: str) -> dict:
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
            json={"target_url": target_url},
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
        "target_url": target_url,
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
            software_version = (
                (result.get("identity") or {}).get("software_version")
                or (result.get("probe_payload") or {}).get("software_version")
                or EDGE_SOFTWARE_VERSION
            )

            node_stmt = pg_insert(VnpNode).values(
                name=edge["name"],
                physical_location=edge["physical_location"],
                region_code=region_code,
                macro_region=edge["macro_region"],
                jurisdiction=edge["jurisdiction"],
                gdpr_zone=bool(edge["gdpr_zone"]),
                software_version=software_version,
                health_state="reachable" if result["is_up"] else "unreachable",
                registration_status="registered",
                last_seen_at=result["completed_at"] if result["is_up"] else None,
            )
            node_stmt = node_stmt.on_conflict_do_update(
                index_elements=['region_code'],
                set_={
                    "name": node_stmt.excluded.name,
                    "physical_location": node_stmt.excluded.physical_location,
                    "macro_region": node_stmt.excluded.macro_region,
                    "jurisdiction": node_stmt.excluded.jurisdiction,
                    "gdpr_zone": node_stmt.excluded.gdpr_zone,
                    "software_version": node_stmt.excluded.software_version,
                    "health_state": node_stmt.excluded.health_state,
                    "last_seen_at": node_stmt.excluded.last_seen_at,
                }
            ).returning(VnpNode.id, VnpNode.software_version)
            
            node_res = await db.execute(node_stmt)
            node_id, node_software_version = node_res.one()

            identity = result.get("identity") or {}
            identity_sig = identity.get("signature") or {}
            public_key = identity_sig.get("public_key")
            signature_key_id = identity_sig.get("key_id") or f"unregistered:{region_code}"
            
            if public_key and signature_key_id:
                key_stmt = pg_insert(VnpNodeKey).values(
                    node_id=node_id,
                    key_id=signature_key_id,
                    public_key=public_key,
                    active=True,
                    created_at=now,
                ).on_conflict_do_update(
                    index_elements=['key_id'],
                    set_={
                        "node_id": node_id,
                        "public_key": public_key,
                        "active": True,
                        "revoked_at": None,
                    }
                )
                await db.execute(key_stmt)

            probe_payload = result.get("probe_payload") or {}
            probe_sig = probe_payload.get("signature") or {}
            heartbeat_signature = identity_sig.get("sig") or probe_sig.get("sig") or ""
            heartbeat_sequence = (
                await db.execute(
                    select(func.coalesce(func.max(VnpNodeHeartbeat.sequence), 0)).where(
                        VnpNodeHeartbeat.node_id == node_id
                    )
                )
            ).scalar_one() + 1
            heartbeat_payload = identity or probe_payload or {
                "region": region_code,
                "timestamp": result["completed_at"].isoformat(),
                "software_version": node.software_version or EDGE_SOFTWARE_VERSION,
            }
            heartbeat_id = (
                heartbeat_payload.get("heartbeat_id")
                or f"{region_code}:heartbeat:{int(result['completed_at'].timestamp() * 1000)}:{uuid.uuid4().hex[:8]}"
            )
            db.add(
                VnpNodeHeartbeat(
                    heartbeat_id=heartbeat_id,
                    node_id=node_id,
                    timestamp=result["completed_at"],
                    software_version=node_software_version or EDGE_SOFTWARE_VERSION,
                    sequence=int(heartbeat_sequence),
                    signature_key_id=signature_key_id,
                    signature=heartbeat_signature,
                    payload_digest=VNPEventVerifier.payload_digest(heartbeat_payload),
                    created_at=now,
                )
            )

            sequence = (
                await db.execute(
                    select(func.coalesce(func.max(VnpObservation.sequence), 0)).where(
                        VnpObservation.node_id == node_id
                    )
                )
            ).scalar_one() + 1
            previous_signature = (
                await db.execute(
                    select(VnpObservation.signature)
                    .where(VnpObservation.node_id == node_id)
                    .order_by(VnpObservation.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            target_url = probe_payload.get("target_url") or result.get("target_url") or VNP_EDGE_DEFAULT_TARGET
            target_hash = hashlib.sha256(target_url.encode("utf-8")).hexdigest()[:8]
            raw_observation_id = probe_payload.get("observation_id")
            observation_id = (
                f"{raw_observation_id}:{target_hash}"[:100]
                if raw_observation_id
                else f"{region_code}:{int(result['completed_at'].timestamp() * 1000)}:{target_hash}:{uuid.uuid4().hex[:8]}"
            )
            measurement = probe_payload.get("measurement") or {}
            db.add(
                VnpObservation(
                    observation_id=observation_id,
                    node_id=node_id,
                    region=region_code,
                    site_code=region_code,
                    physical_location=edge["physical_location"],
                    target_id=target_url,
                    measurement_profile="edge-target-http",
                    measurement_version="vnp-methodology-v1.0",
                    started_at=datetime.fromisoformat(probe_payload["started_at"]) if probe_payload.get("started_at") else result["started_at"],
                    completed_at=datetime.fromisoformat(probe_payload["completed_at"]) if probe_payload.get("completed_at") else result["completed_at"],
                    total_ms=result["total_ms"],
                    http_status=measurement.get("status_code") or result["status_code"],
                    transport_reachable=bool(result["is_up"]),
                    semantic_assertion=bool(measurement.get("success")) if "success" in measurement else bool(result["is_up"]),
                    response_fingerprint=result["response_fingerprint"],
                    error_code=measurement.get("error_code") or result["error_code"],
                    error_category="transport" if (measurement.get("error_code") or result["error_code"]) else None,
                    sequence=int(sequence),
                    previous_observation_hash=previous_signature,
                    signature_key_id=signature_key_id,
                    signature=probe_sig.get("sig") or "",
                    payload_digest=VNPEventVerifier.payload_digest(probe_payload) if probe_payload else None,
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
        async with async_session() as lock_db:
            lock_acquired = bool(
                (
                    await lock_db.execute(
                        text("SELECT pg_try_advisory_lock(:lock_id)"),
                        {"lock_id": VNP_PROBE_ADVISORY_LOCK_ID},
                    )
                ).scalar_one()
            )
            if not lock_acquired:
                logger.info(
                    "[VNP Probe Swarm] skipping cycle; another BYOS replica holds the probe lock"
                )
                return
            try:
                await _run_locked_cycle(client)
            finally:
                await lock_db.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": VNP_PROBE_ADVISORY_LOCK_ID},
                )
                await lock_db.commit()

    async def _run_locked_cycle(client: httpx.AsyncClient) -> None:
        tasks = [ping_target(client, target) for target in VNP_TARGETS]
        edge_secret = os.getenv("VNP_HUB_SECRET_KEY") or os.getenv("HUB_SECRET_KEY")
        edge_tasks = []
        if edge_secret:
            targets = await edge_target_urls()
            edge_tasks = [
                ping_edge_node(client, edge, edge_secret, target_url)
                for edge in configured_edge_nodes()
                for target_url in targets
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
