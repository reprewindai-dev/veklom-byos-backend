"""SEKED service integration for Veklom Authority system."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.core.database.database import get_db
from backend.db.models.authority import AuthorityDecision, AuthorityRun


class SEKEDService:
    """SEKED v1.0 measurement and decision service."""
    
    SEKED_SPECIFICATION_VERSION = "1.0"
    SEKED_CANONICAL_FINGERPRINT = "038f8464884a556fbee43972b27cbdfd08d3b522e644c0c644ad1b2ded82fcc7"
    
    @staticmethod
    def calculate_seked_ratios(measurement: Dict[str, Any]) -> Dict[str, float]:
        """Calculate SEKED ratios from measurement.
        
        Args:
            measurement: Dict with E, R, C, D, S values (0-9)
            
        Returns:
            Dict with sigma, ci, si ratios
        """
        E = measurement.get('E', 5)
        R = measurement.get('R', 5)
        C = measurement.get('C', 5)
        D = measurement.get('D', 5)
        S = measurement.get('S', 5)
        
        # SEKED v1.0 formula: σ = (E + D) / (R + 1)
        sigma = (E + D) / (R + 1)
        
        # Cognitive Index: CI = C / I (where I = 10 - R)
        I = 10 - R
        ci = C / I
        
        # Stability Index: SI = S / 10
        si = S / 10
        
        return {
            'sigma': round(sigma, 2),
            'ci': round(ci, 2),
            'si': round(si, 2)
        }
    
    @staticmethod
    def get_seked_directive(ratio: float) -> Dict[str, Any]:
        """Get SEKED directive based on sigma ratio.
        
        Args:
            ratio: Sigma ratio value
            
        Returns:
            Directive dict with action_type and reasoning
        """
        if ratio >= 4.0:
            return {
                'ratio': ratio,
                'directive': "Execute primary objectives with full resources",
                'action_type': "EXECUTE",
                'confidence': 0.95,
                'reasoning': 'High operational capacity indicates optimal execution state'
            }
        elif ratio >= 2.5:
            return {
                'ratio': ratio,
                'directive': "Prepare for execution with monitoring protocols",
                'action_type': "PREPARE",
                'confidence': 0.85,
                'reasoning': 'Moderate capacity suggests preparation phase'
            }
        elif ratio >= 1.5:
            return {
                'ratio': ratio,
                'directive': "Conserve resources and maintain current state",
                'action_type': "CONSERVE",
                'confidence': 0.75,
                'reasoning': 'Limited capacity requires conservation'
            }
        elif ratio >= 0.5:
            return {
                'ratio': ratio,
                'directive': "Initiate recovery protocols and resource allocation",
                'action_type': "RECOVER",
                'confidence': 0.80,
                'reasoning': 'Low capacity indicates need for recovery'
            }
        else:
            return {
                'ratio': ratio,
                'directive': "Escalate to human intervention and emergency protocols",
                'action_type': "ESCALATE",
                'confidence': 0.90,
                'reasoning': 'Critical capacity requires immediate escalation'
            }
    
    @staticmethod
    def create_seked_fingerprint(state: Dict[str, Any]) -> str:
        """Create cryptographic fingerprint of SEKED state.
        
        Args:
            state: SEKED state dict
            
        Returns:
            SHA-256 fingerprint
        """
        state_string = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_string.encode()).hexdigest()
    
    @staticmethod
    def create_seked_state(measurement: Dict[str, Any]) -> Dict[str, Any]:
        """Create complete SEKED state from measurement.
        
        Args:
            measurement: SEKED measurement dict
            
        Returns:
            Complete SEKED state with ratios, directive, and fingerprint
        """
        measurement_with_timestamp = {
            **measurement,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        ratios = SEKEDService.calculate_seked_ratios(measurement_with_timestamp)
        directive = SEKEDService.get_seked_directive(ratios['sigma'])
        
        state = {
            'measurement': measurement_with_timestamp,
            'ratios': ratios,
            'directive': directive
        }
        
        fingerprint = SEKEDService.create_seked_fingerprint(state)
        
        return {
            **state,
            'fingerprint': fingerprint
        }
    
    @staticmethod
    def apply_seked_decision(
        authority_decision: AuthorityDecision,
        measurement: Optional[Dict[str, Any]] = None
    ) -> AuthorityDecision:
        """Apply SEKED decision to authority decision.
        
        Args:
            authority_decision: Existing authority decision
            measurement: Optional SEKED measurement
            
        Returns:
            Updated authority decision with SEKED data
        """
        if not measurement:
            # Default measurement for agent state
            measurement = {'E': 5, 'R': 5, 'C': 5, 'D': 5, 'S': 5}
        
        seked_state = SEKEDService.create_seked_state(measurement)
        
        # Map SEKED action_type to authority decision
        seked_action = seked_state['directive']['action_type']
        if seked_action == 'EXECUTE':
            authority_decision.decision = 'approve'
            authority_decision.confidence_score = seked_state['directive']['confidence']
        elif seked_action in ['RECOVER', 'CONSERVE']:
            authority_decision.decision = 'deny'
            authority_decision.confidence_score = seked_state['directive']['confidence']
        elif seked_action == 'ESCALATE':
            authority_decision.decision = 'escalate'
            authority_decision.confidence_score = seked_state['directive']['confidence']
        else:
            authority_decision.decision = 'deny'
            authority_decision.confidence_score = 0.5
        
        # Store SEKED data
        authority_decision.seked_measurement = seked_state['measurement']
        authority_decision.seked_ratios = seked_state['ratios']
        authority_decision.seked_directive = seked_state['directive']
        authority_decision.reason = f"SEKED directive: {seked_state['directive']['directive']}"
        
        return authority_decision
    
    @staticmethod
    def initialize_authority_run_with_seked(
        authority_run: AuthorityRun,
        initial_measurement: Optional[Dict[str, Any]] = None
    ) -> AuthorityRun:
        """Initialize AuthorityRun with SEKED state.
        
        Args:
            authority_run: Authority run to initialize
            initial_measurement: Optional initial SEKED measurement
            
        Returns:
            Updated authority run with SEKED integration
        """
        if not initial_measurement:
            initial_measurement = {'E': 5, 'R': 5, 'C': 5, 'D': 5, 'S': 5}
        
        seked_state = SEKEDService.create_seked_state(initial_measurement)
        
        authority_run.seked_initial_measurement = seked_state['measurement']
        authority_run.seked_final_directive = seked_state['directive']
        
        return authority_run
    
    @staticmethod
    def get_seked_health_status() -> Dict[str, Any]:
        """Get SEKED service health status.
        
        Returns:
            Health status dict
        """
        return {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'specification_version': SEKEDService.SEKED_SPECIFICATION_VERSION,
            'fingerprint': SEKEDService.SEKED_CANONICAL_FINGERPRINT,
            'service': 'SEKED v1.0 Policy Engine'
        }

    @staticmethod
    async def check_agent_privilege(db: Any, agent_id: str) -> bool:
        """Check if an agent has execution privileges.
        
        Args:
            db: Database session
            agent_id: The agent to check
            
        Returns:
            bool: True if active, False if revoked
        """
        from sqlalchemy import select
        from backend.db.models.benchmarks import AgentPrivilege
        
        stmt = select(AgentPrivilege).where(AgentPrivilege.agent_id == agent_id)
        result = await db.execute(stmt)
        privilege = result.scalar_one_or_none()
        
        if not privilege:
            # If no privilege record exists, default to active
            return True
            
        return privilege.status == "active"

    @staticmethod
    async def revoke_agent_privileges(
        db: Any, 
        agent_id: str, 
        provider: str, 
        reason: str,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Revoke an agent's execution privileges dynamically.
        
        Args:
            db: Database session
            agent_id: The agent to revoke
            provider: The provider name
            reason: The revocation reason
            run_id: The ID of the benchmark run that triggered this
            
        Returns:
            Dict containing the updated privilege record
        """
        from sqlalchemy import select
        from backend.db.models.benchmarks import AgentPrivilege
        from datetime import datetime, timezone
        
        stmt = select(AgentPrivilege).where(AgentPrivilege.agent_id == agent_id)
        result = await db.execute(stmt)
        privilege = result.scalar_one_or_none()
        
        now = datetime.now(timezone.utc)
        
        if not privilege:
            privilege = AgentPrivilege(
                agent_id=agent_id,
                provider=provider,
                status="revoked",
                revoked_at=now,
                revoked_reason=reason,
                revoked_by="system",
                last_benchmark_run_id=run_id
            )
            db.add(privilege)
        else:
            privilege.status = "revoked"
            privilege.revoked_at = now
            privilege.revoked_reason = reason
            privilege.revoked_by = "system"
            if run_id:
                privilege.last_benchmark_run_id = run_id
            
        await db.commit()
        await db.refresh(privilege)
        
        return {
            "agent_id": privilege.agent_id,
            "status": privilege.status,
            "revocation_reason": privilege.revoked_reason
        }

    @staticmethod
    async def restore_agent_privileges(
        db: Any, 
        agent_id: str, 
        admin_id: str, 
        reason: str
    ) -> Dict[str, Any]:
        """Manually restore an agent's execution privileges.
        
        Args:
            db: Database session
            agent_id: The agent to restore
            admin_id: The administrator performing the restore
            reason: The restore reason
            
        Returns:
            Dict containing the updated privilege record
        """
        from sqlalchemy import select
        from backend.db.models.benchmarks import AgentPrivilege
        from datetime import datetime, timezone
        
        stmt = select(AgentPrivilege).where(AgentPrivilege.agent_id == agent_id)
        result = await db.execute(stmt)
        privilege = result.scalar_one_or_none()
        
        if not privilege:
            raise ValueError(f"Agent {agent_id} privilege record not found.")
            
        now = datetime.now(timezone.utc)
        
        privilege.status = "active"
        privilege.restored_at = now
        privilege.restored_by = admin_id
        privilege.restore_reason = reason
            
        await db.commit()
        await db.refresh(privilege)
        
        return {
            "agent_id": privilege.agent_id,
            "status": privilege.status,
            "restore_reason": privilege.restore_reason
        }

# Global SEKED service instance
seked_service = SEKEDService()
