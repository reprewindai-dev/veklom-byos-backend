import logging
import asyncio
from typing import Dict, Any, Literal, List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime

from backend.apps.gpc.canonical_plan import CanonicalPlanIR, PlanStep
from backend.apps.policy.pdp_engine import DecisionRecord

logger = logging.getLogger(__name__)

class StepExecutionState(BaseModel):
    step_id: str
    status: Literal["Pending", "Running", "Success", "Failed"] = "Pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0

class WorkflowState(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str
    status: Literal["Pending", "Running", "Success", "Failed", "Denied"] = "Pending"
    steps_state: Dict[str, StepExecutionState] = Field(default_factory=dict)
    decision_record: Optional[DecisionRecord] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DurableWorkflowEngine:
    """
    Simulates a durable execution engine like Temporal.
    Guarantees that a plan is executed deterministically according to policy.
    """
    
    def __init__(self):
        # In a real system, this would be a durable datastore or Temporal server
        self._state_store: Dict[str, WorkflowState] = {}
        
    def submit_plan(self, plan: CanonicalPlanIR, decision: DecisionRecord) -> str:
        """Submit an evaluated plan for execution."""
        workflow_id = str(uuid4())
        
        state = WorkflowState(
            workflow_id=workflow_id,
            plan_id=plan.plan_id,
            decision_record=decision
        )
        
        if decision.status == "Denied":
            state.status = "Denied"
        else:
            for step in plan.steps:
                state.steps_state[step.step_id] = StepExecutionState(step_id=step.step_id)
                
        self._state_store[workflow_id] = state
        return workflow_id

    async def execute_step(self, step: PlanStep, idempotency_key: str) -> Dict[str, Any]:
        """
        Simulate executing a single step idempotently.
        In reality, this invokes the Execution Adapters.
        """
        logger.info(f"Executing step {step.action} with key {idempotency_key}")
        # Simulate work
        await asyncio.sleep(0.1)
        return {"simulated_result": f"Executed {step.action}"}

    async def run_workflow(self, workflow_id: str, plan: CanonicalPlanIR) -> WorkflowState:
        """Run the workflow to completion, maintaining durable state."""
        state = self._state_store.get(workflow_id)
        if not state:
            raise ValueError("Workflow not found")
            
        if state.status in ["Denied", "Success"]:
            return state # Idempotent return

        state.status = "Running"
        
        try:
            for step in plan.steps:
                step_state = state.steps_state[step.step_id]
                
                # Idempotency check: don't rerun successful steps
                if step_state.status == "Success":
                    continue
                    
                step_state.status = "Running"
                step_state.started_at = datetime.utcnow()
                
                # Execute with simulated idempotency key
                idem_key = f"{workflow_id}-{step.step_id}-{step_state.retries}"
                try:
                    result = await self.execute_step(step, idempotency_key=idem_key)
                    step_state.status = "Success"
                    step_state.result = result
                except Exception as e:
                    step_state.status = "Failed"
                    step_state.error = str(e)
                    state.status = "Failed"
                    return state
                finally:
                    step_state.completed_at = datetime.utcnow()
                    
            state.status = "Success"
        except Exception as e:
            state.status = "Failed"
            logger.error(f"Workflow {workflow_id} failed: {e}")
            
        return state
