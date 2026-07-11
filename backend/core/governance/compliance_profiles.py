from enum import Enum
from dataclasses import dataclass
from typing import List

class ComplianceRegion(Enum):
    GLOBAL = "GLOBAL"
    ONTARIO = "ONTARIO"
    EU = "EU"
    US = "US"

@dataclass(frozen=True)
class ComplianceProfile:
    id: str
    region: ComplianceRegion
    requires_explicit_evidence_logging: bool
    requires_data_residency: bool
    strict_retention_days: int
    allowed_model_regions: List[str]
    description: str

# Default Global Profile - Used when no specific jurisdiction is enforced
GLOBAL_DEFAULT = ComplianceProfile(
    id="global_default",
    region=ComplianceRegion.GLOBAL,
    requires_explicit_evidence_logging=True,
    requires_data_residency=False,
    strict_retention_days=365,
    allowed_model_regions=["US", "EU", "CA"],
    description="Global baseline with standard privacy-by-design and evidence hashing."
)

# Strict Ontario Public Sector Profile (e.g. Quinte West, EOITC, MFIPPA)
ONTARIO_PUBLIC_SECTOR = ComplianceProfile(
    id="ontario_public",
    region=ComplianceRegion.ONTARIO,
    requires_explicit_evidence_logging=True,
    requires_data_residency=True,
    strict_retention_days=730,  # 2 years typically for municipal retention
    allowed_model_regions=["CA"], # Strict residency
    description="Ontario public sector profile enforcing MFIPPA compliance and strict Canadian data residency."
)

# EU GDPR Profile
EU_GDPR_STRICT = ComplianceProfile(
    id="eu_gdpr",
    region=ComplianceRegion.EU,
    requires_explicit_evidence_logging=True,
    requires_data_residency=True,
    strict_retention_days=30, # Shorter default retention, strict right to be forgotten
    allowed_model_regions=["EU"],
    description="EU profile strictly enforcing GDPR data residency and minimization."
)

# US Healthcare / Regulated Profile
US_HIPAA = ComplianceProfile(
    id="us_hipaa",
    region=ComplianceRegion.US,
    requires_explicit_evidence_logging=True,
    requires_data_residency=True,
    strict_retention_days=2190, # 6 years typical for HIPAA
    allowed_model_regions=["US"],
    description="US regulated profile with strict auditing and BAA compliance."
)

# Fail-Closed Profile (Used when configuration is missing or invalid)
FAIL_CLOSED = ComplianceProfile(
    id="fail_closed",
    region=ComplianceRegion.GLOBAL,
    requires_explicit_evidence_logging=True,
    requires_data_residency=True,
    strict_retention_days=0, # Retain nothing
    allowed_model_regions=[], # Allow nothing
    description="Failsafe profile that blocks all execution due to missing or invalid compliance configuration."
)

def get_compliance_profile(profile_id: str) -> ComplianceProfile:
    profiles = {
        "global_default": GLOBAL_DEFAULT,
        "ontario_public": ONTARIO_PUBLIC_SECTOR,
        "eu_gdpr": EU_GDPR_STRICT,
        "us_hipaa": US_HIPAA
    }
    # If the requested profile is unknown, fail completely closed.
    return profiles.get(profile_id.lower(), FAIL_CLOSED)
