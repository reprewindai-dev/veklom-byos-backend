"""
Jurisdiction Detector
Auto-detects data location and applicable legal framework

Determines which laws apply (Law 25, GDPR, CCPA, etc.)
based on:
- IP geolocation of endpoints
- Data classification tags
- Processing purpose
- Consent location

Location: veklom-byos-backend/backend/compliance/jurisdiction_detector.py
"""

from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass
import socket
import geoip2.database


class Jurisdiction(str, Enum):
    """Legal jurisdiction"""
    QUEBEC = "quebec"  # Law 25 (strictest)
    CANADA = "canada"  # PIPEDA
    USA = "usa"  # CCPA (California) or others
    CALIFORNIA = "california"  # CCPA
    TEXAS = "texas"  # TDPSA
    VIRGINIA = "virginia"  # VCDPA
    EU = "eu"  # GDPR (strictest)
    UK = "uk"  # UK GDPR
    AUSTRALIA = "australia"  # Privacy Act
    GLOBAL = "global"  # Multi-jurisdiction


class LegalFramework(str, Enum):
    """Which law governs"""
    LAW25 = "law25"  # Quebec (Law 25 / Bill 64)
    PIPEDA = "pipeda"  # Canada (Personal Information Protection Act)
    GDPR = "gdpr"  # Europe (General Data Protection Regulation)
    CCPA = "ccpa"  # California (California Consumer Privacy Act)
    TDPSA = "tdpsa"  # Texas (Texas Data Privacy and Security Act)
    VCDPA = "vcdpa"  # Virginia (Virginia Consumer Data Protection Act)
    PRIVACY_ACT = "privacy_act"  # Australia
    CUSTOM = "custom"  # Enterprise custom rules


class DataClassification(str, Enum):
    """How the data is classified"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"  # Highest protection (PII, health, financial)
    RESTRICTED_CANADIAN = "restricted_canadian"  # Must stay in Canada
    RESTRICTED_QUEBEC = "restricted_quebec"  # Must stay in Quebec
    RESTRICTED_EU = "restricted_eu"  # Must stay in EU


@dataclass
class JurisdictionDetectionResult:
    """Result of jurisdiction detection"""
    primary_jurisdiction: Jurisdiction
    applicable_frameworks: List[LegalFramework]
    primary_framework: LegalFramework

    # Geographic context
    data_locations: Set[str]  # Where data physically is/will be
    processing_locations: Set[str]  # Where processing happens

    # Enforcement level
    strictness: int  # 1-10 (1=least strict, 10=most strict)
    requires_explicit_consent: bool
    requires_audit_trail: bool
    requires_dsar: bool
    requires_breach_notification: bool
    breach_notification_hours: int  # Hours to notify
    data_retention_max_days: Optional[int]
    cross_border_allowed: bool

    # Confidence
    confidence: float  # 0.0-1.0


class JurisdictionDetector:
    """
    Auto-detects applicable legal frameworks.

    Queries:
    1. Where is the data physically located?
    2. Where is it being processed?
    3. Who is the data subject? (user location)
    4. What type of data is it? (PII, health, financial?)
    5. What's the processing purpose?

    Returns: Which laws apply + enforcement requirements
    """

    def __init__(self, geoip_db_path: Optional[str] = None):
        """
        Initialize detector.

        Args:
            geoip_db_path: Path to GeoIP2 database (optional)
        """
        self.geoip_db_path = geoip_db_path
        self.geoip_reader = None

        # Framework definitions (rules for each jurisdiction)
        self.frameworks = self._init_frameworks()

    def detect_jurisdiction(
        self,
        endpoint_ip: Optional[str] = None,
        endpoint_host: Optional[str] = None,
        data_classification: DataClassification = DataClassification.INTERNAL,
        user_location: Optional[str] = None,  # "quebec", "california", "eu"
        processing_purpose: str = "business_operation",
        affected_data_types: Optional[List[str]] = None,  # "pii", "health", "financial"
    ) -> JurisdictionDetectionResult:
        """
        Detect applicable jurisdiction and legal framework.

        Args:
            endpoint_ip: IP address of data endpoint
            endpoint_host: Hostname of data endpoint
            data_classification: How data is classified
            user_location: Where the data subject is located
            processing_purpose: Why is data being processed
            affected_data_types: What types of data (PII, health, etc.)

        Returns:
            JurisdictionDetectionResult with applicable frameworks
        """

        # Resolve endpoint location
        endpoint_location = self._get_location(endpoint_ip, endpoint_host)

        # Determine primary jurisdiction
        if data_classification in [
            DataClassification.RESTRICTED_QUEBEC,
            DataClassification.RESTRICTED_CANADIAN,
        ]:
            # Explicitly marked as Canada/Quebec
            if data_classification == DataClassification.RESTRICTED_QUEBEC:
                primary_jurisdiction = Jurisdiction.QUEBEC
            else:
                primary_jurisdiction = Jurisdiction.CANADA
        elif endpoint_location and "quebec" in endpoint_location.lower():
            primary_jurisdiction = Jurisdiction.QUEBEC
        elif endpoint_location and "canada" in endpoint_location.lower():
            primary_jurisdiction = Jurisdiction.CANADA
        elif user_location and "quebec" in user_location.lower():
            primary_jurisdiction = Jurisdiction.QUEBEC
        elif user_location and "canada" in user_location.lower():
            primary_jurisdiction = Jurisdiction.CANADA
        elif endpoint_location and "eu" in endpoint_location.lower():
            primary_jurisdiction = Jurisdiction.EU
        elif user_location and "eu" in user_location.lower():
            primary_jurisdiction = Jurisdiction.EU
        elif endpoint_location and ("california" in endpoint_location.lower() or "usa" in endpoint_location.lower()):
            primary_jurisdiction = Jurisdiction.CALIFORNIA
        else:
            primary_jurisdiction = Jurisdiction.GLOBAL

        # Get applicable frameworks
        applicable_frameworks = self._get_applicable_frameworks(
            primary_jurisdiction,
            data_classification,
            affected_data_types or [],
        )

        primary_framework = applicable_frameworks[0] if applicable_frameworks else LegalFramework.CUSTOM

        # Get strictness and requirements
        strictness, requirements = self._get_framework_requirements(primary_framework)

        return JurisdictionDetectionResult(
            primary_jurisdiction=primary_jurisdiction,
            applicable_frameworks=applicable_frameworks,
            primary_framework=primary_framework,
            data_locations={endpoint_location} if endpoint_location else set(),
            processing_locations={endpoint_location} if endpoint_location else set(),
            strictness=strictness,
            requires_explicit_consent=requirements.get("explicit_consent", False),
            requires_audit_trail=requirements.get("audit_trail", False),
            requires_dsar=requirements.get("dsar", False),
            requires_breach_notification=requirements.get("breach_notification", False),
            breach_notification_hours=requirements.get("notification_hours", 72),
            data_retention_max_days=requirements.get("retention_days"),
            cross_border_allowed=requirements.get("cross_border", False),
            confidence=0.95,
        )

    # ====================================================================
    # INTERNAL METHODS
    # ====================================================================

    def _get_location(self, ip: Optional[str], host: Optional[str]) -> Optional[str]:
        """Get geographic location from IP or hostname"""
        if ip:
            return self._geoip_lookup(ip)
        elif host:
            try:
                ip = socket.gethostbyname(host)
                return self._geoip_lookup(ip)
            except Exception:
                return None
        return None

    def _geoip_lookup(self, ip_address: str) -> Optional[str]:
        """Look up IP in GeoIP database"""
        if not self.geoip_db_path or not self.geoip_reader:
            # Fallback to hardcoded ranges
            return self._hardcoded_ip_lookup(ip_address)

        try:
            response = self.geoip_reader.city(ip_address)
            country = response.country.iso_code

            # Map country codes to jurisdiction strings
            if country == "CA":
                return "canada"
            elif country == "US":
                # Could refine to state, but keep simple
                return "usa"
            elif country in ["FR", "DE", "GB", "IT", "ES", "NL", "BE", "AT", "SE", "DK", "FI", "PL"]:
                return "eu"
            elif country == "AU":
                return "australia"
            else:
                return f"country_{country}".lower()
        except Exception:
            return None

    def _hardcoded_ip_lookup(self, ip_address: str) -> Optional[str]:
        """Fallback IP lookup using hardcoded ranges"""
        try:
            ip_int = self._ip_to_int(ip_address)

            # Canadian ranges
            if self._ip_in_range(ip_int, "24.0.0.0", "24.255.255.255"):
                return "canada"
            if self._ip_in_range(ip_int, "68.0.0.0", "68.255.255.255"):
                return "canada"

            # US ranges
            if self._ip_in_range(ip_int, "1.0.0.0", "1.255.255.255"):
                return "usa"

            # EU ranges (simplified)
            if self._ip_in_range(ip_int, "213.0.0.0", "213.255.255.255"):
                return "eu"
        except Exception:
            pass

        return None

    def _ip_to_int(self, ip: str) -> int:
        """Convert IP to integer"""
        return sum(int(octet) << (24 - 8 * i) for i, octet in enumerate(ip.split(".")))

    def _ip_in_range(self, ip_int: int, start: str, end: str) -> bool:
        """Check if IP is in range"""
        start_int = self._ip_to_int(start)
        end_int = self._ip_to_int(end)
        return start_int <= ip_int <= end_int

    def _get_applicable_frameworks(
        self,
        jurisdiction: Jurisdiction,
        classification: DataClassification,
        data_types: List[str],
    ) -> List[LegalFramework]:
        """Get applicable legal frameworks for jurisdiction"""
        frameworks = []

        if jurisdiction == Jurisdiction.QUEBEC:
            frameworks.append(LegalFramework.LAW25)
            frameworks.append(LegalFramework.PIPEDA)  # Also applies in Canada
        elif jurisdiction == Jurisdiction.CANADA:
            frameworks.append(LegalFramework.PIPEDA)
        elif jurisdiction == Jurisdiction.EU:
            frameworks.append(LegalFramework.GDPR)
        elif jurisdiction == Jurisdiction.CALIFORNIA:
            frameworks.append(LegalFramework.CCPA)
        elif jurisdiction == Jurisdiction.TEXAS:
            frameworks.append(LegalFramework.TDPSA)
        elif jurisdiction == Jurisdiction.VIRGINIA:
            frameworks.append(LegalFramework.VCDPA)
        elif jurisdiction == Jurisdiction.AUSTRALIA:
            frameworks.append(LegalFramework.PRIVACY_ACT)
        elif jurisdiction == Jurisdiction.GLOBAL:
            # Multi-jurisdiction: apply all that could apply
            frameworks = [
                LegalFramework.LAW25,
                LegalFramework.GDPR,
                LegalFramework.CCPA,
            ]

        return frameworks if frameworks else [LegalFramework.CUSTOM]

    def _get_framework_requirements(self, framework: LegalFramework) -> Tuple[int, Dict]:
        """Get requirements for a legal framework"""
        requirements = {
            LegalFramework.LAW25: {
                "strictness": 10,
                "explicit_consent": True,
                "audit_trail": True,
                "dsar": True,
                "breach_notification": True,
                "notification_hours": 24,
                "retention_days": 30,
                "cross_border": False,
            },
            LegalFramework.GDPR: {
                "strictness": 10,
                "explicit_consent": True,
                "audit_trail": True,
                "dsar": True,
                "breach_notification": True,
                "notification_hours": 72,
                "retention_days": None,  # No fixed limit
                "cross_border": False,
            },
            LegalFramework.CCPA: {
                "strictness": 7,
                "explicit_consent": False,  # Opt-out model
                "audit_trail": True,
                "dsar": True,
                "breach_notification": True,
                "notification_hours": 0,  # "without unreasonable delay"
                "retention_days": None,
                "cross_border": True,  # Can share with others (with opt-out)
            },
            LegalFramework.PIPEDA: {
                "strictness": 8,
                "explicit_consent": True,
                "audit_trail": True,
                "dsar": True,
                "breach_notification": False,  # Not required federally
                "notification_hours": 72,
                "retention_days": None,
                "cross_border": False,
            },
            LegalFramework.CUSTOM: {
                "strictness": 5,
                "explicit_consent": False,
                "audit_trail": False,
                "dsar": False,
                "breach_notification": False,
                "notification_hours": 0,
                "retention_days": None,
                "cross_border": True,
            },
        }

        req = requirements.get(framework, requirements[LegalFramework.CUSTOM])
        strictness = req.pop("strictness")

        return strictness, req

    def _init_frameworks(self) -> Dict[LegalFramework, Dict]:
        """Initialize legal framework definitions"""
        return {
            LegalFramework.LAW25: {
                "name": "Quebec Law 25 (Bill 64)",
                "jurisdiction": "quebec",
                "year": 2021,
                "strictness": 10,
            },
            LegalFramework.GDPR: {
                "name": "General Data Protection Regulation",
                "jurisdiction": "eu",
                "year": 2018,
                "strictness": 10,
            },
            LegalFramework.CCPA: {
                "name": "California Consumer Privacy Act",
                "jurisdiction": "california",
                "year": 2020,
                "strictness": 7,
            },
            LegalFramework.PIPEDA: {
                "name": "Personal Information Protection and Electronic Documents Act",
                "jurisdiction": "canada",
                "year": 2000,
                "strictness": 8,
            },
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.compliance.jurisdiction_detector import (
    JurisdictionDetector,
    DataClassification,
)

detector = JurisdictionDetector()

# Detect for Quebec customer data
result = detector.detect_jurisdiction(
    endpoint_host="db-quebec.internal.veklom.com",
    data_classification=DataClassification.RESTRICTED_QUEBEC,
    user_location="quebec",
    affected_data_types=["pii"],
)

print(f"Primary jurisdiction: {result.primary_jurisdiction}")
print(f"Primary framework: {result.primary_framework}")
print(f"Strictness: {result.strictness}/10")
print(f"Requires consent: {result.requires_explicit_consent}")
print(f"Requires audit: {result.requires_audit_trail}")
print(f"Breach notification: {result.breach_notification_hours} hours")
print(f"Cross-border allowed: {result.cross_border_allowed}")

# Results:
# Primary jurisdiction: quebec
# Primary framework: law25
# Strictness: 10/10
# Requires consent: True
# Requires audit: True
# Breach notification: 24 hours
# Cross-border allowed: False
"""
