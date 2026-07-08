from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import hashlib
import json
import uuid

# ============================================================================
# SCHEMA VERSION
# ============================================================================

MCPAPI_V2_SCHEMA_VERSION = "1.0.0"

# ============================================================================
# ENUMS
# ============================================================================

class GovernanceTier(str, Enum):
    SYSTEM = "system"
    USER = "user"
    SERVICE = "service"

class AnomalyType(str, Enum):
    REQUEST_SPIKE = "request_spike"
    FAILURE_SPIKE = "failure_spike"
    NEW_CAPABILITY_ACCESS = "new_capability_access"
    OFF_HOURS_ACTIVITY = "off_hours_activity"
    UNUSUAL_PATTERN = "unusual_pattern"
    CAPABILITY_MUTATION = "capability_mutation"
    DELEGATION_CHAIN_EXPLOIT = "delegation_chain_exploit"

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecommendedAction(str, Enum):
    LOG = "log"
    ALERT = "alert"
    QUARANTINE = "quarantine"
    BLOCK = "block"

class QuarantineStatus(str, Enum):
    QUARANTINED = "quarantined"
    APPROVED = "approved"
    DENIED = "denied"
    AUTO_RELEASED = "auto_released"

# ============================================================================
# CORE IDENTITY & PERMISSIONS
# ============================================================================

class AuthorityPermissions(BaseModel):
    can_execute: bool
    can_delegate: bool
    can_read_ledger: bool
    can_write_ledger: bool

class AuthorityBundle(BaseModel):
    bundle_id: str
    agent_id: str
    issued_by: str
    issued_at: str
    expires_at: str
    mcp_tools: List[str]
    permissions: AuthorityPermissions
    signature: str

class VeklomAgent(BaseModel):
    agent_id: str
    agent_name: str
    mission_file: str
    authority_bundle_id: str
    owner_id: str
    created_at: str
    public_key: str
    governance_tier: GovernanceTier
    associated_mcp_servers: List[str]

# ============================================================================
# SAFETY LAYER (ANOMALIES & QUARANTINE)
# ============================================================================

class BehavioralBaseline(BaseModel):
    agent_id: str
    observation_window_days: int
    avg_requests_per_hour: float
    std_dev_requests_per_hour: float
    avg_failure_rate: float
    std_dev_failure_rate: float
    typical_capabilities: Dict[str, int]
    typical_time_windows: List[int]
    typical_error_types: Dict[str, int]
    confidence_score: float
    last_updated: str
    is_locked: bool

class CurrentMetric(BaseModel):
    requests_per_hour: float
    failure_rate: float
    new_capabilities: List[str]
    time_of_day: int
    requests_in_window: int

class AnomalyDetection(BaseModel):
    detection_id: str
    agent_id: str
    detected_at: str
    anomaly_type: AnomalyType
    baseline: BehavioralBaseline
    current_metric: CurrentMetric
    deviation_score: float
    anomaly_score: float
    severity: Severity
    recommended_action: RecommendedAction
    evidence_hash: str

class QuarantinedRequest(BaseModel):
    quarantine_id: str
    original_request: Dict[str, Any]
    original_timestamp: str
    quarantine_reason: str
    anomalies_detected: List[AnomalyDetection]
    trust_suppression_applied: bool
    suppressed_trust_score: float
    approval_required: bool
    approvers_required: int
    approvals_received: List[str]
    approval_deadline: str
    status: QuarantineStatus
    resolution_timestamp: Optional[str] = None
    resolution_reason: Optional[str] = None

class ApprovalSignature(BaseModel):
    approver_id: str
    approved_at: str
    signature: str
    approval_evidence: str
    trust_score: float

class ApprovalQuorum(BaseModel):
    approval_id: str
    quarantine_id: str
    required_approvers: List[str]
    current_approvals: Dict[str, ApprovalSignature]
    required_count: int
    threshold_reached: bool
    approval_deadline: str
    escalation_path: List[str]
    escalation_triggered: bool

# ============================================================================
# AUDIT & LEDGER
# ============================================================================

class GnomLedgerEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    event_type: str  # "created" | "executed" | "denied" | "escalated"
    capability_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    evidence_hash: str
    trust_delta: float
    new_trust_score: float
    metadata: Dict[str, Any]

class VeklomPGLEntry(BaseModel):
    who: str
    what: str
    when: str
    why: str
    how: str
    proof: str
    birth_certificate: Optional[str] = None
