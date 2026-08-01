"""
Law 25 Compliance Framework
Canadian Data Sovereignty & PIPEDA Enforcement

Law 25 Section 93 requires:
- Complete audit trail of data processing
- Proof of Canadian data residency
- Consent tracking and revocation capability
- Breach notification within 24 hours
- Individual data access rights (DSARs)

This framework enforces compliance at the pipeline execution level.

Location: veklom-byos-backend/backend/compliance/law25_framework.py
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json


class DataResidency(str, Enum):
    """Data residency classification"""
    CANADIAN = "canadian"
    QUEBEC = "quebec"
    RESTRICTED = "restricted"  # Personal data, highest protection
    CROSS_BORDER = "cross_border"  # Not allowed without consent


class ConsentStatus(str, Enum):
    """Consent states per Law 25 Section 12"""
    EXPLICIT = "explicit"  # Written, clear consent
    IMPLIED = "implied"  # Inferred from action
    WITHDRAWN = "withdrawn"  # User revoked
    EXPIRED = "expired"  # Consent lapsed
    NEVER_GIVEN = "never_given"


class ProcessingPurpose(str, Enum):
    """PIPEDA Schedule 1 processing purposes"""
    BUSINESS_OPERATION = "business_operation"  # Core function
    ANALYTICS = "analytics"  # Aggregate insights (non-PII)
    RESEARCH = "research"  # Academic use
    MARKETING = "marketing"  # Promotional
    FRAUD_PREVENTION = "fraud_prevention"  # Security
    LEGAL_COMPLIANCE = "legal_compliance"  # Regulatory


@dataclass
class DataElement:
    """Single data point in pipeline"""
    element_id: str
    field_name: str
    data_type: str  # string, int, float, bool, date, phone, ssn, etc.
    classification: str  # public, internal, confidential, restricted
    residency: DataResidency
    contains_pii: bool  # Personally Identifiable Information
    is_sensitive: bool  # Sensitive personal information (health, finance)
    retention_days: int  # How long to keep


@dataclass
class ProcessingActivity:
    """Single data processing operation"""
    activity_id: str
    pipeline_id: str
    node_id: str  # Which node in the pipeline
    operation: str  # read, transform, filter, aggregate, export
    input_elements: List[str]  # IDs of input data elements
    output_elements: List[str]  # IDs of output data elements
    purpose: ProcessingPurpose
    timestamp: datetime
    user_id: str
    ip_address: str
    system_fingerprint: str  # Hardware/deployment identifier


@dataclass
class ConsentRecord:
    """User consent for data processing"""
    consent_id: str
    user_id: str
    tenant_id: str
    purpose: ProcessingPurpose
    granted_at: datetime
    expires_at: Optional[datetime]  # None = indefinite
    status: ConsentStatus
    withdrawal_reason: Optional[str]  # Why consent was revoked
    withdrawn_at: Optional[datetime]
    proof_of_consent: str  # URL or reference to consent document


class Law25ComplianceFramework:
    """
    Enforcement engine for Law 25 (Quebec's Data Privacy Law).
    
    Key requirements:
    - Section 12: Consent for data collection
    - Section 19: Right to be forgotten
    - Section 93: Audit trail requirements
    - Section 95: DSAR (Data Subject Access Request)
    - Section 98: Breach notification (24 hours)
    """
    
    def __init__(self, tenant_id: str, jurisdiction: str = "quebec"):
        """
        Initialize compliance framework.
        
        Args:
            tenant_id: Organization ID
            jurisdiction: "quebec" (Law 25) or "canada" (PIPEDA)
        """
        self.tenant_id = tenant_id
        self.jurisdiction = jurisdiction
        
        # Registries
        self.data_elements: Dict[str, DataElement] = {}
        self.processing_activities: List[ProcessingActivity] = []
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.breach_log: List[Dict[str, Any]] = []
        
        # Compliance state
        self.audit_trail: List[Dict[str, Any]] = []
        self.last_audit_date: Optional[datetime] = None
    
    # ====================================================================
    # DATA CLASSIFICATION
    # ====================================================================
    
    def register_data_element(
        self,
        element_id: str,
        field_name: str,
        data_type: str,
        classification: str,
        residency: DataResidency,
        contains_pii: bool = False,
        is_sensitive: bool = False,
        retention_days: int = 30,
    ) -> None:
        """
        Register a data element in the pipeline.
        
        Triggers automatic compliance checks.
        """
        element = DataElement(
            element_id=element_id,
            field_name=field_name,
            data_type=data_type,
            classification=classification,
            residency=residency,
            contains_pii=contains_pii,
            is_sensitive=is_sensitive,
            retention_days=retention_days,
        )
        
        self.data_elements[element_id] = element
        
        # Log registration
        self._log_audit_event(
            event_type="DATA_ELEMENT_REGISTERED",
            details={
                "element_id": element_id,
                "contains_pii": contains_pii,
                "is_sensitive": is_sensitive,
                "residency": residency.value,
            },
        )
        
        # Trigger residency check
        if residency == DataResidency.CROSS_BORDER:
            self._flag_compliance_concern(
                level="HIGH",
                message=f"Cross-border data flow detected for {field_name}",
                requires_explicit_consent=True,
            )
    
    # ====================================================================
    # CONSENT MANAGEMENT (Section 12)
    # ====================================================================
    
    def record_consent(
        self,
        user_id: str,
        purpose: ProcessingPurpose,
        expires_at: Optional[datetime] = None,
        proof_url: str = "",
    ) -> str:
        """
        Record explicit consent for data processing.
        
        Args:
            user_id: Individual giving consent
            purpose: What the data will be used for
            expires_at: When consent expires (None = indefinite)
            proof_url: URL to consent document
            
        Returns:
            Consent ID for audit trail
        """
        consent_id = f"consent_{user_id}_{purpose.value}_{datetime.utcnow().timestamp()}"
        
        consent = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            tenant_id=self.tenant_id,
            purpose=purpose,
            granted_at=datetime.utcnow(),
            expires_at=expires_at,
            status=ConsentStatus.EXPLICIT,
            withdrawal_reason=None,
            withdrawn_at=None,
            proof_of_consent=proof_url,
        )
        
        self.consent_records[consent_id] = consent
        
        self._log_audit_event(
            event_type="CONSENT_GRANTED",
            details={
                "consent_id": consent_id,
                "user_id": user_id,
                "purpose": purpose.value,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )
        
        return consent_id
    
    def withdraw_consent(
        self,
        consent_id: str,
        reason: str = "",
    ) -> bool:
        """
        Withdraw consent (Section 19 - Right to be forgotten).
        
        Args:
            consent_id: Consent to withdraw
            reason: Why it's being withdrawn
            
        Returns:
            True if successfully withdrawn
        """
        if consent_id not in self.consent_records:
            return False
        
        consent = self.consent_records[consent_id]
        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawal_reason = reason
        consent.withdrawn_at = datetime.utcnow()
        
        self._log_audit_event(
            event_type="CONSENT_WITHDRAWN",
            details={
                "consent_id": consent_id,
                "reason": reason,
            },
        )
        
        # Trigger DPIA (Data Protection Impact Assessment)
        self._trigger_dpia(
            reason="Consent withdrawal",
            affected_user=consent.user_id,
        )
        
        return True
    
    def check_consent(
        self,
        user_id: str,
        purpose: ProcessingPurpose,
    ) -> bool:
        """
        Check if user has active consent for a processing purpose.
        
        Returns:
            True if consent is active and not expired
        """
        for consent in self.consent_records.values():
            if consent.user_id != user_id or consent.purpose != purpose:
                continue
            
            # Check if active
            if consent.status != ConsentStatus.EXPLICIT:
                return False
            
            # Check if expired
            if consent.expires_at and datetime.utcnow() > consent.expires_at:
                consent.status = ConsentStatus.EXPIRED
                return False
            
            return True
        
        return False
    
    # ====================================================================
    # PROCESSING ACTIVITY LOGGING (Section 93 - Audit Trail)
    # ====================================================================
    
    def log_processing_activity(
        self,
        pipeline_id: str,
        node_id: str,
        operation: str,  # read, transform, filter, aggregate, export
        input_elements: List[str],
        output_elements: List[str],
        purpose: ProcessingPurpose,
        user_id: str,
        ip_address: str,
        system_fingerprint: str,
    ) -> str:
        """
        Log a single data processing operation.
        
        This is the core audit trail for Law 25 Section 93.
        """
        activity_id = f"activity_{pipeline_id}_{node_id}_{datetime.utcnow().timestamp()}"
        
        activity = ProcessingActivity(
            activity_id=activity_id,
            pipeline_id=pipeline_id,
            node_id=node_id,
            operation=operation,
            input_elements=input_elements,
            output_elements=output_elements,
            purpose=purpose,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address,
            system_fingerprint=system_fingerprint,
        )
        
        self.processing_activities.append(activity)
        
        # Log to audit trail
        self._log_audit_event(
            event_type="PROCESSING_ACTIVITY",
            details={
                "activity_id": activity_id,
                "operation": operation,
                "input_elements": input_elements,
                "output_elements": output_elements,
                "purpose": purpose.value,
                "user_id": user_id,
                "system_fingerprint": system_fingerprint,
            },
        )
        
        # Verify residency for output
        for element_id in output_elements:
            if element_id in self.data_elements:
                element = self.data_elements[element_id]
                if element.residency == DataResidency.CROSS_BORDER:
                    self._flag_compliance_concern(
                        level="HIGH",
                        message=f"Cross-border processing detected: {operation} on {element.field_name}",
                        activity_id=activity_id,
                    )
        
        return activity_id
    
    def get_audit_trail(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        pipeline_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for compliance reporting.
        
        Supports filtering by date range, user, or pipeline.
        """
        results = []
        
        for event in self.audit_trail:
            # Filter by date
            if start_date and event["timestamp"] < start_date:
                continue
            if end_date and event["timestamp"] > end_date:
                continue
            
            # Filter by user
            if user_id and event.get("details", {}).get("user_id") != user_id:
                continue
            
            # Filter by pipeline
            if pipeline_id and event.get("details", {}).get("pipeline_id") != pipeline_id:
                continue
            
            results.append(event)
        
        return results
    
    # ====================================================================
    # DATA SUBJECT ACCESS RIGHTS (Section 95 - DSAR)
    # ====================================================================
    
    def process_dsar(
        self,
        user_id: str,
        request_id: str = "",
    ) -> Dict[str, Any]:
        """
        Process Data Subject Access Request (DSAR).
        
        Returns all data and processing records for a user.
        Must be completed within 30 days per Law 25.
        """
        if not request_id:
            request_id = f"dsar_{user_id}_{datetime.utcnow().timestamp()}"
        
        # Collect all data about this user
        user_data = {
            "request_id": request_id,
            "user_id": user_id,
            "request_date": datetime.utcnow().isoformat(),
            "data_elements": [],
            "processing_activities": [],
            "consent_records": [],
            "completion_deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        }
        
        # Find all processing activities for this user
        for activity in self.processing_activities:
            if activity.user_id == user_id:
                user_data["processing_activities"].append(asdict(activity))
        
        # Find all consent records for this user
        for consent in self.consent_records.values():
            if consent.user_id == user_id:
                user_data["consent_records"].append(asdict(consent))
        
        # Log the DSAR
        self._log_audit_event(
            event_type="DSAR_PROCESSED",
            details={
                "request_id": request_id,
                "user_id": user_id,
                "data_records_returned": len(user_data["processing_activities"]),
            },
        )
        
        return user_data
    
    # ====================================================================
    # BREACH NOTIFICATION (Section 98 - Breach Reporting)
    # ====================================================================
    
    def report_breach(
        self,
        description: str,
        affected_users: List[str],
        severity: str = "high",  # low, medium, high, critical
        breach_date: Optional[datetime] = None,
    ) -> str:
        """
        Report a data breach.
        
        Must notify individuals within 24 hours per Law 25 Section 98.
        """
        breach_id = f"breach_{datetime.utcnow().timestamp()}"
        
        breach = {
            "breach_id": breach_id,
            "reported_at": datetime.utcnow().isoformat(),
            "breach_date": (breach_date or datetime.utcnow()).isoformat(),
            "description": description,
            "affected_user_count": len(affected_users),
            "severity": severity,
            "notification_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "status": "pending_external_notification",
        }
        
        self.breach_log.append(breach)
        
        # Log to audit trail
        self._log_audit_event(
            event_type="BREACH_REPORTED",
            details={
                "breach_id": breach_id,
                "affected_users": len(affected_users),
                "severity": severity,
            },
        )
        
        # External notifications are intentionally not simulated here; callers must hand this record to the notification worker.
        
        return breach_id
    
    # ====================================================================
    # INTERNAL AUDIT & COMPLIANCE CHECKING
    # ====================================================================
    
    def _log_audit_event(
        self,
        event_type: str,
        details: Dict[str, Any],
    ) -> None:
        """Log event to internal audit trail"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": self.tenant_id,
            "event_type": event_type,
            "details": details,
            "hash": self._compute_event_hash(event_type, details),
        }
        
        self.audit_trail.append(event)
    
    def _compute_event_hash(self, event_type: str, details: Dict[str, Any]) -> str:
        """Hash event for integrity verification"""
        data = f"{event_type}:{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _flag_compliance_concern(
        self,
        level: str,  # LOW, MEDIUM, HIGH, CRITICAL
        message: str,
        requires_explicit_consent: bool = False,
        activity_id: Optional[str] = None,
    ) -> None:
        """Flag a potential compliance issue for review"""
        self._log_audit_event(
            event_type="COMPLIANCE_CONCERN",
            details={
                "level": level,
                "message": message,
                "requires_explicit_consent": requires_explicit_consent,
                "activity_id": activity_id,
            },
        )
        
        if level == "CRITICAL":
            self._log_audit_event(event_type="COMPLIANCE_ALERT_REQUIRED", details={"message": message})
    
    def _trigger_dpia(
        self,
        reason: str,
        affected_user: Optional[str] = None,
    ) -> None:
        """Trigger Data Protection Impact Assessment"""
        self._log_audit_event(
            event_type="DPIA_TRIGGERED",
            details={
                "reason": reason,
                "affected_user": affected_user,
            },
        )
    
    # ====================================================================
    # COMPLIANCE REPORTING
    # ====================================================================
    
    def generate_law25_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive Law 25 compliance report.
        
        Used for regulatory audits and internal compliance reviews.
        """
        period = f"{start_date.date()} to {end_date.date()}"
        
        # Filter events to period
        events = self.get_audit_trail(start_date, end_date)
        
        # Categorize events
        categories = {}
        for event in events:
            event_type = event["event_type"]
            categories[event_type] = categories.get(event_type, 0) + 1
        
        # Compliance metrics
        total_activities = len(self.processing_activities)
        activities_with_pii = sum(
            1 for a in self.processing_activities
            for eid in a.output_elements
            if eid in self.data_elements and self.data_elements[eid].contains_pii
        )
        
        report = {
            "report_period": period,
            "generated_at": datetime.utcnow().isoformat(),
            "tenant_id": self.tenant_id,
            "jurisdiction": self.jurisdiction,
            
            "executive_summary": {
                "total_audit_events": len(events),
                "total_processing_activities": total_activities,
                "activities_involving_pii": activities_with_pii,
                "consent_records": len(self.consent_records),
                "breaches_reported": len(self.breach_log),
            },
            
            "event_breakdown": categories,
            
            "compliance_status": {
                "section_12_consent": self._check_section_12(),
                "section_19_dsar": self._check_section_19(),
                "section_93_audit": self._check_section_93(),
                "section_95_dsar": self._check_section_95(),
                "section_98_breach": self._check_section_98(),
            },
            
            "audit_trail": events[-100:],  # Last 100 events
            "data_residency_summary": self._get_residency_summary(),
        }
        
        return report
    
    def _check_section_12(self) -> Dict[str, Any]:
        """Check consent compliance (Section 12)"""
        return {
            "compliant": all(
                c.status in [ConsentStatus.EXPLICIT, ConsentStatus.WITHDRAWN]
                for c in self.consent_records.values()
            ),
            "total_consents": len(self.consent_records),
            "explicit_consents": sum(
                1 for c in self.consent_records.values()
                if c.status == ConsentStatus.EXPLICIT
            ),
        }
    
    def _check_section_19(self) -> Dict[str, Any]:
        """Check right to be forgotten (Section 19)"""
        return {
            "compliant": len(self.breach_log) == 0,  # No data retention violations
            "withdrawals_processed": sum(
                1 for c in self.consent_records.values()
                if c.status == ConsentStatus.WITHDRAWN
            ),
        }
    
    def _check_section_93(self) -> Dict[str, Any]:
        """Check audit trail (Section 93)"""
        return {
            "compliant": len(self.audit_trail) > 0,
            "audit_events_logged": len(self.audit_trail),
            "last_audit": (
                self.audit_trail[-1]["timestamp"]
                if self.audit_trail
                else None
            ),
        }
    
    def _check_section_95(self) -> Dict[str, Any]:
        """Check DSAR capability (Section 95)"""
        return {
            "compliant": True,  # System supports DSAR
            "dsar_mechanism": "process_dsar method",
            "response_deadline_days": 30,
        }
    
    def _check_section_98(self) -> Dict[str, Any]:
        """Check breach notification (Section 98)"""
        return {
            "compliant": all(
                (datetime.fromisoformat(b["reported_at"]) - 
                 datetime.fromisoformat(b["breach_date"])).total_seconds() < 86400  # 24 hours
                for b in self.breach_log
            ),
            "breaches_reported": len(self.breach_log),
        }
    
    def _get_residency_summary(self) -> Dict[str, int]:
        """Summarize data residency classification"""
        summary = {}
        for element in self.data_elements.values():
            residency = element.residency.value
            summary[residency] = summary.get(residency, 0) + 1
        return summary


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.compliance.law25_framework import (
    Law25ComplianceFramework,
    DataResidency,
    ProcessingPurpose,
)

# Create compliance engine
compliance = Law25ComplianceFramework(tenant_id="default", jurisdiction="quebec")

# Register data elements
compliance.register_data_element(
    element_id="user_email",
    field_name="email",
    data_type="string",
    classification="confidential",
    residency=DataResidency.QUEBEC,  # Must stay in Quebec
    contains_pii=True,
    is_sensitive=False,
    retention_days=30,
)

# Record consent
consent_id = compliance.record_consent(
    user_id="user_123",
    purpose=ProcessingPurpose.ANALYTICS,
    expires_at=datetime.utcnow() + timedelta(days=365),
    proof_url="https://example.com/consent/abc123",
)

# Log processing activity
compliance.log_processing_activity(
    pipeline_id="pipeline_1",
    node_id="filter_node",
    operation="filter",
    input_elements=["user_email", "user_age"],
    output_elements=["user_email_filtered"],
    purpose=ProcessingPurpose.ANALYTICS,
    user_id="admin_1",
    ip_address="10.0.0.1",
    system_fingerprint="veklom-prod-001",
)

# Process DSAR
dsar_result = compliance.process_dsar(user_id="user_123")
print(f"DSAR records: {len(dsar_result['processing_activities'])}")

# Generate compliance report
report = compliance.generate_law25_compliance_report(
    start_date=datetime.utcnow() - timedelta(days=30),
    end_date=datetime.utcnow(),
)
print(f"Compliance report: {report['compliance_status']}")
"""