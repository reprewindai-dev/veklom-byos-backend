from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# ---------------------------------------------------------
# W3C Trace Context & Base Observability
# ---------------------------------------------------------
class W3CTraceContext(BaseModel):
    """W3C Trace Context headers for distributed tracing."""
    traceparent: str = Field(..., description="W3C traceparent (version-traceid-parentid-traceflags)")
    tracestate: Optional[str] = Field(None, description="W3C tracestate (vendor specific routing)")

class CloudEventBase(BaseModel):
    """Base schema for standard CloudEvents (used by Replay)."""
    specversion: str = "1.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    type: str
    datacontenttype: str = "application/json"
    time: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]

# ---------------------------------------------------------
# Identity, Transport, and Protocol Adapters
# ---------------------------------------------------------
class AmphotericContext(BaseModel):
    """Unified transport and protocol detection context."""
    transport: Literal["rest", "mcp", "webmcp", "ui"]
    protocol_version: str
    authenticated_identity: Optional[str] = Field(None, description="Identity established by SPIFFE/mTLS before HTTP")
    client_heuristics: Dict[str, Any] = Field(default_factory=dict, description="Headers, IPs, unverified hints")

class ExecutionIdentity(BaseModel):
    """PGL-anchored identity representing WHO is executing."""
    pgl_id: str
    workspace_id: str
    assurance_level: Literal["unverified", "verified", "hardware_attested"]
    birth_certificate_hash: Optional[str] = None
    status: Literal["active", "suspended", "revoked"]

# ---------------------------------------------------------
# Governance, Authorization & Integrity
# ---------------------------------------------------------
class ExecutionAuthorization(BaseModel):
    """EAT (Execution Authorization Token) - Single-use token for side-effects."""
    eat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    audience: str
    scope: str
    nonce: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    single_use: bool = True
    cappo_decision_ref: str

class SourceAttestation(BaseModel):
    """RepoGate supply chain attestation (in-toto/SLSA mapping)."""
    attestation_id: str
    slsa_level: int
    repository: str
    commit_sha: str
    build_digest: str
    policy_findings: List[str]
    approval_state: Literal["pending", "approved", "rejected"]
    timestamp: datetime
    dsse_signature: str

# ---------------------------------------------------------
# Core Product Objects: Context & Connection
# ---------------------------------------------------------
class ConnectionContext(BaseModel):
    """The canonical context passed through the unified fabric."""
    connection_id: str
    operation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    actor_id: str
    agent_id: Optional[str] = None
    intent: str
    idempotency_key: str
    deadline_at: datetime
    trace_context: W3CTraceContext
    evidence_mode: Literal["consequential", "ephemeral"] = "consequential"

class ConnectionRequirements(BaseModel):
    """Requirements resolved by Interlink-CAPI Resource Server."""
    identity_scheme: Literal["pgl"] = "pgl"
    identity_status: Literal["active"] = "active"
    identity_assurance: Literal["verified", "hardware_attested"]
    source_integrity_minimum_state: Literal["approved"] = "approved"
    execution_authority_scheme: Literal["cappo_eat_v1"] = "cappo_eat_v1"
    require_eat: bool = True
    payment_scheme: Literal["x402", "none"] = "none"
    evidence_receipt: Literal["pgl", "none"] = "pgl"
    evidence_replay: Literal["consequential", "none"] = "consequential"

class TrustConnection(BaseModel):
    """The central, canonical connection object for Veklom."""
    connection_id: str = Field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:12]}")
    version: str = "1.0"
    workspace_id: str
    status: Literal["active", "suspended", "revoked", "closed"]
    participants: Dict[str, Any]
    identity_refs: List[str]
    capabilities: List[str]
    amphoteric_context: AmphotericContext
    source_integrity_ref: Optional[str] = None
    execution_authority: Literal["cappo"] = "cappo"
    payment_scheme: Literal["x402", "none"] = "none"
    evidence_refs: List[str] = Field(default_factory=list)
    replay_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ---------------------------------------------------------
# Evidence & Settlement
# ---------------------------------------------------------
class PGLReceipt(BaseModel):
    """Cryptographic proof of an event, anchored to the ledger."""
    receipt_id: str
    operation_id: str
    connection_id: str
    event_hash: str
    dsse_signature: str
    timestamp: datetime

class ReplayPacketSegment(BaseModel):
    """Content-addressed chunk of a replay packet."""
    segment_hash: str # SHA-256 content address
    operation_id: str
    connection_id: str
    events: List[CloudEventBase]
    previous_segment_hash: Optional[str] = None

class ReplayPacket(BaseModel):
    """The master wrapper for a complete replay."""
    packet_id: str
    schema_version: str = "v1"
    connection_id: str
    root_segment_hash: str
    final_segment_hash: Optional[str] = None
    dsse_signature: str
