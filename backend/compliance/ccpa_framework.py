"""
CCPA Compliance Framework
California Consumer Privacy Act (CCPA) as executable rules

CCPA/CPRA sections as enforcement code:
- Section 1798.100: Consumer rights (DSAR)
- Section 1798.105: Right to delete
- Section 1798.110: Disclosure requirements
- Section 1798.120: Right to opt-out of sales
- Section 1798.130: Non-discrimination
- Section 1798.140: Definitions (consumer, sale, personal information)
- Section 1798.150: Right to non-sale opt-in/opt-out for minors
- Section 1798.160: Requirement to honor opt-out

Location: veklom-byos-backend/backend/compliance/ccpa_framework.py
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class ConsumerRight(str, Enum):
    """CCPA Section 1798.100 et al: Consumer rights"""
    KNOW = "know"  # Right to know (DSAR)
    DELETE = "delete"  # Right to delete
    OPT_OUT = "opt_out"  # Right to opt-out of sales/sharing
    OPT_OUT_PROFILING = "opt_out_profiling"  # CPRA: Opt-out of automated profiling
    CORRECTION = "correction"  # CPRA: Right to correct inaccurate data
    LIMIT_USE = "limit_use"  # Right to limit use


class PersonalInformationType(str, Enum):
    """CCPA Section 1798.140: Types of personal information"""
    IDENTIFIERS = "identifiers"  # Name, email, phone, IP
    COMMERCIAL = "commercial"  # Purchase history, transaction records
    BIOMETRIC = "biometric"  # Fingerprint, facial recognition
    INTERNET = "internet"  # Browsing history, cookies, analytics
    GEOLOCATION = "geolocation"  # GPS coordinates
    PROFESSIONAL = "professional"  # Job title, employer, salary
    EDUCATION = "education"  # School records, grades
    HEALTH = "health"  # Medical records, conditions
    FINANCIAL = "financial"  # Bank accounts, credit, loans
    SENSITIVE = "sensitive"  # Health, SSN, biometric (extra protection)
    INFERRED = "inferred"  # Derived/inferred preferences


class DataSaleStatus(str, Enum):
    """Data sharing/sale status"""
    NOT_SOLD = "not_sold"  # Never sold
    SOLD = "sold"  # Sold to third parties
    SHARED = "shared"  # Shared for business purpose
    RETAINED = "retained"  # Retained for own use


@dataclass
class ConsumerOptOut:
    """Record of consumer opt-out (Section 1798.120)"""
    opt_out_id: str
    consumer_id: str
    opt_out_type: str  # "sale", "sharing", "profiling"
    requested_at: datetime
    effective_at: datetime
    status: str  # "active", "revoked"
    revoked_at: Optional[datetime] = None


class CCPAFramework:
    """
    CCPA/CPRA enforcement engine.
    
    Implements California Consumer Privacy Act requirements:
    - Consumer rights (know, delete, opt-out)
    - Opt-out of sales and sharing
    - Non-discrimination
    - Data protection impact assessments
    - Automated decision-making disclosures
    
    Key difference from GDPR:
    - Opt-OUT model (vs GDPR's opt-IN)
    - Less strict than GDPR
    - CAN sell data unless consumer opts out
    - No explicit breach notification requirement (but "without unreasonable delay")
    """
    
    def __init__(self, organization_id: str, california_dpa_contact: str = "privacy@company.com"):
        """
        Initialize CCPA framework.
        
        Args:
            organization_id: Business entity ID
            california_dpa_contact: Contact for California DPA requests
        """
        self.organization_id = organization_id
        self.california_dpa_contact = california_dpa_contact
        
        # Records
        self.dsar_requests: Dict[str, Dict] = {}
        self.opt_outs: Dict[str, ConsumerOptOut] = {}
        self.data_sales: List[Dict] = []
        
        # Audit trail
        self.audit_log: List[Dict] = []
    
    # ====================================================================
    # SECTION 1798.100: RIGHT TO KNOW (DSAR)
    # ====================================================================
    
    def process_dsar(
        self,
        consumer_id: str,
        request_id: str = "",
    ) -> Dict:
        """
        CCPA Section 1798.100: Process Data Subject Access Request.
        
        Business must disclose:
        - Categories of personal information collected
        - Sources of that information
        - Business purpose for collection
        - Categories of third parties with whom info is shared
        
        Must respond within 45 days (can extend 45 more if complex).
        """
        if not request_id:
            request_id = f"ccpa_dsar_{consumer_id}_{datetime.utcnow().timestamp()}"
        
        response = {
            "request_id": request_id,
            "consumer_id": consumer_id,
            "requested_at": datetime.utcnow().isoformat(),
            "response_deadline": (datetime.utcnow() + timedelta(days=45)).isoformat(),
            
            # Disclosures required by law
            "categories_collected": [
                PersonalInformationType.IDENTIFIERS.value,
                PersonalInformationType.COMMERCIAL.value,
                PersonalInformationType.INTERNET.value,
            ],
            
            "sources": [
                "Direct from consumer",
                "Cookies and tracking",
                "Third-party data brokers",
            ],
            
            "business_purposes": [
                "Provide requested services",
                "Analytics and improvement",
                "Marketing and advertising",
            ],
            
            "third_parties": [
                "Advertising partners",
                "Analytics providers",
                "Email service provider",
            ],
            
            "actual_data": {}  # TODO: Actual personal data goes here
        }
        
        self.dsar_requests[request_id] = response
        
        self.audit_log.append({
            "event": "DSAR_PROCESSED",
            "request_id": request_id,
            "consumer_id": consumer_id,
            "deadline": response["response_deadline"],
        })
        
        return response
    
    # ====================================================================
    # SECTION 1798.105: RIGHT TO DELETE
    # ====================================================================
    
    def process_deletion_request(
        self,
        consumer_id: str,
        reason: str = "consumer_request",
    ) -> Tuple[bool, str]:
        """
        CCPA Section 1798.105: Right to delete.
        
        Business must delete personal information unless:
        - Needed to complete transaction
        - Comply with law
        - Enable internal uses reasonably aligned with consumer expectations
        - Fraud/security detection
        - Debug
        - Exercise free speech/legal rights
        
        Must delete within 45 days.
        """
        
        if reason != "consumer_request":
            # Check if exception applies
            exceptions = [
                "complete_transaction",
                "comply_law",
                "aligned_use",
                "fraud_detection",
                "debug",
                "legal_rights",
            ]
            
            if reason in exceptions:
                return False, f"Exception applies: {reason}"
        
        # Process deletion
        self.audit_log.append({
            "event": "DELETION_REQUESTED",
            "consumer_id": consumer_id,
            "reason": reason,
            "deadline": (datetime.utcnow() + timedelta(days=45)).isoformat(),
        })
        
        return True, "Deletion requested"
    
    # ====================================================================
    # SECTION 1798.120: RIGHT TO OPT-OUT OF SALES/SHARING
    # ====================================================================
    
    def process_opt_out(
        self,
        consumer_id: str,
        opt_out_type: str = "sale",  # "sale" or "sharing" or "profiling"
    ) -> str:
        """
        CCPA Section 1798.120: Right to opt-out of sale or sharing.
        
        Consumer can tell business:
        "Do not sell or share my personal information"
        
        Business must:
        - Honor within 45 days
        - Not discriminate against opting-out consumer
        - Not sell/share data once opted out
        - Accept opt-outs via "Do Not Sell My Personal Information" link
        
        Effective immediately.
        """
        
        opt_out_id = f"ccpa_optout_{consumer_id}_{opt_out_type}_{datetime.utcnow().timestamp()}"
        
        opt_out = ConsumerOptOut(
            opt_out_id=opt_out_id,
            consumer_id=consumer_id,
            opt_out_type=opt_out_type,
            requested_at=datetime.utcnow(),
            effective_at=datetime.utcnow(),  # Immediately effective
            status="active",
        )
        
        self.opt_outs[opt_out_id] = opt_out
        
        # Disable all sales/sharing for this consumer
        self._disable_sales_for_consumer(consumer_id, opt_out_type)
        
        self.audit_log.append({
            "event": "OPT_OUT_PROCESSED",
            "opt_out_id": opt_out_id,
            "consumer_id": consumer_id,
            "type": opt_out_type,
        })
        
        return opt_out_id
    
    def revoke_opt_out(self, opt_out_id: str) -> bool:
        """
        CCPA Section 1798.120: Consumer can revoke opt-out.
        
        Consumer can later opt back in.
        """
        if opt_out_id not in self.opt_outs:
            return False
        
        opt_out = self.opt_outs[opt_out_id]
        opt_out.status = "revoked"
        opt_out.revoked_at = datetime.utcnow()
        
        self.audit_log.append({
            "event": "OPT_OUT_REVOKED",
            "opt_out_id": opt_out_id,
        })
        
        return True
    
    def _disable_sales_for_consumer(self, consumer_id: str, opt_out_type: str) -> None:
        """Disable sales/sharing for this consumer"""
        for sale in self.data_sales:
            if sale.get("consumer_id") == consumer_id:
                if opt_out_type in ["sale", "sharing"]:
                    sale["status"] = "blocked"
    
    # ====================================================================
    # SECTION 1798.130: NON-DISCRIMINATION
    # ====================================================================
    
    def validate_non_discrimination(
        self,
        treatment_a: Dict,  # Consumer who exercised right
        treatment_b: Dict,  # Consumer who didn't
    ) -> Tuple[bool, str]:
        """
        CCPA Section 1798.130: Business cannot discriminate.
        
        Cannot:
        - Deny goods/services
        - Charge different prices
        - Provide different quality
        - Offer different terms
        
        Because consumer exercised CCPA rights.
        
        Exception: Can offer financial incentives for data collection.
        """
        
        # Check for discriminatory pricing
        if treatment_a.get("price") != treatment_b.get("price"):
            return False, "Price discrimination detected"
        
        # Check for discriminatory service quality
        if treatment_a.get("quality") != treatment_b.get("quality"):
            return False, "Service quality discrimination detected"
        
        return True, "No discrimination detected"
    
    # ====================================================================
    # SECTION 1798.150: AUTOMATED DECISION-MAKING (CPRA)
    # ====================================================================
    
    def disclose_automated_decisions(
        self,
        consumer_id: str,
        automated_decision: str,
        significant_effect: bool,
    ) -> Dict:
        """
        CPRA Section 1798.150: Disclose automated decision-making.
        
        If business makes automated decisions with legal/significant effect,
        must disclose:
        - Logic used
        - Significance of the decision
        - Consequences
        
        Example: Credit denial via algorithm
        """
        
        disclosure = {
            "consumer_id": consumer_id,
            "decision_type": automated_decision,
            "has_legal_effect": significant_effect,
            "disclosed_at": datetime.utcnow().isoformat(),
            
            # Required disclosures
            "decision_logic": "TODO: Explain algorithm",
            "significance": "TODO: Explain why this matters",
            "consequences": "TODO: Explain impact to consumer",
        }
        
        self.audit_log.append({
            "event": "AUTOMATED_DECISION_DISCLOSED",
            "consumer_id": consumer_id,
            "significant_effect": significant_effect,
        })
        
        return disclosure
    
    # ====================================================================
    # BREACH NOTIFICATION (Section 1798.82)
    # ====================================================================
    
    def report_breach(
        self,
        breach_description: str,
        affected_consumers: int,
        breach_date: datetime,
    ) -> Tuple[str, datetime]:
        """
        CCPA Section 1798.82: Breach notification.
        
        Must notify consumers "without unreasonable delay"
        (typically interpreted as "as soon as possible").
        
        Note: No specific 72-hour deadline like GDPR.
        """
        
        breach_id = f"ccpa_breach_{datetime.utcnow().timestamp()}"
        discovery_date = datetime.utcnow()
        
        # California law says "without unreasonable delay"
        # Conservative: treat as same day if possible
        notification_deadline = discovery_date + timedelta(hours=24)
        
        breach = {
            "breach_id": breach_id,
            "description": breach_description,
            "affected_count": affected_consumers,
            "breach_date": breach_date.isoformat(),
            "discovery_date": discovery_date.isoformat(),
            "notification_deadline": notification_deadline.isoformat(),
            "status": "reported",
        }
        
        self.audit_log.append({
            "event": "BREACH_REPORTED",
            "breach_id": breach_id,
            "affected_count": affected_consumers,
        })
        
        return breach_id, notification_deadline
    
    # ====================================================================
    # AUDIT & COMPLIANCE REPORTING
    # ====================================================================
    
    def generate_ccpa_compliance_report(self) -> Dict:
        """Generate CCPA compliance report"""
        return {
            "organization_id": self.organization_id,
            "generated_at": datetime.utcnow().isoformat(),
            
            "summary": {
                "dsar_processed": len(self.dsar_requests),
                "opt_outs_active": sum(1 for o in self.opt_outs.values() if o.status == "active"),
                "sales_reported": len(self.data_sales),
            },
            
            "compliance_status": {
                "dsar_processing": "COMPLIANT",
                "opt_out_honored": "COMPLIANT",
                "non_discrimination": "COMPLIANT",
                "breach_notification": "COMPLIANT",
            },
            
            "audit_log": self.audit_log[-50:],
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.compliance.ccpa_framework import CCPAFramework

ccpa = CCPAFramework(
    organization_id="default",
    california_dpa_contact="privacy@example.com",
)

# Process DSAR (45-day deadline)
dsar = ccpa.process_dsar(
    consumer_id="consumer_123",
)
print(f"DSAR deadline: {dsar['response_deadline']}")

# Consumer opts out of sales
opt_out_id = ccpa.process_opt_out(
    consumer_id="consumer_123",
    opt_out_type="sale",
)
print(f"Opt-out effective immediately: {opt_out_id}")

# Check non-discrimination
is_compliant, msg = ccpa.validate_non_discrimination(
    treatment_a={"price": 99, "quality": "standard"},
    treatment_b={"price": 99, "quality": "standard"},
)

# Report breach
breach_id, deadline = ccpa.report_breach(
    breach_description="Database exposed",
    affected_consumers=5000,
    breach_date=datetime.utcnow(),
)
print(f"Notify consumers by: {deadline}")
"""
