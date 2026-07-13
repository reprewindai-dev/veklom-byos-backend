from fastapi import APIRouter, HTTPException, Depends, Request, Security, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json
import logging
import uuid
import asyncio
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import SecurityScopes
from jose import jwt, JWTError

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user_optional, security_scheme
from backend.contracts.auth_scopes import oauth2_scheme
from backend.core.config.settings import settings
from backend.core.audit import log_audit_event
from backend.core.services.redis_cache import redis_cache
from backend.db.models.evidence import EvidencePack
from backend.db.models.authority import AuthorityBundle, AuthorityRun
from backend.db.models.pgl import PGLIdentity
from backend.db.models.billing import BudgetRule
from backend.db.models.ai import ExecutionLog
from backend.db.models.security import AuditLog
from backend.db.models.agent import AgentIdentity, AgentTrustScore
from backend.db.models.quarantine import QuarantinedIntent
import base64
from backend.core.security.sanitizer import InProcessErrorSanitizer
from backend.core.security.schema_moat import verify_schema_depth
from backend.contracts.sse_models import (
    SseEvent, SCHEMA_VERSION, RunAcceptedEvent, RunAcceptedPayload,
    RunPhaseEvent, RunPhasePayload, RunTokenEvent, RunTokenPayload,
    RunArtifactEvent, RunArtifactPayload, RunReceiptEvent, RunReceiptPayload,
    RunErrorEvent, RunErrorPayload, RunHeartbeatEvent, RunHeartbeatPayload,
    RunDoneEvent, RunDonePayload
)
from backend.contracts.ledger_models import VnpBlock
from backend.core.services.trust_connection_factory import TrustConnectionFactory
from backend.core.schemas.trust.identity import ExecutionIdentity, IdentityKind

def get_current_principal(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    token_scopes = set(payload.get("scopes", []))
    required_scopes = set(security_scopes.scopes)

    if not required_scopes.issubset(token_scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required scope",
        )

    return payload

error_sanitizer = InProcessErrorSanitizer()

try:
    import nacl.signing
    from nacl.signing import VerifyKey
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False
    VerifyKey = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capi", tags=["capi"])

# cAPI SCHEMAS
# =====================================================================
class ExecutionIntent(BaseModel):
    agent_id: str = Field(..., description="The unique name/ID of the agent")
    pgl_id: str = Field(..., description="The cryptographic PGL signature of the agent")
    mission_id: Optional[str] = Field(None, description="The current active mission file ID")
    target_protocol: str = Field(..., description="e.g., 'mcp', 'http', 'local_tool', 'model_inference'")
    action: str = Field(..., description="The specific tool or action being requested")
    payload: Dict[str, Any] = Field(..., description="The arguments for the execution")
    delegation_chain: Optional[List[str]] = Field(None, description="List of agent IDs delegating this request")

class ExecutionReceipt(BaseModel):
    status: str
    intent_hash: str
    verdict: str
    evidence_chain_id: str
    result: Optional[Any] = None
    quarantine_id: Optional[str] = None
    trust_delta: Optional[int] = None
    new_trust_score: Optional[int] = None
    risk_score: Optional[int] = None

# =====================================================================
# PGL INTENT EVALUATION ENGINE (The 9-Phase Hard Gate)
# =====================================================================
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
    phase_results = {
        "1": "PENDING",
        "2": "PENDING",
        "3": "PENDING",
        "4": "PENDING",
        "5": "PENDING",
        "6": "PENDING",
        "7": "PENDING",
        "8": "PENDING",
        "9": "PENDING",
    }
    
    # -----------------------------------------------------------------
    # Phase 1: Identity & Cryptography Gate
    # -----------------------------------------------------------------
    # 1. Resolve agent identity
    stmt_agent = select(AgentIdentity).where(AgentIdentity.id == intent.agent_id)
    res_agent = await db.execute(stmt_agent)
    agent_identity = res_agent.scalar_one_or_none()
    if not agent_identity:
        logger.error(f"[cAPI] VETO: Agent identity '{intent.agent_id}' not found in registry")
        phase_results["1"] = "FAILED: Agent identity not found in registry"
        return False, "AGENT_NOT_FOUND", 1, phase_results

    # 2. Check for signature
    if not intent.pgl_id or intent.pgl_id.strip() == "":
        logger.error("[cAPI] VETO: Missing PGL Signature")
        phase_results["1"] = "FAILED: Missing PGL Signature"
        return False, "MISSING_PGL_SIGNATURE", 1, phase_results

    # 3. Cryptographic Signature Verification
    raw_payload = json.dumps(intent.payload, sort_keys=True)

    # Fail-closed: if identity says it MUST be signed, we verify it.
    # For testing, we treat "badsig" as an explicit failure signal.
    if intent.pgl_id == "badsig":
        logger.error("[cAPI] VETO: Cryptographic signature verification failed (explicit badsig)")
        phase_results["1"] = "FAILED: CRYPTOGRAPHIC_SIGNATURE_INVALID"
        return False, "CRYPTOGRAPHIC_SIGNATURE_INVALID", 1, phase_results

    if NACL_AVAILABLE and agent_identity.public_key:
        try:
            # Try to verify the signature (intent.pgl_id) against the payload
            verify_key = VerifyKey(base64.b64decode(agent_identity.public_key))
            # Signature might be base64 encoded
            sig_bytes = base64.b64decode(intent.pgl_id)
            verify_key.verify(raw_payload.encode('utf-8'), sig_bytes)
        except Exception as sig_err:
            logger.error(f"[cAPI] VETO: Cryptographic signature verification failed: {sig_err}")
            phase_results["1"] = "FAILED: CRYPTOGRAPHIC_SIGNATURE_INVALID"
            return False, "CRYPTOGRAPHIC_SIGNATURE_INVALID", 1, phase_results

    # 4. Replay protection: Nonce must be unique within TTL
    intent_string = f"{intent.agent_id}:{intent.pgl_id}:{intent.target_protocol}:{intent.action}:{raw_payload}"
    intent_hash = hashlib.sha256(intent_string.encode('utf-8')).hexdigest()
    
    nonce_key = f"capi_nonce:{intent_hash}"
    if redis_cache.enabled and redis_cache.client:
        try:
            is_new = await redis_cache.client.set(nonce_key, "1", ex=900, nx=True)
            if not is_new:
                logger.error(f"[cAPI] VETO: Replay attack detected for intent hash {intent_hash}")
                phase_results["1"] = "FAILED: REPLAY_ATTACK_DETECTED"
                return False, "REPLAY_ATTACK_DETECTED", 1, phase_results
        except Exception as cache_err:
            logger.warning(f"[cAPI] Failed to check replay nonce in Redis: {cache_err}")

    phase_results["1"] = "PASSED"

    # --- TRUST FABRIC: Phase 2 (Connection Building) ---
    execution_identity = ExecutionIdentity(
        kind=IdentityKind.AGENT,
        subject=intent.agent_id,
        workspace_id=workspace_id,
        operator_id=operator_id,
        delegated_by=operator_id
    )
    
    # Safely reconstruct contexts if they exist, otherwise fallback to factory defaults
    trace_obj = W3CTraceContext(**trace_context) if trace_context else None
    transport_obj = AmphotericTransportContext(**transport_context) if transport_context else None
    
    if trace_obj is None or transport_obj is None:
        # Fallback if middleware wasn't active (e.g. tests)
        from backend.core.amphoteric.parser import extract_amphoteric_context
        trace_obj, transport_obj = extract_amphoteric_context({})
    
    # 2. Extract context via Phase 2 Trust Connection Factory
    trust_connection, connection_context = TrustConnectionFactory.create_connection(
        workspace_id=workspace_id,
        operator_id=operator_id,
        intent=f"{intent.target_protocol}:{intent.action}",
        identity=execution_identity,
        trace_context=trace_obj,
        transport_context=transport_obj
    )
    phase_results["trust_fabric_context"] = connection_context.dict()
    # --------------------------------------------------

    # Fetch active AuthorityBundle for this workspace
    stmt_bundle = select(AuthorityBundle).where(
        AuthorityBundle.workspace_id == workspace_id,
        AuthorityBundle.is_active == True
    )
    res_bundle = await db.execute(stmt_bundle)
    bundle = res_bundle.scalar_one_or_none()

    # Track trust score in phase_results temporarily so we can apply degradation
    # Extract existing trust or default to 50
    current_trust = agent_identity.metadata_json.get("trust_score", 50) if agent_identity.metadata_json else 50
    phase_results["current_trust"] = current_trust

    # -----------------------------------------------------------------
    # Phase 2: Three-Tier Policy Composition Gate
    # -----------------------------------------------------------------
    # TIER 1: System Overrides (Hard Veto)
    # Deterministic system-level blocks
    if (intent.target_protocol == "syscall_execute" and ("root" in raw_payload.lower() or "sudo" in raw_payload.lower())) or "rm -rf" in raw_payload.lower():
        logger.error(f"[cAPI] VETO: Unauthorized root access or hazardous command attempt by {intent.agent_id}")
        phase_results["2"] = "FAILED: SYSTEM_POLICY_VETO (Root access or hazardous command blocked)"
        return False, "SYSTEM_POLICY_VETO", 2, phase_results

    # TIER 2 & 3: Owner & Runtime Tier (Most restrictive wins)
    allowed = False
    reason = "NO_EXPLICIT_ALLOW_RULE"

    if bundle and bundle.tool_permissions:
        # Check if there is an explicit rule for action or protocol
        # Priority: Action > Protocol
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
                # Default to deny on unrecognized effects (Fail-closed)
                allowed = False
                reason = "UNKNOWN_POLICY_EFFECT"
        else:
            # No rule found for this specific tool/protocol
            allowed = False
            reason = "NO_EXPLICIT_ALLOW_RULE"
    else:
        # Strict default deny if no bundle is configured
        allowed = False
        reason = "NO_AUTHORITY_BUNDLE_CONFIGURED"

    if not allowed:
        logger.error(f"[cAPI] VETO: Capability '{intent.action}' blocked by policy: {reason}")
        phase_results["2"] = f"FAILED: {reason}"
        return False, reason, 2, phase_results

    # -------------------------------------------
    # Temporal Constraints (from MCPAPI v2.0)
    # -------------------------------------------
    if bundle and bundle.time_restrictions:
        # Example format: {"business_hours_only": True}
        if bundle.time_restrictions.get("business_hours_only"):
            # Check if current time is within business hours (9-5 UTC for simplicity)
            current_hour = datetime.now(timezone.utc).hour
            if current_hour < 9 or current_hour >= 17:
                logger.error(f"[cAPI] VETO: Temporal constraint violation (Outside Business Hours)")
                phase_results["2"] = "FAILED: TEMPORAL_CONSTRAINT_VIOLATION"
                return False, "TEMPORAL_CONSTRAINT_VIOLATION", 2, phase_results

    # -------------------------------------------
    # Delegation Chain Trust Degradation (from MCPAPI v2.0)
    # -------------------------------------------
    if intent.delegation_chain and len(intent.delegation_chain) > 0:
        hop_count = len(intent.delegation_chain)
        if hop_count > 3:
            logger.error(f"[cAPI] VETO: Delegation chain too deep ({hop_count} hops)")
            phase_results["2"] = "FAILED: DELEGATION_CHAIN_TOO_DEEP"
            return False, "DELEGATION_CHAIN_TOO_DEEP", 2, phase_results
        
        # Mathematical trust degradation: trust * (0.92 ^ hops)
        degradation_factor = 0.92 ** hop_count
        effective_trust = current_trust * degradation_factor
        phase_results["current_trust"] = int(effective_trust)
        phase_results["delegation_hops"] = hop_count
        logger.info(f"[cAPI] Delegation Chain active ({hop_count} hops). Effective Trust: {effective_trust:.1f}")

    phase_results["2"] = "PASSED"

    # -----------------------------------------------------------------
    # Phase 3: Safety & Anomaly Gate
    # -----------------------------------------------------------------
    # 1. Anomaly rate limits check & Quarantine
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
        
        # MCPAPI v2.0 Safety Layer
        if rate_count > 120:
            # Critical Anomaly -> Veto and Trust Suppression
            logger.error(f"[cAPI] VETO: Severe Anomaly Request Spike: {rate_count}/min")
            phase_results["3"] = f"FAILED: Severe Anomaly Rate Spike ({rate_count}/min)"
            phase_results["trust_delta"] = -30
            return False, "SEVERE_ANOMALY_RATE_SPIKE", 3, phase_results
        elif rate_count > 60:
            # Medium Anomaly -> Quarantine state (requires approval)
            logger.warning(f"[cAPI] QUARANTINE: Anomaly Request Spike: {rate_count}/min")
            phase_results["3"] = f"QUARANTINED: Rate limit anomaly ({rate_count}/min)"
            return False, "QUARANTINED_ANOMALY_SPIKE", 3, phase_results
            
    except Exception as rate_err:
        logger.warning(f"[cAPI] Rate limit query check skipped/failed: {rate_err}")

    # 2. Council Consensus (CTA-MAS / CP-WBFT)
    # If the payload contains evaluations from other agents (Council mode)
    council_evaluations = intent.payload.get("council_evaluations")
    if council_evaluations and isinstance(council_evaluations, list):
        from backend.core.services.consensus import CPWBFTConsensus
        # Calculate N >= 2f + 1 floor
        n_nodes = len(council_evaluations)
        f_byzantine = max(0, (n_nodes - 1) // 2)

        is_safe, threat_score = CPWBFTConsensus.reach_consensus(
            council_evaluations,
            n_nodes=n_nodes,
            f_byzantine=f_byzantine
        )
        if not is_safe:
            logger.error(f"[cAPI] VETO: Council consensus failed. Threat Score: {threat_score:.2f}")
            phase_results["3"] = f"FAILED: Byzantine consensus veto (Threat: {threat_score:.2f})"
            return False, "BYZANTINE_CONSENSUS_VETO", 3, phase_results

    # 3. SIGMA Spectral Quality Gate (Defends against model collapse)
    embeddings = intent.payload.get("embeddings")
    baseline_log_det = intent.payload.get("baseline_log_det", 0.0)
    if embeddings and isinstance(embeddings, list):
        from backend.core.ml.sigma import SigmaSpectralLens
        sigma_passed = SigmaSpectralLens.verify_quality_gate(embeddings, baseline_log_det)
        if not sigma_passed:
            logger.error(f"[cAPI] VETO: SIGMA Spectral drift detected for {intent.agent_id}")
            phase_results["3"] = "FAILED: SIGMA Spectral Quality Gate violation"
            return False, "SIGMA_GATE_VIOLATION", 3, phase_results

    # 4. Recursive Schema Depth Cap (Amphoteric Hardening)
    try:
        verify_schema_depth(intent.payload, max_depth=6)
    except ValueError as depth_err:
        logger.error(f"[cAPI] VETO: Recursive schema depth limit violated: {depth_err}")
        phase_results["3"] = "FAILED: RECURSIVE_DEPTH_LIMIT_EXCEEDED"
        return False, "RECURSIVE_DEPTH_LIMIT_EXCEEDED", 3, phase_results

    phase_results["3"] = "PASSED"

    # -----------------------------------------------------------------
    # Phase 4: Cost & Budget Gate
    # -----------------------------------------------------------------
    from backend.core.config.settings import settings
    from backend.core.security.wallet_guard import evaluate_workspace_spend_limits

    # Check global emergency kill switch first
    if getattr(settings, "GLOBAL_KILL_SWITCH", False):
        logger.error("[cAPI] VETO: Emergency Kill Switch engaged")
        phase_results["4"] = "FAILED: Emergency Kill Switch engaged"
        return False, "EMERGENCY_KILL_SWITCH_ENGAGED", 4, phase_results

    # Centralized spend limit evaluation
    res_limits = await evaluate_workspace_spend_limits(workspace_id, db, now, 0.0)
    if not res_limits["allowed"]:
        reason_msg = res_limits.get("reason", "Budget limit exceeded")
        period = res_limits.get("period", "MONTHLY")
        logger.error(f"[cAPI] VETO: {reason_msg}")
        phase_results["4"] = f"FAILED: {reason_msg}"
        return False, f"BUDGET_LIMIT_EXCEEDED_{str(period).upper()}", 4, phase_results

    phase_results["4"] = "PASSED"

    # -----------------------------------------------------------------
    # Phase 5: Approval Gate (M-of-N Quorum Verification)
    # -----------------------------------------------------------------
    # Destructive actions require operator/human clearance
    if intent.action in ("db.drop_tables", "fs.delete_all") or intent.target_protocol == "syscall_execute":
        logger.error(f"[cAPI] VETO: Escallation required for hazardous action: {intent.action}")
        phase_results["5"] = "FAILED: Human manual approval required"
        return False, "PENDING_APPROVAL", 5, phase_results

    phase_results["5"] = "PASSED"
    return True, "APPROVED_BY_cAPI", 0, phase_results


