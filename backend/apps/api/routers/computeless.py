from fastapi import APIRouter
import time
import uuid
import hashlib
import json

router = APIRouter(prefix="/computeless", tags=["Computeless"])

@router.post("/execute")
async def execute_computeless(payload: dict):
    # This route is a demo/reference until actual authority path is wired.
    # Must not claim 'success' for work that did not happen.
    
    receipt_id = str(uuid.uuid4())
    timestamp = time.time()
    
    # Calculate a real hash of the payload instead of a fake one
    payload_str = json.dumps(payload, sort_keys=True).encode("utf-8")
    actual_hash = hashlib.sha256(payload_str).hexdigest()
    
    return {
        "status": "demo_reference",
        "receipt_id": receipt_id,
        "evidence_hash": actual_hash,
        "timestamp": timestamp,
        "signature": None,
        "signature_state": "UNSIGNED",
        "evidence_class": "LOCAL_RECEIPT",
        "limitation": "Demo/Reference execution. Not bound by CAPPO authority, completely unsigned."
    }

@router.get("/telemetry")
async def get_computeless_telemetry():
    return {
        "latency_ms": None,
        "throughput_tps": None,
        "active_sessions": None,
        "compute_cost_credits": None,
        "evidence_class": "STATIC_ASSERTION",
        "status": "UNMEASURED"
    }

@router.get("/evidence")
async def get_computeless_evidence():
    timestamp = time.time()
    empty_payload = json.dumps({"type": "empty_reference"}).encode("utf-8")
    actual_hash = hashlib.sha256(empty_payload).hexdigest()
    
    return {
        "status": "pending_verification",
        "evidence_hash": actual_hash,
        "timestamp": timestamp,
        "signer": None,
        "signature_state": "UNSIGNED",
        "evidence_class": "LOCAL_RECEIPT",
        "limitation": "A hash is not a signature. Lacks execution_id, authority digest, identity binding, and PGL commitment."
    }
