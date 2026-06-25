"""
SIGMA (Spectral Inequalities for Gram Matrix Analysis) Framework.
Prevents recursive training model collapse by analyzing embedding space eigenspectrum.
"""

import numpy as np
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class SigmaSpectralLens:
    """
    Analyzes the Gram matrix of embedding vectors to detect representation space health.
    If the eigenspectrum drifts towards singularity (log-determinant -> -inf),
    it indicates model collapse.
    """

    @staticmethod
    def compute_log_det(embeddings: np.ndarray, regularizer: float = 1e-6) -> float:
        """
        Calculates the log-determinant of the Gram matrix G = MM^T.
        Using a regularizer for numerical stability.
        """
        if embeddings.shape[0] < embeddings.shape[1]:
            # Case where sample size n is greater than embedding dim m
            # G = M M^T (m x m)
            M = embeddings # (m x n)
            G = np.dot(M, M.T)
        else:
            # Case where sample size n is less than embedding dim m
            # We can use Sylvester's determinant theorem: det(I + AB) = det(I + BA)
            # But for simplicity, we assume n > m as per SIGMA spec.
            G = np.dot(embeddings.T, embeddings)

        m = G.shape[0]
        # Regularized Gram matrix
        G_reg = G + regularizer * np.eye(m)

        # Calculate log determinant using Cholesky or SVD for stability
        try:
            # np.linalg.slogdet returns (sign, logdet)
            sign, logdet = np.linalg.slogdet(G_reg)
            if sign <= 0:
                logger.warning("Gram matrix is not positive definite even with regularizer.")
            return logdet
        except np.linalg.LinAlgError:
            logger.error("Gram matrix determinant calculation failed.")
            return -np.inf

    @classmethod
    def estimate_spectral_drift(
        cls,
        observed_embeddings: np.ndarray,
        baseline_log_det: float,
        total_sample_count: int,
        regularizer: float = 1e-6
    ) -> float:
        """
        Estimates spectral drift using block sub-sampling strategy.
        delta_G = G_KF(k) - G_KF(0)
        """
        m, n_A = observed_embeddings.shape
        rho = n_A / total_sample_count
        beta_k = (total_sample_count - n_A) * rho

        G_A = np.dot(observed_embeddings, observed_embeddings.T)

        # LogDet_delta(G_A + beta * I)
        log_det_observed = np.linalg.slogdet(G_A + (beta_k + regularizer) * np.eye(m))[1]

        # G_KF = LogDet - m * log(beta + delta)
        g_kf_k = log_det_observed - m * np.log(beta_k + regularizer)

        drift = g_kf_k - baseline_log_det
        return drift

    @classmethod
    def verify_quality_gate(
        cls,
        embeddings: List[List[float]],
        baseline_log_det: float,
        threshold: float = 5.0
    ) -> bool:
        """
        Verifies if the current batch of embeddings passes the SIGMA spectral quality gate.
        """
        if not embeddings:
            return False

        M = np.array(embeddings).T # Convert list of vectors to (m x n) matrix
        current_log_det = cls.compute_log_det(M)

        # In a real system, total_sample_count would be known.
        # Here we use the observed count as an approximation for the drift estimate.
        drift = abs(current_log_det - baseline_log_det)

        if drift > threshold:
            logger.warning(f"SIGMA gate failure: Spectral drift detected ({drift:.4f} > {threshold})")
            return False

        return True
