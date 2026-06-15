"""Memory Fabric Service for tracking risks, outcome feedback, and high performer registry."""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models.risk_profile import OrgRiskProfile, OutcomeFeedback, HighPerformerEntry


class MemoryFabricService:
    """Tracks and scores organization risks, records feedback, and registers high-performing runs."""

    @classmethod
    async def get_org_risk_profile(cls, db: AsyncSession, org_id: str) -> OrgRiskProfile:
        """Retrieves or initializes the risk profile for a given organization."""
        query = select(OrgRiskProfile).where(OrgRiskProfile.org_id == org_id)
        result = await db.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = OrgRiskProfile(
                org_id=org_id,
                abuse_score=0.0,
                override_abuse_score=0.0,
                payment_risk_score=0.0,
                injection_attempts=0,
                composite_risk=0.0
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
            
        return profile

    @classmethod
    async def record_execution(
        cls,
        db: AsyncSession,
        org_id: str,
        trace_id: str,
        injection_detected: bool,
        override_applied: bool,
        task_type: str,
        genome_hash: str,
        performance_score: float = 1.0,
        output_signature: str = ""
    ) -> None:
        """Updates organization risk metrics based on execution outcome and registers high-performing signatures."""
        profile = await cls.get_org_risk_profile(db, org_id)
        
        # 1. Update injection metrics
        if injection_detected:
            profile.injection_attempts += 1
            profile.abuse_score = min(profile.abuse_score + 0.15, 1.0)
            
        # 2. Update override metrics
        if override_applied:
            profile.override_abuse_score = min(profile.override_abuse_score + 0.05, 1.0)
            
        # 3. Composite score calculation
        profile.composite_risk = min(
            (profile.abuse_score * 0.5) + (profile.override_abuse_score * 0.3) + (profile.payment_risk_score * 0.2),
            1.0
        )
        
        # 4. Record high performer entry if performance is high
        if performance_score >= 0.9 and output_signature:
            q = select(HighPerformerEntry).where(
                HighPerformerEntry.genome_hash == genome_hash,
                HighPerformerEntry.task_type == task_type,
                HighPerformerEntry.output_signature == output_signature
            )
            res = await db.execute(q)
            existing = res.scalar_one_or_none()
            
            if not existing:
                high_perf = HighPerformerEntry(
                    task_type=task_type,
                    output_signature=output_signature,
                    performance_score=performance_score,
                    genome_hash=genome_hash
                )
                db.add(high_perf)
                
        await db.commit()

    @classmethod
    async def submit_feedback(
        cls,
        db: AsyncSession,
        trace_id: str,
        accepted: bool,
        user_rating: Optional[int] = None,
        feedback_text: Optional[str] = None,
        actual_outcome: Optional[Dict[str, Any]] = None,
        predicted_outcome: Optional[Dict[str, Any]] = None
    ) -> OutcomeFeedback:
        """Saves user rating and outcome comparison feedback."""
        query = select(OutcomeFeedback).where(OutcomeFeedback.trace_id == trace_id)
        result = await db.execute(query)
        feedback = result.scalar_one_or_none()
        
        if feedback:
            feedback.accepted = accepted
            feedback.user_rating = user_rating
            feedback.feedback_text = feedback_text
            feedback.actual_outcome = actual_outcome
            feedback.predicted_outcome = predicted_outcome
        else:
            feedback = OutcomeFeedback(
                trace_id=trace_id,
                accepted=accepted,
                user_rating=user_rating,
                feedback_text=feedback_text,
                actual_outcome=actual_outcome,
                predicted_outcome=predicted_outcome
            )
            db.add(feedback)
            
        await db.commit()
        await db.refresh(feedback)
        return feedback
