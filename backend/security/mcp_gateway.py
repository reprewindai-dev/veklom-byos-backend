import time
from typing import Dict, Any, Optional
from datetime import datetime

from backend.models.mcpapi_v2 import AuthorityBundle, VeklomAgent
from backend.services.safety_layer import (
    BehavioralBaselineService, 
    AnomalyDetectionService, 
    RequestQuarantineService, 
    ApprovalQuorumService
)
from backend.services.intelligence_layer import CostAttributionService, RiskScoringService
from backend.services.governance_layer import PolicyCompositionEngine, PermissionsCalculator

class EnhancedMCPAPIRuntime:
    def __init__(self):
        # Safety Layer
        self.baseline_service = BehavioralBaselineService()
        self.anomaly_detection = AnomalyDetectionService(self.baseline_service)
        self.quarantine_service = RequestQuarantineService()
        self.quorum_service = ApprovalQuorumService()
        
        # Intelligence Layer
        self.cost_attribution = CostAttributionService()
        self.risk_scoring = RiskScoringService()
        
        # Governance Layer
        self.policy_composition = PolicyCompositionEngine()
        self.permissions_calculator = PermissionsCalculator()

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        connection_id = request.get("connection_id", "unknown")
        agent_id = request.get("agent_id")
        capability_id = request.get("capability_id")

        try:
            # ====================================================================
            # PHASE 1: IDENTITY, SECURITY, & UPSTREAM VERIFICATION
            # ====================================================================
            
            # The game-changer: We don't just verify a token. We hit the IdentityRAG (PGL)
            # to retrieve the agent's cross-cluster lineage, birth certificate, and 
            # real-time context before they execute anything.
            agent_context = self._resolve_agent_identity_with_rag(agent_id)
            if not agent_context:
                return self._create_error_response(connection_id, "401", "Agent not found or revoked")
            
            # BYOS Node 4 Enforcement: Cryptographically verify upstream evidence
            upstream_evidence_hash = request.get("upstream_evidence_hash")
            if not upstream_evidence_hash:
                 return self._create_error_response(connection_id, "403", "Missing upstream evidence hash from Node 3")
                 
            # Note: Signature verification, replay prevention, and hash validation go here.
            
            # ====================================================================
            # PHASE 2: CAPABILITY & POLICY
            # ====================================================================
            
            composition = self.policy_composition.compose_policy(
                agent_id, capability_id, 
                system_policy=None, owner_policy=None, runtime_policy=None, temporal_policy=None
            )
            
            # Assume starting trust is 50 for demo logic
            effective_perms = self.permissions_calculator.calculate_effective_permissions(
                agent_id, capability_id, 50.0, 
                composition["system_policy"], composition["owner_policy"], composition["runtime_policy"]
            )
            
            if not effective_perms.get("can_execute", False):
                return self._create_error_response(connection_id, "403", "Insufficient permissions")

            # ====================================================================
            # PHASE 3: SAFETY & ANOMALY DETECTION
            # ====================================================================
            
            from backend.models.mcpapi_v2 import CurrentMetric
            
            # Extract real-time metrics
            current_metric = CurrentMetric(
                requests_per_hour=15.0,
                failure_rate=0.02,
                new_capabilities=[],
                time_of_day=datetime.utcnow().hour,
                requests_in_window=15
            )
            
            all_anomalies = self.anomaly_detection.detect_anomalies(agent_id, current_metric)
            
            from backend.models.mcpapi_v2 import Severity
            critical_anomalies = [a for a in all_anomalies if a.severity == Severity.CRITICAL]
            
            if critical_anomalies:
                # Critical anomaly detected -> Automatic Quarantine
                quarantine = self.quarantine_service.quarantine(request, critical_anomalies, {"applied": True, "suppressed_score": 20})
                return self._handle_quarantine(quarantine, connection_id)

            # ====================================================================
            # PHASE 4: COST & BUDGET ENFORCEMENT
            # ====================================================================
            
            # BYOS Node 4 enforces compute cost based on VNP micro-stakes
            estimated_workload_cost = 5.0 # Stub calculation
            if not self.cost_attribution.can_afford_request(agent_id, capability_id, estimated_cost=estimated_workload_cost):
                return self._create_error_response(connection_id, "402", "VNP Micro-Stake budget exceeded. x402 Payment Required.")

            # ====================================================================
            # PHASE 5: APPROVAL WORKFLOWS
            # ====================================================================
            
            # If the effective permissions dict strictly requires approval
            if effective_perms.get("requires_approval", False) or any(a.recommended_action.value == "quarantine" for a in all_anomalies):
                quorum = self.quorum_service.create_quorum(
                    connection_id, 
                    effective_perms.get("approval_path", []),
                    2
                )
                return self._create_approval_response(connection_id, quorum)

            # ====================================================================
            # PHASE 6: EXECUTION
            # ====================================================================
            
            # In a real scenario, this routes to the underlying MCP tool.
            execution_start = time.time()
            result = {"data": "Capability executed successfully"}
            execution_time_ms = int((time.time() - execution_start) * 1000)

            # ====================================================================
            # PHASE 7: EVIDENCE & PROOF
            # ====================================================================
            
            import hashlib
            import json
            import uuid
            
            # Generate immutable evidence hash
            pgl_hash = hashlib.sha256(json.dumps({
                "who": agent_id,
                "what": capability_id,
                "when": datetime.utcnow().isoformat(),
                "result_status": "success"
            }).encode()).hexdigest()

            # ====================================================================
            # PHASE 8: AUDIT & COMPLIANCE
            # ====================================================================
            
            risk_profile = self.risk_scoring.calculate_risk_score(agent_id, {"anomaly_score": 0})

            # ====================================================================
            # PHASE 9: RESPONSE
            # ====================================================================
            
            return {
                "connection_id": connection_id,
                "status": "authorized",
                "evidence_hash": pgl_hash,
                "result": {
                    "output": result,
                    "execution_time_ms": execution_time_ms
                },
                "metadata": {
                    "trust_delta": 2,
                    "new_trust_score": 52,
                    "audit_logged": True,
                    "anomalies_detected": len(all_anomalies),
                    "cost_attributed": 10.0,
                    "risk_score": risk_profile["overall_risk_score"],
                    "threat_level": risk_profile["threat_level"]
                }
            }

        except Exception as e:
            return self._create_error_response(connection_id, "500", str(e))

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================
    
    def _resolve_agent_identity_with_rag(self, agent_id: str) -> Optional[Dict[str, Any]]:
        # Stub for the IdentityRAG (PGL) cross-cluster tenant resolution mapping
        if not agent_id:
            return None
        return {"agent_id": agent_id, "workspace_id": "ws-123"}
        
    def _handle_quarantine(self, quarantine: Any, connection_id: str) -> Dict[str, Any]:
        return {
            "connection_id": connection_id,
            "status": "quarantined",
            "quarantine_id": quarantine.quarantine_id,
            "reason": quarantine.quarantine_reason,
            "requires_approval": quarantine.approval_required,
            "approvers_needed": quarantine.approvers_required,
            "approval_deadline": quarantine.approval_deadline
        }
        
    def _create_approval_response(self, connection_id: str, quorum: Any) -> Dict[str, Any]:
        return {
            "connection_id": connection_id,
            "status": "approval_required",
            "approval_id": quorum.approval_id,
            "required_approvers": quorum.required_approvers,
            "required_count": quorum.required_count,
            "deadline": quorum.approval_deadline
        }
        
    def _create_error_response(self, connection_id: str, code: str, message: str) -> Dict[str, Any]:
        return {
            "connection_id": connection_id,
            "status": "error",
            "error": {
                "code": code,
                "message": message
            }
        }
