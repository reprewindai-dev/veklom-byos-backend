"""
Compositional Trust Algebra (CTA) for Multi-Agent Systems.
Implements the mathematical foundations of trust decay and delegation non-amplification.
"""

import math
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CompositionalTrustAlgebra:
    """
    Mathematical foundations for agent trust management.
    Ensures that trust cannot be artificially inflated via delegation.
    """

    DECAY_LAMBDA = 0.15 # Trust decay constant

    @classmethod
    def apply_trust_decay(cls, hops: int, base_trust: float) -> float:
        """
        Theorem 1: Guaranteed Trust Decay.
        T_h = T_0 * exp(-lambda * h)
        """
        if hops <= 0:
            return base_trust

        return base_trust * math.exp(-cls.DECAY_LAMBDA * hops)

    @staticmethod
    def verify_non_amplification(parent_trust: float, delegated_trust: float) -> bool:
        """
        Theorem 2: Delegation Non-Amplification.
        An agent cannot delegate a higher trust weight than it currently possesses.
        """
        return delegated_trust <= parent_trust

    @classmethod
    def compute_delegation_path_trust(cls, path_trust_scores: List[float]) -> float:
        """
        Computes the effective trust of a delegation chain.
        The chain is only as strong as its weakest link, decayed by distance.
        """
        if not path_trust_scores:
            return 0.0

        # Weakest link principle
        bottleneck_trust = min(path_trust_scores)

        # Distance decay principle (number of hops)
        hops = len(path_trust_scores) - 1

        return cls.apply_trust_decay(hops, bottleneck_trust)

    @staticmethod
    def calculate_reputation_vector(success_rate: float, tenure_days: int, anomaly_count: int) -> float:
        """
        Calculates a reputation score rho_j (0.0 to 1.0).
        Blends performance, reliability, and age.
        """
        # Base performance
        score = success_rate * 0.5

        # Tenure bonus (logarithmic growth)
        tenure_bonus = min(0.3, math.log1p(tenure_days) / 10.0)
        score += tenure_bonus

        # Anomaly penalty (aggressive)
        penalty = min(0.2, anomaly_count * 0.05)
        score -= penalty

        return max(0.0, min(1.0, score))
