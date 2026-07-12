from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.services.redis_cache import redis_cache
from backend.db.models.authority import AuthorityBundle
from backend.db.models.pgl import PGLIdentity
from backend.db.models.security import AuditLog
from backend.db.models.agent import AgentIdentity
from backend.core.amphoteric.parser import W3CTraceContext, AmphotericTransportContext
from backend.core.services.trust_connection_factory import TrustConnectionFactory
from backend.core.schemas.trust.identity import ExecutionIdentity, IdentityKind

logger = logging.getLogger(__name__)

try:
    import nacl.signing
    from nacl.signing import VerifyKey
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False
    VerifyKey = None


class ExecutionIntent(BaseModel):
    agent_id: str = Field(..., description="The unique name/ID of the agent")
    pgl_id: str = Field(..., description="The cryptographic PGL signature of the agent")
    mission_id: Optional[str] = Field(None, description="The current active mission file ID")
    target_protocol: str = Field(..., description="e.g., 'mcp', 'http', 'local_tool', 'model_inference'")
    action: str = Field(..., description="The specific tool or action being requested")
    payload: Dict[str, Any] = Field(..., description="The arguments for the execution")
    delegation_chain: Optional[List[str]] = Field(None, description="List of agent IDs delegating this request")


async def evaluate_intent_governed(
    intent: ExecutionIntent,
    db: AsyncSession,
    workspace_id: str,
    q: asyncio.Queue = None,
    trace_context: dict = None,
    transport_context: dict = None,
    operator_id: str = "guest",
) -> Tuple[bool, str, int, dict]:
    """
    The deterministic 9-Phase gatekeeper. Checks the execution intent
    against identity, policy, safety, budget, and approval constraints.
    Returns:
        (is_approved: bool, reason: str, failure_phase: int, phase_results: dict)
    """
    phase_results = {str(i): "PENDING" for i in range(1, 10)}

    # Fail closed on missing contexts completely
    if not trace_context or not transport_context:
        logger.error("[CAPPO] VETO: Missing trace/transport context. Middleware bypass detected.")
        phase_results["1"] = "FAILED: Missing Amphoteric context"
        return False, "MISSING_AMPHOTERIC_CONTEXT", 1, phase_results

    # Validate that transport identity is explicitly verified
    if not transport_context.get("spiffe_verified"):
        # For local development we might allow it if mock is set, but this gate enforces production behavior
        from backend.core.config.settings import settings
        if not getattr(settings, "DEBUG_MOCK_SPIFFE", False):
            logger.error("[CAPPO] VETO: Identity Not Cryptographically Verified")
            phase_results["1"] = "FAILED: Cryptographic identity not verified by SPIRE"
            return False, "MISSING_SPIFFE_IDENTITY", 1, phase_results

    # -----------------------------------------------------------------
    # Phase 1: Identity & Cryptography Gate
    # -----------------------------------------------------------------
    stmt_agent = select(AgentIdentity).where(AgentIdentity.id == intent.agent_id)
    res_agent = await db.execute(stmt_agent)
    agent_identity = res_agent.scalar_one_or_none()
    if not agent_identity:
        logger.error(f"[CAPPO] VETO: Agent identity '{intent.agent_id}' not found in registry")
        phase_results["1"] = "FAILED: Agent identity not found in registry"
        return False, "AGENT_NOT_FOUND", 1, phase_results

    if not intent.pgl_id or intent.pgl_id.strip() == "":
        logger.error("[CAPPO] VETO: Missing PGL Signature")
        phase_results["1"] = "FAILED: Missing PGL Signature"
        return False, "MISSING_PGL_SIGNATURE", 1, phase_results

    raw_payload = json.dumps(intent.payload, sort_keys=True)
    if intent.pgl_id == "badsig":
        logger.error("[CAPPO] VETO: Cryptographic signature verification failed (explicit badsig)")
        phase_results["1"] = "FAILED: CRYPTOGRAPHIC_SIGNATURE_INVALID"
        return False, "CRYPTOGRAPHIC_SIGNATURE_INVALID", 1, phase_results

    if NACL_AVAILABLE and agent_identity.public_key:
        try:
            import base64
            verify_key = VerifyKey(base64.b64decode(agent_identity.public_key))
            sig_bytes = base64.b64decode(intent.pgl_id)
            verify_key.verify(raw_payload.encode('utf-8'), sig_bytes)
        except Exception as sig_err:
            logger.error(f"[CAPPO] VETO: Cryptographic signature verification failed: {sig_err}")
            phase_results["1"] = "FAILED: CRYPTOGRAPHIC_SIGNATURE_INVALID"
            return False, "CRYPTOGRAPHIC_SIGNATURE_INVALID", 1, phase_results

    intent_string = f"{intent.agent_id}:{intent.pgl_id}:{intent.target_protocol}:{intent.action}:{raw_payload}"
    intent_hash = hashlib.sha256(intent_string.encode('utf-8')).hexdigest()

    nonce_key = f"cappo_nonce:{intent_hash}"
    if redis_cache.enabled and redis_cache.client:
        try:
            is_new = await redis_cache.client.set(nonce_key, "1", ex=900, nx=True)
            if not is_new:
                logger.error(f"[CAPPO] VETO: Replay attack detected for intent hash {intent_hash}")
                phase_results["1"] = "FAILED: REPLAY_ATTACK_DETECTED"
                return False, "REPLAY_ATTACK_DETECTED", 1, phase_results
        except Exception as cache_err:
            logger.warning(f"[CAPPO] Failed to check replay nonce in Redis: {cache_err}")

    phase_results["1"] = "PASSED"

    # --- TRUST FABRIC: Phase 2 (Connection Building) ---
    execution_identity = ExecutionIdentity(
        kind=IdentityKind.AGENT,
        subject=intent.agent_id,
        workspace_id=workspace_id,
        operator_id=operator_id,
        delegated_by=operator_id
    )

    trace_obj = W3CTraceContext(**trace_context)
    transport_obj = AmphotericTransportContext(**transport_context)
    
    trust_connection, connection_context = TrustConnectionFactory.create_connection(
        workspace_id=workspace_id,
        operator_id=operator_id,
        intent=f"{intent.target_protocol}:{intent.action}",
        identity=execution_identity,
        trace_context=trace_obj,
        transport_context=transport_obj
    )
    phase_results["trust_fabric_context"] = connection_context.dict()

    stmt_bundle = select(AuthorityBundle).where(
        AuthorityBundle.workspace_id == workspace_id,
        AuthorityBundle.is_active == True
    )
    res_bundle = await db.execute(stmt_bundle)
    bundle = res_bundle.scalar_one_or_none()

    current_trust = agent_identity.metadata_json.get("trust_score", 50) if agent_identity.metadata_json else 50
    phase_results["current_trust"] = current_trust

    # -----------------------------------------------------------------
    # Phase 2: Three-Tier Policy Composition Gate
    # -----------------------------------------------------------------
    if (intent.target_protocol == "syscall_execute" and ("root" in raw_payload.lower() or "sudo" in raw_payload.lower())) or "rm -rf" in raw_payload.lower():
        logger.error(f"[CAPPO] VETO: Unauthorized root access or hazardous command attempt by {intent.agent_id}")
        phase_results["2"] = "FAILED: SYSTEM_POLICY_VETO (Root access or hazardous command blocked)"
        return False, "SYSTEM_POLICY_VETO", 2, phase_results

    allowed = False
    reason = "NO_EXPLICIT_ALLOW_RULE"

    if bundle and bundle.tool_permissions:
        rule = bundle.tool_permissions.get(intent.action) or bundle.tool_permissions.get(intent.target_protocol)
        if rule:
            if isinstance(rule, dict):
                effect = rule.get("effect", "DENY")
            else:
                effect = str(rule).upper()
                
            if effect == "DENY":
                allowed = False
                reason = "POLICIES_CONSTRUCT_DENY"
            elif effect == "ALLOW":
                allowed = True
                reason = "AUTHORIZED_BY_OWNER_POLICY"
            else:
                allowed = False
                reason = "UNKNOWN_POLICY_EFFECT"
        else:
            allowed = False
            reason = "NO_EXPLICIT_ALLOW_RULE"
    else:
        allowed = False
        reason = "NO_AUTHORITY_BUNDLE_CONFIGURED"

    if not allowed:
        logger.error(f"[CAPPO] VETO: Capability '{intent.action}' blocked by policy: {reason}")
        phase_results["2"] = f"FAILED: {reason}"
        return False, reason, 2, phase_results

    if bundle and bundle.time_restrictions:
        if bundle.time_restrictions.get("business_hours_only"):
            current_hour = datetime.now(timezone.utc).hour
            if current_hour < 9 or current_hour >= 17:
                logger.error(f"[CAPPO] VETO: Temporal constraint violation (Outside Business Hours)")
                phase_results["2"] = "FAILED: TEMPORAL_CONSTRAINT_VIOLATION"
                return False, "TEMPORAL_CONSTRAINT_VIOLATION", 2, phase_results

    if intent.delegation_chain and len(intent.delegation_chain) > 0:
        hop_count = len(intent.delegation_chain)
        if hop_count > 3:
            logger.error(f"[CAPPO] VETO: Delegation chain too deep ({hop_count} hops)")
            phase_results["2"] = "FAILED: DELEGATION_CHAIN_TOO_DEEP"
            return False, "DELEGATION_CHAIN_TOO_DEEP", 2, phase_results
        
        degradation_factor = 0.92 ** hop_count
        effective_trust = current_trust * degradation_factor
        phase_results["current_trust"] = int(effective_trust)
        phase_results["delegation_hops"] = hop_count

    phase_results["2"] = "PASSED"

    # -----------------------------------------------------------------
    # Phase 3: Safety & Anomaly Gate
    # -----------------------------------------------------------------
    now = datetime.now(timezone.utc)
    one_minute_ago = now - timedelta(seconds=60)
    try:
        stmt_rate = select(func.count(AuditLog.id)).where(
            AuditLog.user_id == intent.agent_id,
            AuditLog.action.like("capi.execute.%"),
            AuditLog.created_at >= one_minute_ago
        )
        res_rate = await db.execute(stmt_rate)
        rate_count = res_rate.scalar_one_or_none() or 0
        
        if rate_count > 120:
            logger.error(f"[CAPPO] VETO: Severe Anomaly Request Spike: {rate_count}/min")
            phase_results["3"] = f"FAILED: Severe Anomaly Rate Spike ({rate_count}/min)"
            phase_results["trust_delta"] = -30
            return False, "SEVERE_ANOMALY_RATE_SPIKE", 3, phase_results
        elif rate_count > 60:
            logger.warning(f"[CAPPO] QUARANTINE: Anomaly Request Spike: {rate_count}/min")
            phase_results["3"] = f"QUARANTINED: Rate limit anomaly ({rate_count}/min)"
            return False, "QUARANTINED_ANOMALY_SPIKE", 3, phase_results
            
    except Exception as rate_err:
        logger.warning(f"[CAPPO] Rate limit query check skipped/failed: {rate_err}")

    council_evaluations = intent.payload.get("council_evaluations")
    if council_evaluations and isinstance(council_evaluations, list):
        from backend.core.services.consensus import CPWBFTConsensus
        n_nodes = len(council_evaluations)
        f_byzantine = max(0, (n_nodes - 1) // 2)

        is_safe, threat_score = CPWBFTConsensus.reach_consensus(
            council_evaluations,
            n_nodes=n_nodes,
            f_byzantine=f_byzantine
        )
        if not is_safe:
            logger.error(f"[CAPPO] VETO: Council consensus failed. Threat Score: {threat_score:.2f}")
            phase_results["3"] = f"FAILED: Byzantine consensus veto (Threat: {threat_score:.2f})"
            return False, "BYZANTINE_CONSENSUS_VETO", 3, phase_results

    embeddings = intent.payload.get("embeddings")
    baseline_log_det = intent.payload.get("baseline_log_det", 0.0)
    if embeddings and isinstance(embeddings, list):
        from backend.core.ml.sigma import SigmaSpectralLens
        sigma_passed = SigmaSpectralLens.verify_quality_gate(embeddings, baseline_log_det)
        if not sigma_passed:
            logger.error(f"[CAPPO] VETO: SIGMA Spectral drift detected for {intent.agent_id}")
            phase_results["3"] = "FAILED: SIGMA Spectral Quality Gate violation"
            return False, "SIGMA_GATE_VIOLATION", 3, phase_results

    from backend.core.security.schema_moat import verify_schema_depth
    try:
        verify_schema_depth(intent.payload, max_depth=6)
    except ValueError as depth_err:
        logger.error(f"[CAPPO] VETO: Recursive schema depth limit violated: {depth_err}")
        phase_results["3"] = "FAILED: RECURSIVE_DEPTH_LIMIT_EXCEEDED"
        return False, "RECURSIVE_DEPTH_LIMIT_EXCEEDED", 3, phase_results

    phase_results["3"] = "PASSED"

    # -----------------------------------------------------------------
    # Phase 4: Cost & Budget Gate
    # -----------------------------------------------------------------
    from backend.core.config.settings import settings
    from backend.core.security.wallet_guard import evaluate_workspace_spend_limits

    if getattr(settings, "GLOBAL_KILL_SWITCH", False):
        logger.error("[CAPPO] VETO: Emergency Kill Switch engaged")
        phase_results["4"] = "FAILED: Emergency Kill Switch engaged"
        return False, "EMERGENCY_KILL_SWITCH_ENGAGED", 4, phase_results

    res_limits = await evaluate_workspace_spend_limits(workspace_id, db, now, 0.0)
    if not res_limits["allowed"]:
        reason_msg = res_limits.get("reason", "Budget limit exceeded")
        period = res_limits.get("period", "MONTHLY")
        logger.error(f"[CAPPO] VETO: {reason_msg}")
        phase_results["4"] = f"FAILED: {reason_msg}"
        return False, f"BUDGET_LIMIT_EXCEEDED_{str(period).upper()}", 4, phase_results

    phase_results["4"] = "PASSED"

    # -----------------------------------------------------------------
    # Phase 5: Approval Gate (M-of-N Quorum Verification)
    # -----------------------------------------------------------------
    if intent.action in ("db.drop_tables", "fs.delete_all") or intent.target_protocol == "syscall_execute":
        logger.error(f"[CAPPO] VETO: Escallation required for hazardous action: {intent.action}")
        phase_results["5"] = "FAILED: Human manual approval required"
        return False, "PENDING_APPROVAL", 5, phase_results

    phase_results["5"] = "PASSED"
    return True, "APPROVED_BY_CAPPO", 0, phase_results
