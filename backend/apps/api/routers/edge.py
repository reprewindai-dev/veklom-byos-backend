"""Veklom Edge & Legacy Ingestion Router.

Enables legacy network, industrial, and IoT protocols (SNMP, Modbus TCP, OPC UA, MQTT, polling, and webhooks)
to ingest signal metrics cleanly, safely, and securely into the governed Veklom workspace and runs queue.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.db.models.security import AuditLog, SecurityEvent
from backend.db.models.run import VeklomRun
from backend.services.orchestrator import RunOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge", tags=["Edge Ingestion"])


# ---------------------------------------------------------------------------
# Ingestion Pydantic Schemas
# ---------------------------------------------------------------------------

class LegacyWebhookPayload(BaseModel):
    source_protocol: str = Field(..., description="Ingress protocol: snmp, modbus, mqtt, opc_ua, webhook, polling")
    source_system: str = Field(..., description="Origin identifier of the gateway, machine, or router")
    workspace_id: str = Field(..., description="Target Veklom workspace UUID")
    signal_type: str = Field(..., description="Metric or indicator category, e.g. system_failure, temperature, alert")
    payload: Dict[str, Any] = Field(..., description="Raw dictionary containing the unstructured signal data")
    severity: str = Field("info", description="Signal alert level: info, warning, medium, high, critical")
    correlation_id: Optional[str] = Field(None, description="Optional external trace identifier")


class CanonicalEdgeMessage(BaseModel):
    message_id: str
    source_protocol: str
    source_system: str
    workspace_id: str
    signal_type: str
    payload: Dict[str, Any]
    severity: str
    timestamp: str
    correlation_id: str
    normalized_fields: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helper Normalizer & Policy Filter
# ---------------------------------------------------------------------------

def normalize_payload(payload: Dict[str, Any], protocol: str) -> Dict[str, Any]:
    """
    Examines unstructured payload and extracts a standardized schema
    containing keys like metric_value, warning, raw_status.
    Matches standard IT and industrial SCADA / OT patterns.
    """
    normalized = {
        "metric_value": None,
        "warning": False,
        "raw_status": "unknown",
        "protocol_metadata": {}
    }
    
    if not payload:
        return normalized

    if protocol == "snmp":
        # Standard SNMP: OIDs, varbinds, trap_oid, agent_ip
        # e.g., payload = {"trap_oid": "1.3.6.1.6.3.1.1.5.3", "varbinds": {"1.3.6.1.2.1.2.2.1.8.1": 2}}
        varbinds = payload.get("varbinds") or payload.get("variables") or {}
        trap_oid = payload.get("trap_oid") or payload.get("oid")
        
        # Check varbinds first, or fall back to sys_status/sys_descr
        metric = None
        if varbinds:
            # Get the first varbind value as metric
            metric = list(varbinds.values())[0] if isinstance(varbinds, dict) else varbinds
        else:
            metric = payload.get("value") or payload.get("oid_value")
            
        normalized["metric_value"] = metric
        
        # In SNMP traps, a status code (like ifOperStatus) of 2 (down) or trap linkDown (1.3.6.1.6.3.1.1.5.3) is critical
        is_link_down = trap_oid in ("1.3.6.1.6.3.1.1.5.3", "linkDown")
        has_error_status = payload.get("error_status", 0) != 0
        has_critical_vars = any(
            "error" in str(k).lower() or "fail" in str(v).lower() or v == 2
            for k, v in (varbinds.items() if isinstance(varbinds, dict) else [])
        )
        
        normalized["warning"] = is_link_down or has_error_status or has_critical_vars or "trap_alert" in payload
        normalized["raw_status"] = "link_down" if is_link_down else "error" if (has_error_status or has_critical_vars) else "active"
        normalized["protocol_metadata"] = {
            "trap_oid": trap_oid,
            "error_index": payload.get("error_index", 0),
            "sys_up_time": payload.get("sys_up_time")
        }
        
    elif protocol == "modbus":
        # Standard Modbus: registers, coils, unit_id, function_code, exception_code
        # e.g., payload = {"unit_id": 1, "registers": [234, 12], "function_code": 3, "exception_code": None}
        registers = payload.get("registers") or payload.get("coil_value") or payload.get("coils")
        fc = payload.get("function_code") or payload.get("fc")
        exception = payload.get("exception_code") or payload.get("exception")
        
        if isinstance(registers, list) and len(registers) > 0:
            normalized["metric_value"] = registers[0] if len(registers) == 1 else registers
        else:
            normalized["metric_value"] = registers
            
        normalized["warning"] = exception is not None or fc == 0x80 or payload.get("error") is not None
        normalized["raw_status"] = "exception_fault" if normalized["warning"] else "operational"
        normalized["protocol_metadata"] = {
            "unit_id": payload.get("unit_id") or payload.get("slave_id", 1),
            "function_code": fc,
            "exception_code": exception
        }
        
    elif protocol == "opc_ua":
        # Standard OPC UA: node_id, node_value, status_code, server_timestamp
        # e.g., payload = {"node_id": "ns=2;s=Device1.Temp", "node_value": 45.2, "status_code": "0x00000000"}
        val = payload.get("node_value") or payload.get("value")
        status_code = str(payload.get("status_code") or payload.get("status") or "0x00000000").lower()
        
        normalized["metric_value"] = val
        # Status code beginning with 0x8 represents Bad status in OPC UA specifications
        is_bad_status = status_code.startswith("0x8") or "bad" in status_code
        normalized["warning"] = is_bad_status or "error" in status_code
        normalized["raw_status"] = "bad_status" if is_bad_status else "good"
        normalized["protocol_metadata"] = {
            "node_id": payload.get("node_id"),
            "status_code": status_code,
            "source_timestamp": payload.get("source_timestamp")
        }
        
    else:
        # Standard HTTP webhooks and generic formats
        normalized["metric_value"] = payload.get("value") or payload.get("metric")
        normalized["warning"] = "alert" in str(payload).lower() or payload.get("status") in ("fail", "error", "degraded")
        normalized["raw_status"] = payload.get("status") or "unknown"
        normalized["protocol_metadata"] = {
            "headers": payload.get("headers"),
            "event_type": payload.get("event")
        }
        
    return normalized


# ---------------------------------------------------------------------------
# API Key Verification Dependency
# ---------------------------------------------------------------------------

async def verify_edge_api_key(
    x_edge_api_key: Optional[str] = Header(None, alias="X-Edge-Api-Key")
) -> str:
    """Verifies that the incoming request carries a valid Edge API Key."""
    if not x_edge_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Edge-Api-Key authentication header."
        )
    if x_edge_api_key != settings.EDGE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Edge API Key credentials."
        )
    return x_edge_api_key


# ---------------------------------------------------------------------------
# Webhook Ingest Endpoint
# ---------------------------------------------------------------------------

@router.post("/input/webhook", response_model=CanonicalEdgeMessage)
async def ingest_webhook_event(
    payload: LegacyWebhookPayload,
    x_key: str = Depends(verify_edge_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified ingestion endpoint accepting webhook signals from legacy systems.
    Validates, normalizes, logs to audit/security DB and routes critical alarms to Veklom run queue.
    """
    # 1. Strict Protocol Validation
    valid_protocols = {"snmp", "modbus", "mqtt", "opc_ua", "webhook", "polling"}
    if payload.source_protocol.lower() not in valid_protocols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported protocol '{payload.source_protocol}'. Must be one of: {', '.join(valid_protocols)}"
        )

    # 2. Strict Severity Validation
    valid_severities = {"info", "warning", "medium", "high", "critical"}
    if payload.severity.lower() not in valid_severities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported severity '{payload.severity}'. Must be one of: {', '.join(valid_severities)}"
        )

    msg_id = str(uuid.uuid4())
    correlation_id = payload.correlation_id or f"corr_{msg_id[:8]}"
    now_str = datetime.now(timezone.utc).isoformat()
    
    # 3. Normalize legacy payload
    norm_fields = normalize_payload(payload.payload, payload.source_protocol)
    
    canonical_msg = CanonicalEdgeMessage(
        message_id=msg_id,
        source_protocol=payload.source_protocol.lower(),
        source_system=payload.source_system,
        workspace_id=payload.workspace_id,
        signal_type=payload.signal_type,
        payload=payload.payload,
        severity=payload.severity.lower(),
        timestamp=now_str,
        correlation_id=correlation_id,
        normalized_fields=norm_fields
    )

    # 4. Audit logging
    try:
        audit_log = AuditLog(
            workspace_id=payload.workspace_id,
            action=f"edge.ingest.{payload.source_protocol}",
            resource_type="edge_event",
            resource_id=msg_id,
            details={
                "message_id": msg_id,
                "source_system": payload.source_system,
                "signal_type": payload.signal_type,
                "severity": payload.severity,
                "normalized": norm_fields
            }
        )
        db.add(audit_log)
    except Exception as e:
        logger.error(f"Failed to write edge audit log: {e}")

    # 5. Security escalation for high/critical events
    if payload.severity.lower() in ("high", "critical"):
        try:
            sec_event = SecurityEvent(
                workspace_id=payload.workspace_id,
                event_type="edge_alert_escalation",
                threat_type="legacy_system_anomaly",
                severity=payload.severity.lower(),
                description=f"Escalated edge signal from {payload.source_system} ({payload.source_protocol})",
                details={
                    "message_id": msg_id,
                    "signal_type": payload.signal_type,
                    "raw_payload": payload.payload,
                    "normalized": norm_fields
                }
            )
            db.add(sec_event)
        except Exception as e:
            logger.error(f"Failed to write edge security event: {e}")

    # 6. Commit DB changes
    await db.commit()

    # 7. Route to Veklom Run workflow if severity is warning, high or critical
    if payload.severity.lower() in ("warning", "medium", "high", "critical"):
        try:
            orchestrator = RunOrchestrator(db)
            intent_payload = {
                "goal": f"Normalize and handle legacy industrial edge signal: {payload.signal_type}",
                "edge_signal": canonical_msg.model_dump(),
                "escalated": payload.severity.lower() in ("high", "critical")
            }
            # Create asynchronous execution plan
            await orchestrator.create_run(
                workspace_id=payload.workspace_id,
                tenant_id=payload.workspace_id,
                actor_id="system_edge_connector",
                intent=intent_payload
            )
            logger.info(f"Routed edge signal {msg_id} into Veklom Run queue")
        except Exception as e:
            logger.error(f"Failed to route edge signal into runs queue: {e}")

    return canonical_msg


# ---------------------------------------------------------------------------
# Stubs & Connectors status (All SNMP/Modbus/OPC/MQTT disabled by default)
# ---------------------------------------------------------------------------

@router.get("/connectors/status")
async def get_connectors_status(x_key: str = Depends(verify_edge_api_key)):
    """Inquires the operational status of all legacy industrial protocols."""
    return {
        "webhook_connector": {"status": "active", "features": ["http_ingestion", "canonical_normalization"]},
        "mqtt_connector": {
            "status": "enabled" if settings.EDGE_MQTT_ENABLED else "disabled",
            "info": "MQTT broker listener scaffolding."
        },
        "snmp_connector": {
            "status": "enabled" if settings.EDGE_SNMP_ENABLED else "disabled",
            "info": "SNMP Trap listener module."
        },
        "modbus_connector": {
            "status": "enabled" if settings.EDGE_MODBUS_ENABLED else "disabled",
            "info": "Modbus TCP master poll gateway."
        },
        "opc_ua_connector": {
            "status": "enabled" if settings.EDGE_OPC_ENABLED else "disabled",
            "info": "OPC UA client telemetry client."
        }
    }
