"""Unified Replay Ingestion Contract."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class CloudEvent(BaseModel):
    """Standard CloudEvent schema."""
    specversion: str = "1.0"
    id: str
    source: str
    type: str
    datacontenttype: str = "application/json"
    time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: Dict[str, Any]

class ReplayPacketV1(BaseModel):
    """Replay Packet schema using SHA-256 content hash as primary lookup key."""
    packet_id: str  # The SHA-256 hash of the content
    event: CloudEvent
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ReplayIngestion:
    """Handles unified ingestion of Replay events."""
    
    def __init__(self):
        # In a real implementation, this might connect to a message queue or DB
        self._store: Dict[str, ReplayPacketV1] = {}

    def emit(self, event: CloudEvent) -> str:
        """
        Emit a CloudEvent to the Replay system.
        Returns the SHA-256 packet_id of the generated ReplayPacket.
        """
        # 1. Serialize the event to a canonical JSON string
        event_json = json.dumps(event.model_dump(), sort_keys=True, separators=(',', ':'))
        
        # 2. Compute the SHA-256 hash to act as the CID-style lookup key
        packet_id = hashlib.sha256(event_json.encode('utf-8')).hexdigest()
        
        # 3. Create the packet
        packet = ReplayPacketV1(
            packet_id=packet_id,
            event=event
        )
        
        # 4. Store the packet (in-memory for now, real implementation would persist to DB/Queue)
        # Replay finalization failing open (via async queue) is the only correct fail-open
        self._store[packet_id] = packet
        
        # Note: We simulate async queue fail-open behavior here
        print(f"[replay-ingestion] Emitted ReplayPacket {packet_id} for event {event.type}")
        
        return packet_id

    def get_packet(self, packet_id: str) -> Optional[ReplayPacketV1]:
        """Fetch a specific tool call/event evidence by its SHA-256 hash."""
        return self._store.get(packet_id)

replay_ingestion = ReplayIngestion()
