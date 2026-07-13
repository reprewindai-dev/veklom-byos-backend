import asyncio
import logging
from typing import Dict
from backend.core.security.governance import RevocationManager, AgentTrustScoreEngine

logger = logging.getLogger(__name__)

class CommanderAgent:
    """
    Agent-000: Sovereign control node logic for network-wide suspension and elevation.
    Monitors agent trust scores and triggers global revocation if scores drop below the critical threshold.
    """
    
    CRITICAL_TRUST_THRESHOLD = 40.0

    @classmethod
    async def evaluate_agent(
        cls, 
        agent_id: str, 
        performance_score: float,
        behavioral_score: float,
        semantic_score: float,
        governance_score: float,
        social_score: float
    ) -> Dict:
        """
        Evaluate an agent's trust score and act if it falls below the critical threshold.
        """
        evaluation = AgentTrustScoreEngine.calculate_ats(
            performance_score=performance_score,
            behavioral_score=behavioral_score,
            semantic_score=semantic_score,
            governance_score=governance_score,
            social_score=social_score
        )
        
        score = evaluation["score"]
        logger.info(f"[Commander Agent-000] Evaluated agent {agent_id}. ATS: {score}")

        if score < cls.CRITICAL_TRUST_THRESHOLD:
            reason = f"Agent {agent_id} trust score ({score}) fell below critical threshold ({cls.CRITICAL_TRUST_THRESHOLD})."
            logger.warning(f"[Commander Agent-000] Initiating global revocation for {agent_id}. Reason: {reason}")
            # Broadcast network-wide suspension
            await RevocationManager.revoke_pgl_identity(pgl_id=agent_id, reason=reason)
            evaluation["action_taken"] = "REVOKED"
        else:
            evaluation["action_taken"] = "NONE"
            
        return evaluation
