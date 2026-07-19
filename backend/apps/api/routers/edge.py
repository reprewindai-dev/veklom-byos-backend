"""Veklom Edge & Legacy Ingestion Router.

Enables legacy network, industrial, and IoT protocols (SNMP, Modbus TCP, OPC UA, MQTT, polling, and webhooks)
to ingest signal metrics cleanly, safely, and securely into the governed Veklom workspace and runs queue.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge", tags=["Edge Ingestion"])


# ---------------------------------------------------------------------------
# Ingestion Pydantic Schemas & OpenAPI Examples
# ---------------------------------------------------------------------------

class LegacyWebhookPayload(BaseModel):
    source_protocol: str = Field(..., description="Ingress protocol: snmp, modbus, mqtt, opc_ua, webhook, polling")
    source_system: str = Field(..., description="Origin identifier of the gateway, machine, or router")
    workspace_id: Optional[str] = Field(None, description="Optional target Veklom workspace UUID")
    tenant_id: Optional[str] = Field(None, description="Optional tenant UUID")
    signal_type: str = Field(..., description="Metric or indicator category, e.g. system_failure, temperature, alert")
    payload: Dict[str, Any] = Field(..., description="Raw dictionary containing the unstructured signal data")
    severity: str = Field("info", description="Signal alert level: info, low, medium, warning, high, critical")
    timestamp: Optional[datetime] = Field(None, description="Optional external timestamp of the event")
    correlation_id: Optional[str] = Field(None, description="Optional external trace identifier")
    raw_ref: Optional[str] = Field(None, description="Optional raw reference string")
    normalized_fields: Dict[str, Any] = Field(default_factory=dict, description="Pre-normalized fields if already structured")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source_protocol": "snmp",
                    "source_system": "core-router-01",
                    "workspace_id": "89078ab2-12e4-4fa7-a3cc-1afd2137d473",
                    "signal_type": "link_down",
                    "severity": "critical",
                    "payload": {
                        "trap_oid": "1.3.6.1.6.3.1.1.5.3",
                        "error_status": 2,
                        "variables": {
                            "1.3.6.1.2.1.2.2.1.8.1": 2
                        }
                    }
                },
                {
                    "source_protocol": "modbus",
                    "source_system": "hvac-controller-04",
                    "workspace_id": "89078ab2-12e4-4fa7-a3cc-1afd2137d473",
                    "signal_type": "compressor_overheat",
                    "severity": "high",
                    "payload": {
                        "unit_id": 12,
                        "function_code": 3,
                        "registers": [850],
                        "exception_code": 2
                    }
                },
                {
                    "source_protocol": "webhook",
                    "source_system": "auth-gateway",
                    "workspace_id": "89078ab2-12e4-4fa7-a3cc-1afd2137d473",
                    "signal_type": "brute_force_detected",
                    "severity": "critical",
                    "payload": {
                        "ip_address": "198.51.100.42",
                        "failed_attempts": 45,
                        "user_agent": "Mozilla/5.0"
                    }
                },
                {
                    "source_protocol": "mqtt",
                    "source_system": "power-meter-3b",
                    "workspace_id": "89078ab2-12e4-4fa7-a3cc-1afd2137d473",
                    "signal_type": "voltage_sag",
                    "severity": "warning",
                    "payload": {
                        "topic": "telemetry/power/sag",
                        "voltage": 185.4,
                        "phase": "A"
                    }
                }
            ]
        }
    }


class CanonicalEdgeResponse(BaseModel):
    accepted: bool = Field(..., description="Indicates if the event was accepted for processing")
    normalized: bool = Field(..., description="Indicates if standard normalizations were successfully applied")
    event_id: str = Field(..., description="Unique generated message identifier")
    correlation_id: str = Field(..., description="Traceability correlation ID for log mapping")
    canonical_message: str = Field(..., description="Human-readable summary of signal processing results")
    audit_status: str = Field(..., description="Durable audit logging status: persisted | not_configured | failed")
    security_event_status: str = Field(..., description="High/critical alarm escalation status: persisted | not_configured | failed")
    routing_status: str = Field(..., description="Veklom run flow dispatcher status: routed | logged_only | not_configured")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking warning messages encountered during parsing")


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

    protocol = protocol.lower()

    if protocol == "snmp":
        varbinds = payload.get("varbinds") or payload.get("variables") or {}
        trap_oid = payload.get("trap_oid") or payload.get("oid")
        
        metric = None
        if varbinds:
            metric = list(varbinds.values())[0] if isinstance(varbinds, dict) else varbinds
        else:
            metric = payload.get("value") or payload.get("oid_value")
            
        normalized["metric_value"] = metric
        
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
        val = payload.get("node_value") or payload.get("value")
        status_code = str(payload.get("status_code") or payload.get("status") or "0x00000000").lower()
        
        normalized["metric_value"] = val
        is_bad_status = status_code.startswith("0x8") or "bad" in status_code
        normalized["warning"] = is_bad_status or "error" in status_code
        normalized["raw_status"] = "bad_status" if is_bad_status else "good"
        normalized["protocol_metadata"] = {
            "node_id": payload.get("node_id"),
            "status_code": status_code,
            "source_timestamp": payload.get("source_timestamp")
        }
        
    else:
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
from backend.core.security.auth import get_current_user_or_api_key


# ---------------------------------------------------------------------------
# Webhook Ingest Endpoint (Production-Safe & Fully Compliant)
# ---------------------------------------------------------------------------

@router.post("/input/webhook", response_model=CanonicalEdgeResponse)
async def ingest_webhook_event(
    payload: LegacyWebhookPayload,
    current_user: Any = Depends(get_current_user_or_api_key),
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported protocol '{payload.source_protocol}'. Must be one of: {', '.join(valid_protocols)}"
        )

    # 2. Strict Severity Validation
    valid_severities = {"info", "low", "medium", "warning", "high", "critical"}
    if payload.severity.lower() not in valid_severities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported severity '{payload.severity}'. Must be one of: {', '.join(valid_severities)}"
        )

    msg_id = str(uuid.uuid4())
    correlation_id = payload.correlation_id or f"corr_{msg_id[:8]}"
    
    # 3. Normalize legacy payload
    norm_fields = normalize_payload(payload.payload, payload.source_protocol)

    audit_status = "not_configured"
    security_event_status = "not_configured"
    routing_status = "not_configured"
    warnings = []

    # 4. Audit logging via existing db models
    try:
        from backend.db.models.security import AuditLog
        audit_log = AuditLog(
            workspace_id=current_user.workspace_id,
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
        audit_status = "persisted"
    except Exception as e:
        logger.error(f"Failed to create edge audit log model: {e}")
        audit_status = "failed"

    # 5. Security escalation for high/critical events
    if payload.severity.lower() in ("high", "critical"):
        try:
            from backend.db.models.security import SecurityEvent
            sec_event = SecurityEvent(
                workspace_id=current_user.workspace_id,
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
            security_event_status = "persisted"
        except Exception as e:
            logger.error(f"Failed to create edge security event model: {e}")
            security_event_status = "failed"

    # 6. Commit Database Updates
    if audit_status == "persisted" or security_event_status == "persisted":
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to commit DB transaction: {e}")
            if audit_status == "persisted":
                audit_status = "failed"
            if security_event_status == "persisted":
                security_event_status = "failed"

    # 7. Route to Veklom Run workflow if severity is high or critical
    if payload.severity.lower() in ("high", "critical"):
        try:
            from backend.services.orchestrator import RunOrchestrator
            from backend.db.models.run import VeklomRun
            orchestrator = RunOrchestrator(db)
            intent_payload = {
                "goal": f"Normalize and handle legacy industrial edge signal: {payload.signal_type}",
                "edge_signal": {
                    "message_id": msg_id,
                    "source_protocol": payload.source_protocol,
                    "source_system": payload.source_system,
                    "signal_type": payload.signal_type,
                    "severity": payload.severity,
                },
                "escalated": True
            }
            # Create asynchronous execution plan using the actual run model
            await orchestrator.create_run(
                workspace_id=current_user.workspace_id,
                tenant_id=current_user.workspace_id,
                actor_id="system_edge_connector",
                intent=intent_payload
            )
            routing_status = "routed"
        except Exception as e:
            logger.error(f"Failed to route edge signal into Veklom runs queue: {e}")
            routing_status = "failed"
    else:
        routing_status = "logged_only"

    # Generate standard canonical success message
    canonical_message = f"Veklom Ingestion: successfully accepted {payload.source_protocol} signal from {payload.source_system} (severity: {payload.severity})."

    return CanonicalEdgeResponse(
        accepted=True,
        normalized=True,
        event_id=msg_id,
        correlation_id=correlation_id,
        canonical_message=canonical_message,
        audit_status=audit_status,
        security_event_status=security_event_status,
        routing_status=routing_status,
        warnings=warnings
    )


# ---------------------------------------------------------------------------
# Connector Status Protocol Stubs (Safe, Ingest-Only, Disabled by Default)
# ---------------------------------------------------------------------------

@router.get("/connectors/status")
async def get_connectors_status(current_user: Any = Depends(get_current_user_or_api_key)):
    """Inquires the operational status of all legacy industrial protocols."""
    return {
        "webhook_connector": {
            "status": "active",
            "supported": True,
            "write_control": False,
            "ingestion_only": True,
            "no_network_polling_starts_automatically": True
        },
        "mqtt_connector": {
            "status": "enabled" if settings.EDGE_MQTT_ENABLED else "disabled",
            "supported": settings.EDGE_MQTT_ENABLED,
            "write_control": False,
            "ingestion_only": True,
            "no_network_polling_starts_automatically": True
        },
        "snmp_connector": {
            "status": "enabled" if settings.EDGE_SNMP_ENABLED else "disabled",
            "supported": settings.EDGE_SNMP_ENABLED,
            "write_control": False,
            "ingestion_only": True,
            "no_network_polling_starts_automatically": True
        },
        "modbus_connector": {
            "status": "enabled" if settings.EDGE_MODBUS_ENABLED else "disabled",
            "supported": settings.EDGE_MODBUS_ENABLED,
            "write_control": False,
            "ingestion_only": True,
            "no_network_polling_starts_automatically": True
        },
        "opc_ua_connector": {
            "status": "enabled" if settings.EDGE_OPC_ENABLED else "disabled",
            "supported": settings.EDGE_OPC_ENABLED,
            "write_control": False,
            "ingestion_only": True,
            "no_network_polling_starts_automatically": True
        },
        "polling_connector": {
            "status": "enabled" if settings.EDGE_POLLING_ENABLED else "disabled",
            "supported": settings.EDGE_POLLING_ENABLED,
            "write_control": False,
            "ingestion_only": True,
            "no_network_polling_starts_automatically": True
        }
    }
