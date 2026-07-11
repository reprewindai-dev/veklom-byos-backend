from typing import Dict, List, Optional, Any, Set
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.models.run import VeklomRun, VeklomRunStatus

class StateTransitionManager:
    VALID_TRANSITIONS: Dict[VeklomRunStatus, Set[VeklomRunStatus]] = {
        VeklomRunStatus.INTENT_CAPTURED: {VeklomRunStatus.COMPILED, VeklomRunStatus.FAILED},
        VeklomRunStatus.COMPILED: {VeklomRunStatus.CONTEXTUALIZED, VeklomRunStatus.FAILED},
        VeklomRunStatus.CONTEXTUALIZED: {VeklomRunStatus.GOVERNED, VeklomRunStatus.FAILED},
        VeklomRunStatus.GOVERNED: {VeklomRunStatus.HELD, VeklomRunStatus.DENIED, VeklomRunStatus.COMMITTED},
        VeklomRunStatus.HELD: {VeklomRunStatus.APPROVED, VeklomRunStatus.DENIED, VeklomRunStatus.FAILED}, # using FAILED for CANCELLED
        VeklomRunStatus.APPROVED: {VeklomRunStatus.COMMITTED},
        VeklomRunStatus.COMMITTED: {VeklomRunStatus.ROUTED, VeklomRunStatus.FAILED},
        VeklomRunStatus.ROUTED: {VeklomRunStatus.EXECUTING, VeklomRunStatus.FAILED},
        VeklomRunStatus.EXECUTING: {VeklomRunStatus.ATTESTED, VeklomRunStatus.FAILED},
        VeklomRunStatus.ATTESTED: {VeklomRunStatus.BILLED, VeklomRunStatus.ROLLED_BACK}, # using ROLLED_BACK for ROLLBACK_REQUIRED
        VeklomRunStatus.BILLED: {VeklomRunStatus.SEALED},
        VeklomRunStatus.SEALED: {VeklomRunStatus.ROLLED_BACK}, # REVIEWED and REPLAYED are not terminal states typically, but could be added
        VeklomRunStatus.FAILED: {VeklomRunStatus.ROLLED_BACK},
        VeklomRunStatus.ROLLED_BACK: set(),
        VeklomRunStatus.DENIED: set()
    }

    @classmethod
    def can_transition(cls, current_state: VeklomRunStatus, new_state: VeklomRunStatus) -> bool:
        allowed = cls.VALID_TRANSITIONS.get(current_state, set())
        return new_state in allowed

class RunOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _update_state(self, run: VeklomRun, new_state: VeklomRunStatus) -> VeklomRun:
        if not StateTransitionManager.can_transition(run.status, new_state):
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

    async def commit_run(self, run: VeklomRun, pgl_identity_data: dict | None = None) -> VeklomRun:
        """
        Commit a run to execution — this is where the PGL hard gate fires.

        Every actor_id on a VeklomRun MUST have a verified gnomledger identity
        before the run can transition to COMMITTED. If the actor has no
        PGL identity, is quarantined, or the birth certificate chain is broken,
        the run is DENIED — not just failed.

        pgl_identity_data is kept for API compatibility but is IGNORED —
        identity is always resolved from gnomledger, never trusted from the caller.
        """
        from backend.core.services.pgl_identity_gate import (
            PGLIdentityGate,
            PGLIdentityError,
            AgentKind,
        )

        # If in HELD, go to APPROVED first
        if run.status == VeklomRunStatus.HELD:
            await self._update_state(run, VeklomRunStatus.APPROVED)

        # ── PGL HARD GATE — resolve actor identity from gnomledger ───────────
        # actor_id comes from the JWT (extracted by ZeroTrustMiddleware), never
        # from the request body. We resolve through the birth certificate chain.
        actor_id = run.actor_id or "unknown"
        try:
            pgl_ctx = await PGLIdentityGate.require(
                db       = self.db,
                actor_id = actor_id,
                action   = "commit_run",
                payload  = {
                    "run_id":       str(run.id) if hasattr(run, "id") else "unknown",
                    "workspace_id": run.workspace_id,
                    "tenant_id":    run.tenant_id,
                    "intent":       run.intent or {},
                },
                kind = AgentKind.SYSTEM
                       if actor_id in ("orchestrator::veklom-runtime",)
                       else AgentKind.REGISTERED,
                scope = "run:commit",
            )
        except PGLIdentityError as exc:
            # PGL gate blocked the run — hard deny, not fail
            import logging
            logging.getLogger(__name__).error(
                f"[Orchestrator] PGL gate blocked commit for actor='{actor_id}': {exc}"
            )
            # Transition to DENIED state with the reason
            if not run.evidence:
                run.evidence = {}
            run.evidence["pgl_denied"] = str(exc)
            run.evidence["pgl_actor_id"] = actor_id
            return await self._update_state(run, VeklomRunStatus.DENIED)
        # ─────────────────────────────────────────────────────────────────────

        # Store the PGL context in pgl_identity for attest_run / rollback_run
        run.pgl_identity = {
            "pre_execution_certificate_id": pgl_ctx.pre_execution_cert_id,
            "pgl_identity_id":              pgl_ctx.pgl_identity_id,
            "genome_hash":                  pgl_ctx.genome_hash,
            "constitution_hash":            pgl_ctx.constitution_hash,
            "intent_hash":                  pgl_ctx.intent_hash,
            "birth_cert_id":               pgl_ctx.birth_cert_id,
            "cleared_at":                   pgl_ctx.cleared_at.isoformat(),
        }
        
        run = await self._update_state(run, VeklomRunStatus.COMMITTED)
        
        # MINT EXECUTION IDENTITY (CAPPO Blueprint)
        run = await self.mint_execution_identity(run)
        
        return run

    async def mint_execution_identity(self, run: VeklomRun) -> VeklomRun:
        """
        Mints the ExecutionIdentityV1 payload required for governed execution.
        Must be called between COMMITTED and ROUTED.
        """
        import json
        import hashlib
        import uuid
        from datetime import datetime, timedelta, timezone
        
        pgl_identity = run.pgl_identity or {}
        seked_state = run.seked_state or {}
        
        # Assemble fields
        execution_identity = {
            "id": str(uuid.uuid4()),
            "run_id": run.run_id,
            "workspace_id": run.workspace_id,
            "pre_execution_certificate_id": pgl_identity.get("pre_execution_certificate_id"),
            "genome_hash": pgl_identity.get("genome_hash"),
            "constitution_hash": pgl_identity.get("constitution_hash"),
            "plan_hash": pgl_identity.get("plan_hash"),
            "seked_directive": seked_state,
            "scope": "run:commit",
            "budget": run.budget or {},
            "delegation_depth": 0,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Compute canonical hash
        raw = json.dumps(execution_identity, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        computed_hash = hashlib.sha256(raw).hexdigest()
        execution_identity["hash"] = computed_hash
        execution_identity["signature"] = "mock_signature_from_configured_signing_key"
        
        # Store on run
        run.execution_identity = execution_identity
        
        # Persist to execution_identities table
        from backend.db.models.pgl import ExecutionIdentity
        ei_record = ExecutionIdentity(
            id=execution_identity["id"],
            run_id=execution_identity["run_id"],
            workspace_id=execution_identity["workspace_id"],
            pre_execution_certificate_id=execution_identity["pre_execution_certificate_id"],
            genome_hash=execution_identity["genome_hash"],
            constitution_hash=execution_identity["constitution_hash"],
            plan_hash=execution_identity["plan_hash"],
            seked_directive=execution_identity["seked_directive"],
            scope=execution_identity["scope"],
            budget=execution_identity["budget"],
            delegation_depth=execution_identity["delegation_depth"],
            hash=execution_identity["hash"],
            signature=execution_identity["signature"]
        )
        self.db.add(ei_record)
        await self.db.commit()
        
        return run

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
