from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(tags=["AsyncAPI"])

ASYNCAPI_MANIFEST: Dict[str, Any] = {
    "asyncapi": "2.6.0",
    "info": {
        "title": "Veklom Event Mesh",
        "version": "1.0.0",
        "description": "Event-driven architecture for the Veklom Sovereign AI Hub. This defines the reactive events (stakes, evidence, probes) that agents and UACP V3 can subscribe to."
    },
    "servers": {
        "production_sse": {
            "url": "https://api.veklom.com/api/v1/vnp/stream/sse",
            "protocol": "http",
            "description": "Server-Sent Events (SSE) stream for real-time telemetry and events."
        },
        "production_ws": {
            "url": "wss://api.veklom.com/api/v1/vnp/stream/ws",
            "protocol": "ws",
            "description": "WebSocket connection for interactive event streaming."
        }
    },
    "channels": {
        "/api/v1/vnp/stream/sse": {
            "subscribe": {
                "summary": "Subscribe to real-time mesh events.",
                "operationId": "subscribeToEvents",
                "message": {
                    "oneOf": [
                        {"$ref": "#/components/messages/VnpStakePlaced"},
                        {"$ref": "#/components/messages/VnpStakeSlashed"},
                        {"$ref": "#/components/messages/VnpStakeYield"},
                        {"$ref": "#/components/messages/EvidenceEmitted"},
                        {"$ref": "#/components/messages/EvidenceVerified"},
                        {"$ref": "#/components/messages/ProbeResult"}
                    ]
                }
            }
        }
    },
    "components": {
        "messages": {
            "VnpStakePlaced": {
                "name": "vnp.stake.placed",
                "title": "VNP Stake Placed",
                "summary": "Emitted when a new performance bond is staked.",
                "payload": {
                    "type": "object",
                    "properties": {
                        "stake_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "api_id": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                }
            },
            "VnpStakeSlashed": {
                "name": "vnp.stake.slashed",
                "title": "VNP Stake Slashed",
                "summary": "Emitted when a node fails an SLA and its bond is slashed.",
                "payload": {
                    "type": "object",
                    "properties": {
                        "stake_id": {"type": "string"},
                        "slashed_amount": {"type": "number"},
                        "reason": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                }
            },
            "VnpStakeYield": {
                "name": "vnp.stake.yield",
                "title": "VNP Stake Yield",
                "summary": "Emitted when a node successfully completes an SLA and earns yield.",
                "payload": {
                    "type": "object",
                    "properties": {
                        "stake_id": {"type": "string"},
                        "yield_amount": {"type": "number"},
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                }
            },
            "EvidenceEmitted": {
                "name": "evidence.emitted",
                "title": "Evidence Emitted",
                "summary": "Emitted when execution evidence is committed to the ledger.",
                "payload": {
                    "type": "object",
                    "properties": {
                        "evidence_id": {"type": "string"},
                        "pipeline_id": {"type": "string"},
                        "hash": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                }
            },
            "EvidenceVerified": {
                "name": "evidence.verified",
                "title": "Evidence Verified",
                "summary": "Emitted when a piece of evidence passes zero-knowledge verification.",
                "payload": {
                    "type": "object",
                    "properties": {
                        "evidence_id": {"type": "string"},
                        "verifier": {"type": "string"},
                        "status": {"type": "string", "enum": ["valid", "invalid"]},
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                }
            },
            "ProbeResult": {
                "name": "probe.result",
                "title": "Probe Result",
                "summary": "Emitted when an active network probe completes its check.",
                "payload": {
                    "type": "object",
                    "properties": {
                        "probe_id": {"type": "string"},
                        "latency_ms": {"type": "number"},
                        "success": {"type": "boolean"},
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                }
            }
        }
    }
}

@router.get("/asyncapi.json")
async def get_asyncapi_schema():
    return ASYNCAPI_MANIFEST
