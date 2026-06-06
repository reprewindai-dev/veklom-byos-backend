from typing import Dict, List, Optional, Any
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.models.run import VeklomRun, VeklomRunStatus

class VeklomRunStateMachine:
    transitions: Dict[VeklomRunStatus, List[VeklomRunStatus]] = {
        VeklomRunStatus.INTENT_CAPTURED: [VeklomRunStatus.COMPILED, VeklomRunStatus.FAILED],
        VeklomRunStatus.COMPILED: [VeklomRunStatus.CONTEXTUALIZED, VeklomRunStatus.FAILED],
        VeklomRunStatus.CONTEXTUALIZED: [VeklomRunStatus.GOVERNED, VeklomRunStatus.FAILED],
        VeklomRunStatus.GOVERNED: [VeklomRunStatus.HELD, VeklomRunStatus.DENIED, VeklomRunStatus.COMMITTED],
        VeklomRunStatus.HELD: [VeklomRunStatus.APPROVED, VeklomRunStatus.DENIED, VeklomRunStatus.FAILED], # using FAILED for CANCELLED
        VeklomRunStatus.APPROVED: [VeklomRunStatus.COMMITTED],
        VeklomRunStatus.COMMITTED: [VeklomRunStatus.ROUTED, VeklomRunStatus.FAILED],
        VeklomRunStatus.ROUTED: [VeklomRunStatus.EXECUTING, VeklomRunStatus.FAILED],
        VeklomRunStatus.EXECUTING: [VeklomRunStatus.ATTESTED, VeklomRunStatus.FAILED],
        VeklomRunStatus.ATTESTED: [VeklomRunStatus.BILLED, VeklomRunStatus.ROLLED_BACK], # using ROLLED_BACK for ROLLBACK_REQUIRED
        VeklomRunStatus.BILLED: [VeklomRunStatus.SEALED],
        VeklomRunStatus.SEALED: [VeklomRunStatus.ROLLED_BACK], # REVIEWED and REPLAYED are not terminal states typically, but could be added
        VeklomRunStatus.FAILED: [VeklomRunStatus.ROLLED_BACK],
        VeklomRunStatus.ROLLED_BACK: [],
        VeklomRunStatus.DENIED: []
    }

    @classmethod
    def can_transition(cls, current_state: VeklomRunStatus, new_state: VeklomRunStatus) -> bool:
        allowed = cls.transitions.get(current_state, [])
        return new_state in allowed

class RunOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _update_state(self, run: VeklomRun, new_state: VeklomRunStatus) -> VeklomRun:
        if not VeklomRunStateMachine.can_transition(run.status, new_state):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state transition from {run.status.value} to {new_state.value}"
            )
        run.status = new_state
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def create_run(self, workspace_id: str, tenant_id: str, actor_id: str, intent: dict) -> VeklomRun:
        run = VeklomRun(
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            intent=intent,
            status=VeklomRunStatus.INTENT_CAPTURED
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def compile_run(self, run: VeklomRun) -> VeklomRun:
        from backend.services.uacp_v2_compiler import UacpV2Compiler
        compiler = UacpV2Compiler()
        
        compiled_plan = await compiler.compile_intent(run.intent)
        run.v2_plan = compiled_plan
        return await self._update_state(run, VeklomRunStatus.COMPILED)

    async def contextualize_run(self, run: VeklomRun) -> VeklomRun:
        from backend.services.uacp_v3_context import UacpV3Contextualizer
        contextualizer = UacpV3Contextualizer()
        
        # In a real flow, v2_plan must exist before this is called
        v2_plan = run.v2_plan or {}
        v3_context = await contextualizer.contextualize_plan(run.intent, v2_plan)
        
        run.v3_context = v3_context
        return await self._update_state(run, VeklomRunStatus.CONTEXTUALIZED)

    async def govern_run(self, run: VeklomRun) -> VeklomRun:
        from backend.services.uacp_v4_governance import UacpV4Governor
        governor = UacpV4Governor()
        
        # In a real flow, v2_plan and v3_context must exist before this is called
        v2_plan = run.v2_plan or {}
        v3_context = run.v3_context or {}
        
        evaluation = await governor.evaluate_plan(run.intent, v2_plan, v3_context)
        run.v4_decision = evaluation
        
        seked_state = evaluation.get("seked_state")
        if seked_state:
            run.seked_state = seked_state
            
        decision = evaluation.get("decision", "DENIED")
        if decision == "APPROVED":
            return await self._update_state(run, VeklomRunStatus.GOVERNED)
        elif decision == "HELD":
            await self._update_state(run, VeklomRunStatus.GOVERNED)
            return await self._update_state(run, VeklomRunStatus.HELD)
        else:
            await self._update_state(run, VeklomRunStatus.GOVERNED)
            return await self._update_state(run, VeklomRunStatus.DENIED)

    async def commit_run(self, run: VeklomRun, pgl_identity_data: dict) -> VeklomRun:
        # If in HELD, we must go to APPROVED first, but caller should do that.
        if run.status == VeklomRunStatus.HELD:
             await self._update_state(run, VeklomRunStatus.APPROVED)
             
        # Call PGL to commit intent and get pre-execution certificate.
        # Pass the orchestrator's session so the ledger persists for real
        # (no anonymous execution). The client flushes; our _update_state commits.
        from backend.services.pgl_client import PGLClient
        pgl = PGLClient(self.db)
        
        pgl_result = await pgl.commit_intent(
            workspace_id=run.workspace_id,
            actor_id=run.actor_id,
            genome_hash=pgl_identity_data.get("genome_hash", "default_genome"),
            constitution_hash=pgl_identity_data.get("constitution_hash", "default_const"),
            plan_hash=pgl_identity_data.get("plan_hash")
        )
        run.pgl_identity = pgl_result
        return await self._update_state(run, VeklomRunStatus.COMMITTED)

    async def route_run(self, run: VeklomRun, route: dict) -> VeklomRun:
        run.route = route
        return await self._update_state(run, VeklomRunStatus.ROUTED)

    async def execute_run(self, run: VeklomRun) -> VeklomRun:
        return await self._update_state(run, VeklomRunStatus.EXECUTING)

    async def attest_run(self, run: VeklomRun, evidence: dict, output_hash: str, outcome_hash: str) -> VeklomRun:
        from backend.services.pgl_client import PGLClient
        pgl = PGLClient(self.db)
        
        pre_cert = run.pgl_identity.get("pre_execution_certificate_id") if run.pgl_identity else None
        if pre_cert:
            pgl_result = await pgl.attest_outcome(
                pre_execution_certificate_id=pre_cert,
                output_hash=output_hash,
                outcome_hash=outcome_hash,
                workspace_id=run.workspace_id,
                actor_id=run.actor_id
            )
            # Merge post-execution PGL details into pgl_identity
            run.pgl_identity.update(pgl_result)
            
        run.evidence = evidence
        return await self._update_state(run, VeklomRunStatus.ATTESTED)

    async def debit_run(self, run: VeklomRun, budget: dict) -> VeklomRun:
        run.budget = budget
        return await self._update_state(run, VeklomRunStatus.BILLED)

    async def seal_run(self, run: VeklomRun) -> VeklomRun:
        # Final sealing logic
        return await self._update_state(run, VeklomRunStatus.SEALED)

    async def fail_run(self, run: VeklomRun, error_details: dict) -> VeklomRun:
        # Optional: append to evidence
        if not run.evidence:
            run.evidence = {}
        run.evidence["error"] = error_details
        return await self._update_state(run, VeklomRunStatus.FAILED)

    async def rollback_run(self, run: VeklomRun, reason: str = "Operator aborted") -> VeklomRun:
        from backend.services.pgl_client import PGLClient
        pgl = PGLClient(self.db)
        
        post_cert = run.pgl_identity.get("post_execution_certificate_id") if run.pgl_identity else None
        if post_cert:
            rb_result = await pgl.register_rollback(
                post_execution_certificate_id=post_cert,
                reason=reason
            )
            run.pgl_identity.update(rb_result)
            
        return await self._update_state(run, VeklomRunStatus.ROLLED_BACK)
