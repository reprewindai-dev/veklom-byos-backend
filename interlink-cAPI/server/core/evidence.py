"""Signed evidence envelope creation."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Mock in-memory store for evidence
_receipt_store = {}

async def seal_intent(intent: Any) -> str:
    """Creates a signed evidence receipt for an intent."""
    receipt_id = f"rcp_{uuid.uuid4().hex[:12]}"
    receipt = {
        "id": receipt_id,
        "type": "intent_approved",
        "agent_id": intent.agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hash": hashlib.sha256(json.dumps(intent.model_dump()).encode()).hexdigest()
    }
    _receipt_store[receipt_id] = receipt
    return receipt_id

async def seal_denial(intent: Any, reason: str) -> str:
    """Creates a signed evidence receipt for a denial."""
    receipt_id = f"rcp_{uuid.uuid4().hex[:12]}"
    receipt = {
        "id": receipt_id,
        "type": "intent_denied",
        "reason": reason,
        "agent_id": intent.agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    _receipt_store[receipt_id] = receipt
    return receipt_id

async def get_receipt(receipt_id: str) -> Optional[Dict[str, Any]]:
    return _receipt_store.get(receipt_id)

async def get_recent_audit(limit: int = 100) -> List[Dict[str, Any]]:
    return list(_receipt_store.values())[-limit:]
