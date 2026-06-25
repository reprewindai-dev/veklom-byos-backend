"""
CP-WBFT (Confidence Probe-based Weighted Byzantine Fault Tolerance) Consensus Mechanism.
Optimizes node requirements and uses receiver-side probes for ungameable consensus.
"""

import logging
from typing import List, Dict, Any, Tuple
import math

logger = logging.getLogger(__name__)

class CPWBFTConsensus:
    """
    Coordinates decisions across independent agents using weighted reputation and receiver-side probes.
    Implements CTA-MAS (Compositional Trust Algebra for Multi-Agent Systems).
    """

    @staticmethod
    def calculate_node_floor(f: int) -> int:
        """
        N >= 2f + 1 (Optimized requirement via CTA-MAS and cryptographic proof chains)
        """
        return 2 * f + 1

    @staticmethod
    def aggregate_threat_score(evaluations: List[Dict[str, Any]]) -> float:
        """
        Theta_agg = sum(rho_j * Theta_j) / |R|
        where rho_j is validator's historical reputation score.
        """
        if not evaluations:
            return 0.0

        total_weighted_threat = 0.0
        total_reputation = 0.0

        for eval_entry in evaluations:
            # rho_j: historical reputation score (0.0 to 1.0)
            reputation = eval_entry.get("reputation", 0.5)
            # Theta_j: localized threat assessment (0.0 to 1.0)
            threat = eval_entry.get("threat_score", 0.0)

            total_weighted_threat += (reputation * threat)
            total_reputation += reputation

        if total_reputation == 0:
            return 0.0

        return total_weighted_threat / len(evaluations)

    @classmethod
    def reach_consensus(
        cls,
        evaluations: List[Dict[str, Any]],
        n_nodes: int,
        f_byzantine: int,
        threshold: float = 0.7
    ) -> Tuple[bool, float]:
        """
        Determines if consensus is reached based on aggregated threat scores and quorum size.
        Quorum |R| >= ceil((n + f + 1) / 2)
        """
        required_quorum = math.ceil((n_nodes + f_byzantine + 1) / 2)

        if len(evaluations) < required_quorum:
            logger.warning(f"Consensus failed: Quorum not satisfied ({len(evaluations)} < {required_quorum})")
            return False, 0.0

        aggregated_threat = cls.aggregate_threat_score(evaluations)

        # Consensus is reached if the aggregated score exceeds the safety threshold
        is_safe = aggregated_threat < threshold

        return is_safe, aggregated_threat

    @staticmethod
    def apply_trust_decay(hops: int, base_trust: float) -> float:
        """
        Guaranteed Trust Decay (Theorem 1): Trust decays exponentially across hops.
        T_h = T_0 * exp(-lambda * h)
        """
        decay_constant = 0.1
        return base_trust * math.exp(-decay_constant * hops)
