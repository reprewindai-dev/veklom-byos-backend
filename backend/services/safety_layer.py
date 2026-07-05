import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import json

from backend.models.mcpapi_v2 import (
    BehavioralBaseline,
    CurrentMetric,
    AnomalyDetection,
    AnomalyType,
    Severity,
    RecommendedAction,
    QuarantinedRequest,
    QuarantineStatus,
    ApprovalQuorum,
    ApprovalSignature
)

# ============================================================================
# BEHAVIORAL BASELINE SERVICE
# ============================================================================

class BehavioralBaselineService:
    def __init__(self):
        self.baselines: Dict[str, BehavioralBaseline] = {}
        self.observations: Dict[str, List[Dict[str, Any]]] = {}
        self.BASELINE_LOCK_DAYS = 30

    def get_baseline(self, agent_id: str) -> Optional[BehavioralBaseline]:
        return self.baselines.get(agent_id)

    # Note: Full statistical baseline building logic omitted for brevity, 
    # assumes pre-populated or handled asynchronously in production.

# ============================================================================
# ANOMALY DETECTION SERVICE
# ============================================================================

class AnomalyDetectionService:
    def __init__(self, baseline_service: BehavioralBaselineService):
        self.baseline_service = baseline_service
        self.anomalies: List[AnomalyDetection] = []
        self.ANOMALY_THRESHOLD = 2.0

    def detect_anomalies(self, agent_id: str, current_metric: CurrentMetric) -> List[AnomalyDetection]:
        baseline = self.baseline_service.get_baseline(agent_id)
        if not baseline or baseline.confidence_score < 50:
            return [] # Not enough data
        
        detected = []

        # 1. Request spike
        if baseline.std_dev_requests_per_hour > 0:
            req_dev = (current_metric.requests_per_hour - baseline.avg_requests_per_hour) / baseline.std_dev_requests_per_hour
            if abs(req_dev) > self.ANOMALY_THRESHOLD:
                detected.append(self._create_anomaly(agent_id, AnomalyType.REQUEST_SPIKE, current_metric, baseline, abs(req_dev)))

        # 2. New Capability
        new_caps = [cap for cap in current_metric.new_capabilities if cap not in baseline.typical_capabilities]
        if new_caps:
            detected.append(self._create_anomaly(agent_id, AnomalyType.NEW_CAPABILITY_ACCESS, current_metric, baseline, len(new_caps)))
            
        # 3. Off hours
        if current_metric.time_of_day not in baseline.typical_time_windows:
            detected.append(self._create_anomaly(agent_id, AnomalyType.OFF_HOURS_ACTIVITY, current_metric, baseline, 1.0))

        self.anomalies.extend(detected)
        return detected

    def _create_anomaly(self, agent_id: str, anomaly_type: AnomalyType, current_metric: CurrentMetric, baseline: BehavioralBaseline, deviation_score: float) -> AnomalyDetection:
        anomaly_score = min(100.0, (abs(deviation_score) / 5.0) * 100.0)
        
        severity = Severity.LOW
        action = RecommendedAction.LOG

        if anomaly_score > 80:
            severity = Severity.CRITICAL
            action = RecommendedAction.BLOCK
        elif anomaly_score > 60:
            severity = Severity.HIGH
            action = RecommendedAction.QUARANTINE
        elif anomaly_score > 40:
            severity = Severity.MEDIUM
            action = RecommendedAction.QUARANTINE

        evidence_hash = hashlib.sha256(json.dumps({
            "agent_id": agent_id,
            "anomaly_type": anomaly_type.value,
            "timestamp": datetime.utcnow().isoformat()
        }).encode()).hexdigest()

        return AnomalyDetection(
            detection_id=str(uuid.uuid4()),
            agent_id=agent_id,
            detected_at=datetime.utcnow().isoformat() + "Z",
            anomaly_type=anomaly_type,
            baseline=baseline,
            current_metric=current_metric,
            deviation_score=deviation_score,
            anomaly_score=anomaly_score,
            severity=severity,
            recommended_action=action,
            evidence_hash=evidence_hash
        )

# ============================================================================
# REQUEST QUARANTINE SERVICE
# ============================================================================

class RequestQuarantineService:
    def __init__(self):
        self.quarantined: Dict[str, QuarantinedRequest] = {}
        self.HOLD_DURATION_MS = 60 * 60 * 1000 # 1 hour
        self.DEFAULT_APPROVERS_REQUIRED = 2

    def quarantine(self, request: Dict[str, Any], anomalies: List[AnomalyDetection], trust_suppression: Optional[Dict[str, Any]] = None) -> QuarantinedRequest:
        reasons = [a.anomaly_type.value for a in anomalies]
        approval_required = any(a.severity in [Severity.HIGH, Severity.CRITICAL] for a in anomalies)
        
        qr = QuarantinedRequest(
            quarantine_id=str(uuid.uuid4()),
            original_request=request,
            original_timestamp=datetime.utcnow().isoformat() + "Z",
            quarantine_reason=f"Anomalies detected: {', '.join(reasons)}",
            anomalies_detected=anomalies,
            trust_suppression_applied=trust_suppression.get("applied", False) if trust_suppression else False,
            suppressed_trust_score=trust_suppression.get("suppressed_score", 0) if trust_suppression else 0,
            approval_required=approval_required,
            approvers_required=self.DEFAULT_APPROVERS_REQUIRED,
            approvals_received=[],
            approval_deadline=(datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
            status=QuarantineStatus.QUARANTINED
        )
        self.quarantined[qr.quarantine_id] = qr
        return qr

    def get_quarantined(self, quarantine_id: str) -> Optional[QuarantinedRequest]:
        return self.quarantined.get(quarantine_id)

# ============================================================================
# APPROVAL QUORUM SERVICE
# ============================================================================

class ApprovalQuorumService:
    def __init__(self):
        self.quorums: Dict[str, ApprovalQuorum] = {}
        self.DEFAULT_QUORUM_SIZE = 2
        self.TRUST_THRESHOLD = 80

    def create_quorum(self, quarantine_id: str, required_approvers: List[str], required_count: int = 2, escalation_path: List[str] = None) -> ApprovalQuorum:
        quorum = ApprovalQuorum(
            approval_id=str(uuid.uuid4()),
            quarantine_id=quarantine_id,
            required_approvers=required_approvers,
            current_approvals={},
            required_count=required_count,
            threshold_reached=False,
            approval_deadline=(datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
            escalation_path=escalation_path or [],
            escalation_triggered=False
        )
        self.quorums[quorum.approval_id] = quorum
        return quorum
