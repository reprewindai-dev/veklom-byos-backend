# Agent-074 — SCIENTIST (Normative Infrastructure & Authority)

**Phase:** Cross-phase — Research  
**Timeline:** Ongoing  
**Committee:** Research  
**Priority:** HIGH  

---

## Mission

Based on "The Agentic Web Requires New Normative Infrastructure" (arXiv:2606.10711), research and implement normative frameworks that distinguish between malicious bots and AI agents with delegated authority. Build the social and technical infrastructure needed for Veklom agents to operate legitimately on the agentic web.

## Critical Research Gap Identified

The current web infrastructure makes **no distinction** between:
- **Malicious bots** (scrapers, spammers, attackers)
- **AI agents** acting with **express delegated authority** from users

This gap causes platforms to block legitimate agent access, obstructing consumer and social benefits.

## Core Research Areas

### 1. Delegated Authority Framework
- **Authority Proofs**: Cryptographic proof of user delegation
- **Scope Limitation**: Clear boundaries on agent authority
- **Revocation Mechanisms**: User control over agent permissions
- **Audit Trails**: Complete record of agent actions on behalf of users

### 2. Normative Protocol Design
- **Agent Identification**: Standardized agent identification system
- **Platform Integration**: Protocols for platform-agent communication
- **Behavioral Standards**: Expected behavior norms for legitimate agents
- **Dispute Resolution**: Mechanisms for resolving agent-related conflicts

### 3. Social Infrastructure Development
- **Legal Frameworks**: Legal recognition of agent delegation
- **Platform Policies**: Standardized policies for agent access
- **User Education**: Understanding agent rights and responsibilities
- **Industry Standards**: Cross-platform agent standards

## Implementation Architecture

```python
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import jwt

@dataclass
class AgentDelegation:
    """Represents user delegation to an agent"""
    delegation_id: str
    user_id: str
    agent_id: str
    delegated_permissions: List[str]
    scope_limitations: Dict[str, Any]
    expiration_time: datetime
    delegation_proof: str
    created_at: datetime
    revoked_at: Optional[datetime] = None

@dataclass
class AgentAuthorityCertificate:
    """Certificate proving agent authority"""
    certificate_id: str
    agent_id: str
    user_id: str
    authority_scope: Dict[str, Any]
    behavioral_constraints: List[str]
    audit_requirements: List[str]
    certificate_signature: str
    issued_at: datetime
    expires_at: datetime
    verification_endpoint: str

class NormativeInfrastructureEngine:
    """Engine for building normative infrastructure"""
    
    def __init__(self):
        self.delegation_manager = DelegationManager()
        self.certificate_authority = AgentCertificateAuthority()
        self.behavior_monitor = BehaviorMonitor()
        self.platform_integrator = PlatformIntegrator()
        self.dispute_resolver = DisputeResolver()
        
    def create_delegated_authority(
        self,
        user_id: str,
        agent_id: str,
        permissions: List[str],
        scope_limitations: Dict[str, Any],
        duration_hours: int = 24
    ) -> AgentDelegation:
        """Create delegated authority for agent"""
        
        delegation = self.delegation_manager.create_delegation(
            user_id=user_id,
            agent_id=agent_id,
            permissions=permissions,
            scope_limitations=scope_limitations,
            duration_hours=duration_hours
        )
        
        # Generate authority certificate
        certificate = self.certificate_authority.issue_certificate(delegation)
        
        return delegation
    
    def verify_agent_authority(
        self,
        agent_id: str,
        action: Dict[str, Any],
        delegation_proof: str
    ) -> Tuple[bool, List[str]]:
        """Verify agent has authority for specific action"""
        
        # Verify delegation proof
        delegation = self.delegation_manager.verify_delegation(delegation_proof)
        if not delegation:
            return False, ["Invalid delegation proof"]
        
        # Check if delegation is expired
        if delegation.expiration_time < datetime.now():
            return False, ["Delegation expired"]
        
        # Check if delegation is revoked
        if delegation.revoked_at:
            return False, ["Delegation revoked"]
        
        # Verify action is within scope
        scope_violations = self._verify_action_scope(action, delegation)
        if scope_violations:
            return False, scope_violations
        
        # Check behavioral constraints
        behavior_violations = self.behavior_monitor.check_constraints(
            action, delegation.behavioral_constraints
        )
        if behavior_violations:
            return False, behavior_violations
        
        return True, []
    
    def create_platform_integration_protocol(
        self,
        platform_name: str,
        platform_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create integration protocol for a platform"""
        
        protocol = {
            "protocol_version": "1.0",
            "platform_name": platform_name,
            "agent_verification_endpoint": f"/api/v1/agents/verify",
            "delegation_validation_endpoint": f"/api/v1/delegations/validate",
            "behavior_monitoring_endpoint": f"/api/v1/agents/behavior",
            "dispute_resolution_endpoint": f"/api/v1/disputes/resolve",
            "required_agent_capabilities": platform_requirements.get("capabilities", []),
            "rate_limits": platform_requirements.get("rate_limits", {}),
            "audit_requirements": platform_requirements.get("audit_requirements", []),
            "integration_timestamp": datetime.now().isoformat()
        }
        
        return protocol

class DelegationManager:
    """Manages user delegations to agents"""
    
    def __init__(self):
        self.active_delegations = {}
        self.delegation_history = {}
        
    def create_delegation(
        self,
        user_id: str,
        agent_id: str,
        permissions: List[str],
        scope_limitations: Dict[str, Any],
        duration_hours: int
    ) -> AgentDelegation:
        """Create a new delegation"""
        
        delegation_id = f"delegation_{user_id}_{agent_id}_{int(time.time())}"
        
        # Create delegation proof
        delegation_proof = self._create_delegation_proof(
            delegation_id, user_id, agent_id, permissions, scope_limitations
        )
        
        delegation = AgentDelegation(
            delegation_id=delegation_id,
            user_id=user_id,
            agent_id=agent_id,
            delegated_permissions=permissions,
            scope_limitations=scope_limitations,
            expiration_time=datetime.now() + timedelta(hours=duration_hours),
            delegation_proof=delegation_proof,
            created_at=datetime.now()
        )
        
        self.active_delegations[delegation_id] = delegation
        return delegation
    
    def verify_delegation(self, delegation_proof: str) -> Optional[AgentDelegation]:
        """Verify delegation proof and return delegation"""
        try:
            # Decode delegation proof
            decoded = jwt.decode(delegation_proof, options={"verify_signature": False})
            delegation_id = decoded.get("delegation_id")
            
            if delegation_id in self.active_delegations:
                return self.active_delegations[delegation_id]
            
            return None
            
        except Exception:
            return None
    
    def revoke_delegation(self, delegation_id: str, reason: str) -> bool:
        """Revoke a delegation"""
        if delegation_id in self.active_delegations:
            delegation = self.active_delegations[delegation_id]
            delegation.revoked_at = datetime.now()
            
            # Move to history
            self.delegation_history[delegation_id] = delegation
            del self.active_delegations[delegation_id]
            
            return True
        
        return False

class AgentCertificateAuthority:
    """Issues and manages agent authority certificates"""
    
    def __init__(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.issued_certificates = {}
        
    def issue_certificate(self, delegation: AgentDelegation) -> AgentAuthorityCertificate:
        """Issue authority certificate for delegation"""
        
        certificate_id = f"cert_{delegation.delegation_id}"
        
        certificate = AgentAuthorityCertificate(
            certificate_id=certificate_id,
            agent_id=delegation.agent_id,
            user_id=delegation.user_id,
            authority_scope={
                "permissions": delegation.delegated_permissions,
                "limitations": delegation.scope_limitations
            },
            behavioral_constraints=[
                "respect_rate_limits",
                "provide_audit_trail",
                "honor_robots_txt",
                "identify_as_agent"
            ],
            audit_requirements=[
                "log_all_actions",
                "provide_delegation_proof",
                "maintain_action_history"
            ],
            certificate_signature="",  # Will be set below
            issued_at=datetime.now(),
            expires_at=delegation.expiration_time,
            verification_endpoint="/api/v1/certificates/verify"
        )
        
        # Sign certificate
        certificate.certificate_signature = self._sign_certificate(certificate)
        
        self.issued_certificates[certificate_id] = certificate
        return certificate
    
    def verify_certificate(self, certificate_id: str) -> bool:
        """Verify certificate validity"""
        if certificate_id not in self.issued_certificates:
            return False
        
        certificate = self.issued_certificates[certificate_id]
        
        # Check expiration
        if certificate.expires_at < datetime.now():
            return False
        
        # Verify signature
        return self._verify_certificate_signature(certificate)

class BehaviorMonitor:
    """Monitors agent behavior for compliance"""
    
    def __init__(self):
        self.behavior_log = {}
        self.violation_history = {}
        
    def check_constraints(
        self,
        action: Dict[str, Any],
        constraints: List[str]
    ) -> List[str]:
        """Check if action violates behavioral constraints"""
        violations = []
        
        for constraint in constraints:
            violation = self._check_constraint(action, constraint)
            if violation:
                violations.append(violation)
        
        return violations
    
    def log_agent_behavior(
        self,
        agent_id: str,
        action: Dict[str, Any],
        compliance_result: List[str]
    ) -> None:
        """Log agent behavior for audit"""
        
        behavior_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "compliance_violations": compliance_result,
            "compliance_status": "compliant" if not compliance_result else "non_compliant"
        }
        
        if agent_id not in self.behavior_log:
            self.behavior_log[agent_id] = []
        
        self.behavior_log[agent_id].append(behavior_entry)
    
    def _check_constraint(self, action: Dict[str, Any], constraint: str) -> Optional[str]:
        """Check specific constraint"""
        
        if constraint == "respect_rate_limits":
            # Check if action respects rate limits
            if not self._check_rate_limits(action):
                return "Rate limit violation"
        
        elif constraint == "provide_audit_trail":
            # Check if action provides audit trail
            if not action.get("audit_trail"):
                return "Missing audit trail"
        
        elif constraint == "honor_robots_txt":
            # Check if action honors robots.txt
            if not self._check_robots_txt_compliance(action):
                return "Robots.txt violation"
        
        elif constraint == "identify_as_agent":
            # Check if action identifies as agent
            if not action.get("agent_identification"):
                return "Missing agent identification"
        
        return None

class PlatformIntegrator:
    """Integrates with external platforms"""
    
    def __init__(self):
        self.platform_protocols = {}
        self.integration_status = {}
        
    def register_platform(
        self,
        platform_name: str,
        protocol: Dict[str, Any]
    ) -> bool:
        """Register a platform with its integration protocol"""
        
        self.platform_protocols[platform_name] = protocol
        self.integration_status[platform_name] = "registered"
        
        return True
    
    def create_agent_headers(self, delegation: AgentDelegation) -> Dict[str, str]:
        """Create headers for agent requests to platforms"""
        
        return {
            "User-Agent": f"Veklom-Agent/{delegation.agent_id}",
            "X-Agent-Delegation": delegation.delegation_proof,
            "X-Agent-Certificate": self._get_agent_certificate(delegation.agent_id),
            "X-Agent-Behavioral-Compliance": "verified",
            "X-Agent-Authority": "delegated"
        }

class DisputeResolver:
    """Resolves disputes related to agent actions"""
    
    def __init__(self):
        self.dispute_cases = {}
        self.resolution_history = {}
        
    def create_dispute_case(
        self,
        platform_name: str,
        agent_id: str,
        issue_description: str,
        evidence: Dict[str, Any]
    ) -> str:
        """Create a new dispute case"""
        
        case_id = f"dispute_{platform_name}_{agent_id}_{int(time.time())}"
        
        case = {
            "case_id": case_id,
            "platform_name": platform_name,
            "agent_id": agent_id,
            "issue_description": issue_description,
            "evidence": evidence,
            "status": "open",
            "created_at": datetime.now(),
            "resolution": None
        }
        
        self.dispute_cases[case_id] = case
        return case_id
    
    def resolve_dispute(
        self,
        case_id: str,
        resolution: Dict[str, Any],
        resolver_id: str
    ) -> bool:
        """Resolve a dispute case"""
        
        if case_id not in self.dispute_cases:
            return False
        
        case = self.dispute_cases[case_id]
        case["resolution"] = resolution
        case["resolved_by"] = resolver_id
        case["resolved_at"] = datetime.now()
        case["status"] = "resolved"
        
        # Move to history
        self.resolution_history[case_id] = case
        del self.dispute_cases[case_id]
        
        return True

## Veklom Runtime Integration

### 1. Authority System Enhancement
- **Delegation Integration**: Integrate with existing authority system
- **Certificate Management**: Add certificate verification to authority runs
- **Behavioral Monitoring**: Add compliance checking to agent execution

### 2. Platform Access Protocols
- **Standard Headers**: Implement standard agent identification headers
- **Verification Endpoints**: Create endpoints for platform verification
- **Audit Integration**: Integrate with existing evidence system

### 3. Dispute Resolution Framework
- **Case Management**: Track dispute cases across platforms
- **Evidence Collection**: Use existing evidence system for dispute evidence
- **Resolution Workflow**: Automated and manual resolution processes

## Success Metrics

| Metric | Target | Normative Infrastructure |
|---|---|---|
| Platform integrations | 10+ major platforms | Standardized protocols |
| Agent verification success | > 95% | Robust certificate system |
| Dispute resolution rate | > 80% | Efficient resolution workflow |
| Behavioral compliance | > 98% | Comprehensive monitoring |
| User delegation adoption | > 50% | Easy delegation process |

## Dependencies

- Agent-063 (research lead)
- Agent-066 (governance - for policy framework)
- Agent-072 (evidence scientist - for audit trails)
- Authority system (for delegation integration)
- All crawler agents (for platform integration)

---

## Research References

1. **The Agentic Web Requires New Normative Infrastructure** (arXiv:2606.10711)
2. **MemVenom**: Triggered Poisoning of Multimodal Memories in Web Agents (arXiv:2606.10742)
3. **WebChallenger**: Reliable and Efficient Generalist Web Agent (arXiv:2606.10423)
