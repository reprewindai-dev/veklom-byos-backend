import math
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def compute_vnp_score(
    p50_latency_ms: int,
    p99_latency_ms: int,
    availability_percent: float,
    owasp_compliance_flag: bool = True,
    schema_conformity_percent: float = 100.0,
    m2m_economics_score: float = 1.0,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Computes the authoritative VNP Score based on the specified benchmark methodology.
    
    Weights (default):
    - Latency Consistency (30%): Extreme outliers (p99) severely break workflows.
    - Availability & Outliers (25%): Blended APImetrics CASC score.
    - Security Posture (20%): OWASP API Security Top 10 2023 Compliance.
    - M2M Economics (15%): x402 / MPP transparency.
    - Data Integrity (10%): Schema conformity.
    """
    if weights is None:
        weights = {
            "latency": 0.30,
            "availability": 0.25,
            "security": 0.20,
            "m2m": 0.15,
            "integrity": 0.10
        }

    # 1. Latency Consistency (p99 penalty framework)
    # A perfectly consistent API has p50 == p99. We penalize the spread and the absolute p99.
    # Max acceptable p99 before scoring 0 on latency is 2000ms.
    norm_p99 = max(0.0, 100.0 - (p99_latency_ms / 20.0))
    spread_penalty = max(0.0, (p99_latency_ms - p50_latency_ms) / 50.0) 
    latency_score = max(0.0, norm_p99 - spread_penalty)

    # 2. Availability (CASC-style)
    # 99.99% = 100 score, 99.0% = 90 score, etc. Non-linear drop.
    if availability_percent >= 99.99:
        availability_score = 100.0
    elif availability_percent >= 99.0:
        availability_score = 90.0 + (availability_percent - 99.0) * 10.0
    else:
        # Sharp penalty for < 99%
        availability_score = max(0.0, availability_percent - 20.0)

    # 3. Security
    security_score = 100.0 if owasp_compliance_flag else 0.0

    # 4. M2M Economics
    m2m_score = min(100.0, max(0.0, m2m_economics_score * 100.0))

    # 5. Data Integrity
    integrity_score = min(100.0, max(0.0, schema_conformity_percent))

    # Calculate Weighted Composite
    composite = (
        (latency_score * weights["latency"]) +
        (availability_score * weights["availability"]) +
        (security_score * weights["security"]) +
        (m2m_score * weights["m2m"]) +
        (integrity_score * weights["integrity"])
    )

    return round(composite, 2)
