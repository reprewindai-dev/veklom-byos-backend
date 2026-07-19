import datetime
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from uuid import uuid4
from backend.apps.gpc.canonical_plan import CanonicalPlanIR

class DecisionRecord(BaseModel):
    """Immutable record of a policy decision."""
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    plan_hash: str = Field(..., description="Hash of the CanonicalPlanIR that was evaluated")
    status: Literal["Approved", "Denied"] = Field(...)
    reason: str = Field(..., description="Explanation of the decision")
    evaluated_policies: List[str] = Field(default_factory=list, description="List of policies evaluated")
    
class PolicyDecisionPoint:
    """
    Evaluates Canonical Plans against organizational policies, budgets, and risk tolerances.
    Simulates a declarative policy engine (like OPA).
    """
    
    def __init__(self, tenant_policies: Dict[str, Any] = None):
        self.tenant_policies = tenant_policies or {}

    def evaluate_plan(self, plan: CanonicalPlanIR, identity_context: Dict[str, Any]) -> DecisionRecord:
        """
        Evaluate a given Canonical Plan against the current context.
        """
        plan_hash = plan.compute_hash()
        evaluated = ["IdentityCheck", "BudgetCheck", "RiskAssessment"]
        
        # 1. Identity Check
        if not identity_context.get("user_id"):
            return DecisionRecord(
                plan_hash=plan_hash,
                status="Denied",
                reason="Missing execution identity (user_id)",
                evaluated_policies=evaluated
            )
            
        # 2. Budget Check
        for constraint, limit in plan.budget_constraints.items():
            if limit > self.tenant_policies.get(f"max_{constraint}", float('inf')):
                return DecisionRecord(
                    plan_hash=plan_hash,
                    status="Denied",
                    reason=f"Plan violates budget constraint: {constraint} ({limit} > max allowed)",
                    evaluated_policies=evaluated
                )
                
        # 3. Risk Assessment
        for risk in plan.risk_flags:
            if risk in self.tenant_policies.get("denied_risks", []):
                return DecisionRecord(
                    plan_hash=plan_hash,
                    status="Denied",
                    reason=f"Plan contains forbidden risk flag: {risk}",
                    evaluated_policies=evaluated
                )
                
        # Passed all simulated OPA constraints
        return DecisionRecord(
            plan_hash=plan_hash,
            status="Approved",
            reason="All policies passed",
            evaluated_policies=evaluated
        )
