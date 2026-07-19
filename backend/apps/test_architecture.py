import asyncio
import json

from backend.apps.gpc.canonical_plan import CanonicalPlanIR, PlanStep, CapabilityRequirement
from backend.apps.policy.pdp_engine import PolicyDecisionPoint
from backend.apps.orchestration.workflow_orchestrator import DurableWorkflowEngine
from backend.apps.evidence.evidence_pipeline import DSSEAttestationBuilder

async def main():
    print("1. Creating Canonical Plan IR...")
    plan = CanonicalPlanIR(
        tenant_id="tenant-123",
        steps=[
            PlanStep(
                action="call_llm",
                parameters={"prompt": "Summarize user feedback"},
                capabilities_required=[
                    CapabilityRequirement(name="openai-api", context={"model": "gpt-4o"})
                ]
            )
        ],
        budget_constraints={"tokens": 1000},
        risk_flags=["PII_ACCESS"]
    )
    
    print(f"Plan Hash: {plan.compute_hash()}")
    
    print("\n2. Evaluating Plan via Policy Decision Point (PDP)...")
    # Simulate a PDP where PII_ACCESS is allowed, but token limit must be <= 5000
    pdp = PolicyDecisionPoint(tenant_policies={
        "max_tokens": 5000,
        "denied_risks": ["UNAUTHORIZED_MUTATION"] 
    })
    
    identity_context = {"user_id": "usr_999"}
    decision = pdp.evaluate_plan(plan, identity_context)
    
    print(f"Decision Status: {decision.status}")
    print(f"Decision Reason: {decision.reason}")
    
    if decision.status != "Approved":
        print("Execution Denied.")
        return

    print("\n3. Orchestrating Durable Workflow Execution...")
    engine = DurableWorkflowEngine()
    workflow_id = engine.submit_plan(plan, decision)
    
    state = await engine.run_workflow(workflow_id, plan)
    print(f"Workflow Final Status: {state.status}")
    
    print("\n4. Building DSSE Attestation (Evidence Pipeline)...")
    builder = DSSEAttestationBuilder()
    attestation = builder.build_workflow_attestation(plan, decision, state)
    
    print("DSSE Envelope Built.")
    print(json.dumps(attestation.model_dump(mode='json'), indent=2))
    
if __name__ == "__main__":
    asyncio.run(main())
