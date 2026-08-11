"""UACP Core - Pure logic module with no I/O dependencies."""

import hashlib
import logging
import math
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DecisionResult:
    """Immutable decision result with audit trail."""
    
    def __init__(
        self,
        decision: str,
        seked_state: Dict[str, Any],
        policy_evaluations: list,
        audit_hash: str,
        latency_ms: float = 0.0
    ):
        self.decision = decision
        self.seked_state = seked_state
        self.policy_evaluations = policy_evaluations
        self.audit_hash = audit_hash
        self.latency_ms = latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "seked_state": self.seked_state,
            "policy_evaluations": self.policy_evaluations,
            "audit_hash": self.audit_hash,
            "latency_ms": self.latency_ms
        }


class UACPDecisionKernel:
    """
    Pure logic kernel for UACP decision evaluation.
    No I/O, no external dependencies - deterministic and testable.
    """
    
    def __init__(self):
        self.policy_registry = self._init_policies()
    
    def _init_policies(self) -> Dict[str, callable]:
        """Initialize policy evaluation functions."""
        return {
            "budget_limit": self._check_budget_limit,
            "data_exfiltration": self._check_data_exfiltration,
            "risk_tier_check": self._check_risk_tier,
            "tool_allowlist": self._check_tool_allowlist,
            "constitutional_bounds": self._check_constitutional_bounds
        }
    
    def evaluate(
        self,
        intent: Dict[str, Any],
        v2_plan: Dict[str, Any],
        v3_context: Dict[str, Any],
        workspace_id: str,
        trace_id: Optional[str] = None
    ) -> DecisionResult:
        """
        Evaluate a plan against all policies and return a decision.
        
        Args:
            intent: User intent description
            v2_plan: V2 compiled plan with policy checkable frame
            v3_context: V3 contextual information
            workspace_id: Workspace identifier
            trace_id: Optional trace ID for observability
        
        Returns:
            DecisionResult with decision, state, and audit trail
        """
        start_time = datetime.now(timezone.utc)
        
        # Extract policy checkable frame
        policy_frame = v2_plan.get("policy_checkable_frame", {})
        risk_tier = policy_frame.get("risk_tier", "low")
        tools = policy_frame.get("tools", [])
        
        # Evaluate all policies
        policy_evaluations = []
        all_passed = True
        
        for policy_name, policy_func in self.policy_registry.items():
            try:
                passed, details = policy_func(policy_frame, v3_context, workspace_id)
                policy_evaluations.append({
                    "policy": policy_name,
                    "passed": passed,
                    "details": details
                })
                if not passed:
                    all_passed = False
            except Exception as e:
                logger.error(f"Policy evaluation failed for {policy_name}: {e}")
                policy_evaluations.append({
                    "policy": policy_name,
                    "passed": False,
                    "error": str(e)
                })
                all_passed = False
        
        # Determine final decision
        decision = self._determine_decision(risk_tier, all_passed, policy_evaluations)
        
        # Generate SEKED state
        seked_state = self._generate_seked_state(decision, v3_context)
        
        # Generate audit hash
        audit_hash = self._generate_audit_hash(intent, v2_plan, decision, trace_id)
        
        # Calculate latency
        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        logger.info(f"[UACP Core] Decision: {decision} for workspace {workspace_id}, trace {trace_id}")
        
        return DecisionResult(
            decision=decision,
            seked_state=seked_state,
            policy_evaluations=policy_evaluations,
            audit_hash=audit_hash,
            latency_ms=latency_ms
        )
    
    def _determine_decision(self, risk_tier: str, all_passed: bool, evaluations: list) -> str:
        """Determine final decision based on risk tier and policy results."""
        if not all_passed:
            return "DENIED"
        
        if risk_tier == "critical":
            return "DENIED"
        elif risk_tier == "high":
            return "HELD"
        else:
            return "APPROVED"
    
    def _generate_seked_state(self, decision: str, v3_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SEKED state based on decision."""
        return {
            "org_clearance_level": v3_context.get("clearance_level", "standard"),
            "human_in_loop_required": (decision == "HELD"),
            "constitutional_compliance": (decision != "DENIED"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_audit_hash(self, intent: Dict, plan: Dict, decision: str, trace_id: Optional[str]) -> str:
        """Generate deterministic audit hash for replay detection."""
        hash_input = f"{intent}|{plan}|{decision}|{trace_id}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:32]
    
    # Policy evaluation functions
    
    def _check_budget_limit(self, policy_frame: Dict, context: Dict, workspace_id: str) -> tuple:
        """Fail closed unless both estimated cost and remaining budget are valid."""
        if "estimated_cost" not in policy_frame:
            return False, {"cost": None, "budget": context.get("budget_remaining"), "reason": "estimated_cost_missing"}
        if "budget_remaining" not in context:
            return False, {"cost": policy_frame.get("estimated_cost"), "budget": None, "reason": "budget_remaining_missing"}

        cost = policy_frame.get("estimated_cost")
        budget = context.get("budget_remaining")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
            return False, {"cost": cost, "budget": budget, "reason": "estimated_cost_invalid"}
        if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not math.isfinite(budget) or budget < 0:
            return False, {"cost": cost, "budget": budget, "reason": "budget_remaining_invalid"}

        passed = cost <= budget
        return passed, {"cost": cost, "budget": budget}
    
    def _check_data_exfiltration(self, policy_frame: Dict, context: Dict, workspace_id: str) -> tuple:
        """Check for data exfiltration risks."""
        has_pii = policy_frame.get("contains_pii", False)
        external_destinations = policy_frame.get("external_destinations", [])
        passed = not (has_pii and len(external_destinations) > 0)
        return passed, {"has_pii": has_pii, "external_destinations": len(external_destinations)}
    
    def _check_risk_tier(self, policy_frame: Dict, context: Dict, workspace_id: str) -> tuple:
        """Check if risk tier is acceptable."""
        risk_tier = policy_frame.get("risk_tier", "low")
        max_risk = context.get("max_risk_tier", "high")
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        passed = risk_order.get(risk_tier, 99) <= risk_order.get(max_risk, 2)
        return passed, {"risk_tier": risk_tier, "max_risk": max_risk}
    
    def _check_tool_allowlist(self, policy_frame: Dict, context: Dict, workspace_id: str) -> tuple:
        """Check if all tools are in the allowlist."""
        tools = policy_frame.get("tools", [])
        allowlist = context.get("tool_allowlist", [])
        blocked = [t for t in tools if t not in allowlist]
        passed = len(blocked) == 0
        return passed, {"blocked_tools": blocked}
    
    def _check_constitutional_bounds(self, policy_frame: Dict, context: Dict, workspace_id: str) -> tuple:
        """Check constitutional policy bounds."""
        constitutional_violations = policy_frame.get("constitutional_violations", [])
        passed = len(constitutional_violations) == 0
        return passed, {"violations": constitutional_violations}
