"""Sovereign API endpoints for Veklom Mission Lock / Policy Inertia behavior governance."""

import enum
import uuid
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, Header, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.services.mission_lock_service import (
    MissionLockService, MissionLockAgent, MissionDNA, MissionPath, TeamCoordinator
)
from backend.db.models.mission_lock import (
    TenantRole, EpisodeTelemetry, RecoveryEvent, DNAAudit, MissionLockAgentState, TeamState, AgentActionTrace
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mission-lock", tags=["Mission Lock Governance"])


# ============================================================================
# PYDANTIC SCHEMAS (Pydantic v2 aligned)
# ============================================================================

class AgentRole(str, enum.Enum):
    ROUTER = "router"
    PLANNER = "planner"
    VERIFIER = "verifier"
    EXECUTOR = "executor"
    WATCHDOG = "watchdog"
    CUSTOM = "custom"


class MissionDNABase(BaseModel):
    role: str
    dominance: float = Field(0.85, ge=0.5, le=1.0)
    plasticity: float = Field(0.01, ge=0.001, le=0.05)
    base_learning_rate: float = Field(0.08, gt=0)
    epsilon: float = Field(0.02, ge=0.001, le=0.2)
    mission_bonus: float = 1.0
    off_path_penalty: float = 0.15
    coordination_weight: float = Field(0.5, ge=0, le=1.0)
    safety_weight: float = 1.0
    cue_boost: float = 0.10
    min_dominance: float = 0.50
    max_epsilon: float = 0.15
    max_plasticity: float = 0.05
    allowed_actions: Optional[List[str]] = None
    forbidden_actions: List[str] = Field(default_factory=list)

    @field_validator("dominance")
    @classmethod
    def validate_dominance(cls, v):
        if not (0.5 <= v <= 1.0):
            raise ValueError("dominance must be between 0.5 and 1.0")
        return v

    @field_validator("plasticity")
    @classmethod
    def validate_plasticity(cls, v):
        if not (0.001 <= v <= 0.05):
            raise ValueError("plasticity must be between 0.001 and 0.05")
        return v


class MissionDNACreate(MissionDNABase):
    agent_id: str


class MissionDNAUpdate(BaseModel):
    dominance: Optional[float] = None
    plasticity: Optional[float] = None
    base_learning_rate: Optional[float] = None
    epsilon: Optional[float] = None
    mission_bonus: Optional[float] = None
    off_path_penalty: Optional[float] = None
    coordination_weight: Optional[float] = None
    safety_weight: Optional[float] = None
    cue_boost: Optional[float] = None
    forbidden_actions: Optional[List[str]] = None
    reason: Optional[str] = None
    changed_by: Optional[str] = None


class MissionDNAResponse(MissionDNABase):
    id: str
    agent_id: str
    tenant_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    locked: bool
    version: int

    model_config = {"from_attributes": True}


class AgentMissionBase(BaseModel):
    mission_name: str
    preferred_transitions: Dict[str, str]
    description: Optional[str] = None


class AgentMissionCreate(AgentMissionBase):
    agent_id: str


class AgentMissionResponse(AgentMissionBase):
    id: str
    agent_id: str
    tenant_id: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


class AgentStateResponse(BaseModel):
    id: str
    agent_id: str
    current_dominance: float
    current_plasticity: float
    current_epsilon: float
    target_return: Optional[float]
    last_episode_return: float
    moving_avg_return: float
    path_conformance: float
    steps_since_recovery: int
    safety_violations: int
    last_action: Optional[str]
    last_state: Optional[str]
    last_update: datetime

    model_config = {"from_attributes": True}


class EpisodeTelemetryCreate(BaseModel):
    agent_id: str
    episode_num: int
    episode_return: float
    path_actions: int = 0
    off_path_actions: int = 0
    path_conformance: float = 0.0
    safety_events: int = 0
    steps: int = 0
    recovery_triggered: bool = False
    dominance_at_episode: float
    epsilon_at_episode: float
    plasticity_at_episode: float


class EpisodeTelemetryResponse(EpisodeTelemetryCreate):
    id: str
    timestamp: datetime
    tenant_id: Optional[str]

    model_config = {"from_attributes": True}


class TeamStateBase(BaseModel):
    team_id: str
    phase: Optional[str] = None
    alerts: List[str] = Field(default_factory=list)
    shared_goal_progress: float = 0.0
    last_joint_actions: Optional[Dict[str, str]] = None


class TeamStateCreate(TeamStateBase):
    pass


class TeamStateResponse(TeamStateBase):
    id: str
    last_update: datetime
    tenant_id: Optional[str]

    model_config = {"from_attributes": True}


class RecoveryEventCreate(BaseModel):
    agent_id: str
    episode_num: int
    trigger: str
    reason: Optional[str] = None
    dominance_before: float
    dominance_after: float
    epsilon_before: float
    epsilon_after: float
    plasticity_before: float
    plasticity_after: float


class RecoveryEventResponse(RecoveryEventCreate):
    id: str
    timestamp: datetime
    tenant_id: Optional[str]

    model_config = {"from_attributes": True}


class AgentActionTraceResponse(BaseModel):
    id: str
    agent_id: str
    state: str
    action: str
    reward: float
    next_state: str
    on_path: bool
    cue: bool
    timestamp: datetime
    tenant_id: Optional[str]

    model_config = {"from_attributes": True}


class CoordinationDecisionRequest(BaseModel):
    team_id: str
    state: str
    cue: bool = False
    alerts: List[str] = Field(default_factory=list)


class CoordinationDecisionResponse(BaseModel):
    team_id: str
    state: str
    joint_actions: Dict[str, str]
    coordination_timestamp: datetime


class AgentUpdateRequest(BaseModel):
    state: str
    action: str
    reward: float
    next_state: str
    on_path: bool


class AgentAdjustmentRequest(BaseModel):
    recent_returns: List[float]
    safety_event: bool = False


class AgentAdjustmentResponse(BaseModel):
    agent_id: str
    dominance: float
    epsilon: float
    plasticity: float
    recovery_triggered: bool
    reason: Optional[str] = None


class BulkDNAUpdateRequest(BaseModel):
    updates: Dict[str, MissionDNAUpdate]
    reason: str
    changed_by: str


class BulkDNAUpdateResponse(BaseModel):
    updated_count: int
    failed_count: int
    results: Dict[str, Dict[str, Any]]


class HealthCheckResponse(BaseModel):
    status: str
    postgres_ok: bool
    timestamp: datetime


class MetricsResponse(BaseModel):
    total_agents: int
    agents_in_recovery: int
    avg_dominance: float
    avg_path_conformance: float
    total_safety_violations: int
    timestamp: datetime


class DNAAuditLogResponse(BaseModel):
    id: str
    agent_id: str
    changed_fields: List[str]
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    changed_by: Optional[str]
    reason: Optional[str]
    timestamp: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# MIDDLEWARE/HELPER: IDEMPOTENCY & SECURE CHECKS
# ============================================================================

async def enforce_authz(
    user_id: str,
    tenant_id: str,
    action: str,
    resource: str,
    db: AsyncSession
) -> None:
    """Zero-Trust continuous authorization checking. Denies access immediately if checks fail."""
    is_granted, reason = await MissionLockService.continuous_authz_gate(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource=resource,
        db=db
    )
    if not is_granted:
        logger.error(f"[ZERO_TRUST_DENIED] user_id={user_id} tenant_id={tenant_id} action={action} resource={resource}. Reason: {reason}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Continuous Authz Denied: {reason}"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthCheckResponse:
    """Verifies that the database pool is responsive and healthy."""
    postgres_ok = False
    try:
        await db.execute(func.now())
        postgres_ok = True
    except Exception as e:
        logger.error(f"Health check failed: {e}")

    return HealthCheckResponse(
        status="ok" if postgres_ok else "degraded",
        postgres_ok=postgres_ok,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/dna", response_model=MissionDNAResponse)
async def create_mission_dna(
    payload: MissionDNACreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> MissionDNAResponse:
    """Register a new immutable, auditable Mission DNA behavioral profile."""
    tenant_id = current_user.workspace_id

    # Idempotency deduplication check
    if idempotency_key:
        cached = await MissionLockService.check_idempotency(idempotency_key, db)
        if cached:
            return MissionDNAResponse(**cached)

    # Secure authz check
    await enforce_authz(current_user.id, tenant_id, "CREATE", f"dna/{payload.agent_id}", db)

    async with db.begin():
        # Check if DNA already exists
        existing = await MissionLockService.get_mission_dna(payload.agent_id, db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mission DNA for agent {payload.agent_id} already exists"
            )

        dna_data = payload.model_dump()
        dna_data["tenant_id"] = tenant_id

        dna = await MissionLockService.create_mission_dna(dna_data, db)
        
        # Populate initial agent_state row
        initial_state = MissionLockAgentState(
            agent_id=dna.agent_id,
            current_dominance=dna.dominance,
            current_plasticity=dna.plasticity,
            current_epsilon=dna.epsilon,
            target_return=None
        )
        db.add(initial_state)

        resp = MissionDNAResponse(
            id=dna.id,
            agent_id=dna.agent_id,
            role=dna.role,
            dominance=dna.dominance,
            plasticity=dna.plasticity,
            base_learning_rate=dna.base_learning_rate,
            epsilon=dna.epsilon,
            mission_bonus=dna.mission_bonus,
            off_path_penalty=dna.off_path_penalty,
            coordination_weight=dna.coordination_weight,
            safety_weight=dna.safety_weight,
            cue_boost=dna.cue_boost,
            min_dominance=dna.min_dominance,
            max_epsilon=dna.max_epsilon,
            max_plasticity=dna.max_plasticity,
            allowed_actions=dna.allowed_actions,
            forbidden_actions=dna.forbidden_actions or [],
            tenant_id=dna.tenant_id,
            created_at=dna.created_at,
            updated_at=dna.updated_at,
            locked=dna.locked,
            version=dna.version
        )
        
        if idempotency_key:
            await MissionLockService.save_idempotency(idempotency_key, resp.model_dump(mode="json"), db)

        return resp


@router.get("/dna/{agent_id}", response_model=MissionDNAResponse)
async def get_mission_dna(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> MissionDNAResponse:
    """Retrieve the DNA profile for an agent."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", f"dna/{agent_id}", db)

    dna = await MissionLockService.get_mission_dna(agent_id, db)
    if not dna:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DNA for agent {agent_id} not found"
        )

    # Scoping isolation check
    if dna.tenant_id != tenant_id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    return MissionDNAResponse(
        id=dna.id,
        agent_id=dna.agent_id,
        role=dna.role,
        dominance=dna.dominance,
        plasticity=dna.plasticity,
        base_learning_rate=dna.base_learning_rate,
        epsilon=dna.epsilon,
        mission_bonus=dna.mission_bonus,
        off_path_penalty=dna.off_path_penalty,
        coordination_weight=dna.coordination_weight,
        safety_weight=dna.safety_weight,
        cue_boost=dna.cue_boost,
        min_dominance=dna.min_dominance,
        max_epsilon=dna.max_epsilon,
        max_plasticity=dna.max_plasticity,
        allowed_actions=dna.allowed_actions,
        forbidden_actions=dna.forbidden_actions or [],
        tenant_id=dna.tenant_id,
        created_at=dna.created_at,
        updated_at=dna.updated_at,
        locked=dna.locked,
        version=dna.version
    )


@router.patch("/dna/{agent_id}", response_model=MissionDNAResponse)
async def update_mission_dna(
    agent_id: str,
    payload: MissionDNAUpdate,
    changed_by: str = Query(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> MissionDNAResponse:
    """Mutate DNA settings with complete transaction audit trails."""
    tenant_id = current_user.workspace_id

    if idempotency_key:
        cached = await MissionLockService.check_idempotency(idempotency_key, db)
        if cached:
            return MissionDNAResponse(**cached)

    await enforce_authz(current_user.id, tenant_id, "UPDATE", f"dna/{agent_id}", db)

    async with db.begin():
        dna_record = await MissionLockService.get_mission_dna(agent_id, db)
        if not dna_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

        if dna_record.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

        updates = payload.model_dump(exclude_none=True, exclude={"reason", "changed_by"})
        reason = payload.reason or "Manual administrative adjust"
        
        dna = await MissionLockService.update_mission_dna(
            agent_id=agent_id,
            updates=updates,
            changed_by=changed_by,
            reason=reason,
            db=db
        )

        resp = MissionDNAResponse(
            id=dna.id,
            agent_id=dna.agent_id,
            role=dna.role,
            dominance=dna.dominance,
            plasticity=dna.plasticity,
            base_learning_rate=dna.base_learning_rate,
            epsilon=dna.epsilon,
            mission_bonus=dna.mission_bonus,
            off_path_penalty=dna.off_path_penalty,
            coordination_weight=dna.coordination_weight,
            safety_weight=dna.safety_weight,
            cue_boost=dna.cue_boost,
            min_dominance=dna.min_dominance,
            max_epsilon=dna.max_epsilon,
            max_plasticity=dna.max_plasticity,
            allowed_actions=dna.allowed_actions,
            forbidden_actions=dna.forbidden_actions or [],
            tenant_id=dna.tenant_id,
            created_at=dna.created_at,
            updated_at=dna.updated_at,
            locked=dna.locked,
            version=dna.version
        )

        if idempotency_key:
            await MissionLockService.save_idempotency(idempotency_key, resp.model_dump(mode="json"), db)

        return resp


@router.post("/dna/bulk-update", response_model=BulkDNAUpdateResponse)
async def bulk_update_dna(
    payload: BulkDNAUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> BulkDNAUpdateResponse:
    """Atomically batch mutate multiple DNA profiles."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "UPDATE", "dna/bulk", db)

    updated_count = 0
    failed_count = 0
    results = {}

    async with db.begin():
        for agent_id, updates in payload.updates.items():
            try:
                dna_record = await MissionLockService.get_mission_dna(agent_id, db)
                if not dna_record:
                    failed_count += 1
                    results[agent_id] = {"status": "failed", "error": "Agent not found"}
                    continue

                if dna_record.tenant_id != tenant_id:
                    failed_count += 1
                    results[agent_id] = {"status": "failed", "error": "Cross-tenant access denied"}
                    continue

                update_dict = updates.model_dump(exclude_none=True, exclude={"reason", "changed_by"})
                await MissionLockService.update_mission_dna(
                    agent_id=agent_id,
                    updates=update_dict,
                    changed_by=payload.changed_by,
                    reason=payload.reason,
                    db=db
                )
                updated_count += 1
                results[agent_id] = {"status": "updated"}
            except Exception as e:
                failed_count += 1
                results[agent_id] = {"status": "failed", "error": str(e)}

    return BulkDNAUpdateResponse(
        updated_count=updated_count,
        failed_count=failed_count,
        results=results,
    )


@router.post("/mission", response_model=AgentMissionResponse)
async def create_agent_mission(
    payload: AgentMissionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> AgentMissionResponse:
    """Create a new expected behavioral trajectory/mission path."""
    tenant_id = current_user.workspace_id

    if idempotency_key:
        cached = await MissionLockService.check_idempotency(idempotency_key, db)
        if cached:
            return AgentMissionResponse(**cached)

    await enforce_authz(current_user.id, tenant_id, "CREATE", f"mission/{payload.agent_id}", db)

    async with db.begin():
        # Make sure agent exists
        dna = await MissionLockService.get_mission_dna(payload.agent_id, db)
        if not dna:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot assign mission. Mission DNA for agent {payload.agent_id} not found."
            )

        if dna.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

        mission_data = payload.model_dump()
        mission_data["tenant_id"] = tenant_id
        mission_data["active"] = True

        m = await MissionLockService.create_agent_mission(mission_data, db)

        resp = AgentMissionResponse(
            id=m.id,
            agent_id=m.agent_id,
            mission_name=m.mission_name,
            preferred_transitions=m.preferred_transitions,
            description=m.description,
            tenant_id=m.tenant_id,
            active=m.active,
            created_at=m.created_at,
            updated_at=m.updated_at,
            version=m.version
        )

        if idempotency_key:
            await MissionLockService.save_idempotency(idempotency_key, resp.model_dump(mode="json"), db)

        return resp


@router.get("/mission/{agent_id}", response_model=AgentMissionResponse)
async def get_agent_mission(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> AgentMissionResponse:
    """Retrieve active mission path for an agent."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", f"mission/{agent_id}", db)

    m = await MissionLockService.get_agent_mission(agent_id, db)
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active mission for agent {agent_id} not found"
        )

    if m.tenant_id != tenant_id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    return AgentMissionResponse(
        id=m.id,
        agent_id=m.agent_id,
        mission_name=m.mission_name,
        preferred_transitions=m.preferred_transitions,
        description=m.description,
        tenant_id=m.tenant_id,
        active=m.active,
        created_at=m.created_at,
        updated_at=m.updated_at,
        version=m.version
    )


@router.post("/agent/{agent_id}/act")
async def agent_act(
    agent_id: str,
    state: str = Query(...),
    cue: bool = Query(False),
    actions: List[str] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> Dict[str, str]:
    """Sovereign out-of-process action selection."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "EXECUTE", f"agent/{agent_id}/act", db)

    async with db.begin():
        agent = await MissionLockService.load_agent_state(agent_id, actions, db)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

        if agent.dna.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

        action = agent.act(state, cue=cue)
        
        # Save trace of trace logs
        on_path = agent.mission.is_on_path(state, action)
        await MissionLockService.record_action_trace(
            agent_id=agent_id,
            state=state,
            action=action,
            reward=0.0,
            next_state="",
            on_path=on_path,
            cue=cue,
            tenant_id=tenant_id,
            db=db
        )

        return {
            "agent_id": agent_id,
            "state": state,
            "action": action,
            "cue": str(cue),
            "on_path": str(on_path)
        }


@router.post("/agent/{agent_id}/update")
async def update_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    actions: List[str] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> Dict[str, str]:
    """Perform out-of-process dual-policy temporal difference learning update."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "UPDATE", f"agent/{agent_id}/update", db)

    async with db.begin():
        agent = await MissionLockService.load_agent_state(agent_id, actions, db)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

        if agent.dna.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

        # Capture states prior to update for telemetry
        dominance_before = agent.dna.dominance
        epsilon_before = agent.dna.epsilon
        plasticity_before = agent.dna.plasticity

        agent.update(payload.state, payload.action, payload.reward, payload.next_state)

        # Build metrics update
        # Simple moving average and conformance trackers
        state_stmt = select(MissionLockAgentState).where(MissionLockAgentState.agent_id == agent_id)
        state_res = await db.execute(state_stmt)
        state_row = state_res.scalar_one_or_none()

        moving_avg = payload.reward
        safety_violations = 0
        if state_row:
            moving_avg = 0.9 * (state_row.moving_avg_return or 0.0) + 0.1 * payload.reward
            safety_violations = state_row.safety_violations
            if payload.action in (agent.dna.forbidden_actions or []):
                safety_violations += 1

        # Record action trace
        await MissionLockService.record_action_trace(
            agent_id=agent_id,
            state=payload.state,
            action=payload.action,
            reward=payload.reward,
            next_state=payload.next_state,
            on_path=payload.on_path,
            cue=False,
            tenant_id=tenant_id,
            db=db
        )

        # Save serialized states
        await MissionLockService.save_agent_state(
            agent=agent,
            db=db,
            last_action=payload.action,
            last_state=payload.state,
            last_episode_return=payload.reward,
            moving_avg_return=moving_avg,
            path_conformance=1.0 if payload.on_path else 0.0,
            safety_violations=safety_violations
        )

        # Log episode telemetry
        telemetry_data = {
            "agent_id": agent_id,
            "episode_num": (state_row.steps_since_recovery if state_row else 0) + 1,
            "episode_return": payload.reward,
            "path_actions": 1 if payload.on_path else 0,
            "off_path_actions": 0 if payload.on_path else 1,
            "path_conformance": 1.0 if payload.on_path else 0.0,
            "safety_events": 1 if payload.action in (agent.dna.forbidden_actions or []) else 0,
            "steps": 1,
            "recovery_triggered": False,
            "dominance_at_episode": dominance_before,
            "epsilon_at_episode": epsilon_before,
            "plasticity_at_episode": plasticity_before,
            "tenant_id": tenant_id
        }
        await MissionLockService.record_episode_telemetry(telemetry_data, db)

        # Update steps_since_recovery
        if state_row:
            state_row.steps_since_recovery += 1

        return {"status": "updated", "agent_id": agent_id}


@router.post("/agent/{agent_id}/adjust", response_model=AgentAdjustmentResponse)
async def adjust_agent(
    agent_id: str,
    payload: AgentAdjustmentRequest,
    actions: List[str] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> AgentAdjustmentResponse:
    """Sovereign out-of-process adaptive parameter adjustment and recovery logic."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "UPDATE", f"agent/{agent_id}/adjust", db)

    async with db.begin():
        agent = await MissionLockService.load_agent_state(agent_id, actions, db)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

        if agent.dna.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

        dominance_before = agent.dna.dominance
        epsilon_before = agent.dna.epsilon
        plasticity_before = agent.dna.plasticity

        recovery_triggered, reason = agent.adjust_rigidity(
            payload.recent_returns, payload.safety_event
        )

        if recovery_triggered:
            # Persistent audit event logging with snapshotting
            await MissionLockService.record_recovery_event(
                agent=agent,
                episode_num=0,
                trigger=reason or "manual",
                reason=reason or "Manual trigger adjustment",
                dominance_before=dominance_before,
                epsilon_before=epsilon_before,
                plasticity_before=plasticity_before,
                db=db
            )

        # Save metrics state changes
        await MissionLockService.save_agent_state(
            agent=agent,
            db=db,
            last_episode_return=payload.recent_returns[-1] if payload.recent_returns else 0.0,
            safety_violations=1 if payload.safety_event else 0
        )

        return AgentAdjustmentResponse(
            agent_id=agent_id,
            dominance=agent.dna.dominance,
            epsilon=agent.dna.epsilon,
            plasticity=agent.dna.plasticity,
            recovery_triggered=recovery_triggered,
            reason=reason
        )


@router.post("/team/decide", response_model=CoordinationDecisionResponse)
async def decide_joint_actions(
    payload: CoordinationDecisionRequest,
    actions: List[str] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> CoordinationDecisionResponse:
    """Coordinated multi-agent joint action decisioning."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "EXECUTE", f"team/{payload.team_id}/decide", db)

    async with db.begin():
        # Scan for active agents in workspace/tenant matching coordination
        stmt = select(MissionDNA.agent_id).where(MissionDNA.tenant_id == tenant_id)
        res = await db.execute(stmt)
        agent_ids = list(res.scalars().all())

        if not agent_ids:
            return CoordinationDecisionResponse(
                team_id=payload.team_id,
                state=payload.state,
                joint_actions={},
                coordination_timestamp=datetime.now(timezone.utc)
            )

        # Assemble stateless coordinator
        agent_pool = {}
        for aid in agent_ids:
            a = await MissionLockService.load_agent_state(aid, actions, db)
            if a:
                agent_pool[aid] = a

        coordinator = TeamCoordinator(agent_pool)
        joint_actions = coordinator.decide_joint_actions(
            state=payload.state,
            team_phase="unknown",
            alerts=payload.alerts
        )

        return CoordinationDecisionResponse(
            team_id=payload.team_id,
            state=payload.state,
            joint_actions=joint_actions,
            coordination_timestamp=datetime.now(timezone.utc)
        )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> MetricsResponse:
    """Aggregate dashboard metrics across all agents in tenant."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", "metrics", db)

    metrics = await MissionLockService.get_global_metrics(db)
    return MetricsResponse(
        total_agents=metrics["total_agents"],
        agents_in_recovery=metrics["agents_in_recovery"],
        avg_dominance=metrics["avg_dominance"],
        avg_path_conformance=metrics["avg_path_conformance"],
        total_safety_violations=metrics["total_safety_violations"],
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/agent/{agent_id}/metrics")
async def get_agent_metrics(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve detailed metrics for a single agent."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", f"agent/{agent_id}/metrics", db)

    dna = await MissionLockService.get_mission_dna(agent_id, db)
    if not dna:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

    if dna.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    metrics = await MissionLockService.get_agent_metrics(agent_id, db)
    
    # Load current state metrics
    state_stmt = select(MissionLockAgentState).where(MissionLockAgentState.agent_id == agent_id)
    state_res = await db.execute(state_stmt)
    state = state_res.scalar_one_or_none()

    return {
        "agent_id": agent_id,
        "role": dna.role,
        "current_dominance": state.current_dominance if state else dna.dominance,
        "current_epsilon": state.current_epsilon if state else dna.epsilon,
        "current_plasticity": state.current_plasticity if state else dna.plasticity,
        "total_episodes": metrics["total_episodes"],
        "avg_return": metrics["avg_return"],
        "avg_conformance": metrics["avg_conformance"],
        "total_safety_events": metrics["total_safety_events"],
        "recovery_count": metrics["recovery_count"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/audit/dna/{agent_id}", response_model=List[DNAAuditLogResponse])
async def get_dna_audit_log(
    agent_id: str,
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> List[DNAAuditLogResponse]:
    """Retrieve DNA audit mutations trace trail."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", f"audit/dna/{agent_id}", db)

    dna = await MissionLockService.get_mission_dna(agent_id, db)
    if not dna:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

    if dna.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    logs = await MissionLockService.get_dna_audit_log(agent_id, limit, db)
    
    return [
        DNAAuditLogResponse(
            id=log.id,
            agent_id=log.agent_id,
            changed_fields=log.changed_fields,
            old_values=log.old_values,
            new_values=log.new_values,
            changed_by=log.changed_by,
            reason=log.reason,
            timestamp=log.timestamp
        )
        for log in logs
    ]


@router.get("/agent/{agent_id}/state", response_model=AgentStateResponse)
async def get_agent_state(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> AgentStateResponse:
    """Retrieve current parameters and state for a target agent."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", f"agent/{agent_id}/state", db)

    dna = await MissionLockService.get_mission_dna(agent_id, db)
    if not dna:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

    if dna.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    stmt = select(MissionLockAgentState).where(MissionLockAgentState.agent_id == agent_id)
    res = await db.execute(stmt)
    state = res.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"State for agent {agent_id} not found")

    return state


@router.get("/agents/{agent_id}/state", response_model=AgentStateResponse)
async def get_agents_state_plural(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> AgentStateResponse:
    """Plural alias: Retrieve current parameters and state for a target agent."""
    return await get_agent_state(agent_id, db, current_user)


@router.get("/team/{team_id}/coordinate", response_model=TeamStateResponse)
async def get_team_coordinate(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> TeamStateResponse:
    """Retrieve team coordination snapshot state."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", f"team/{team_id}/coordinate", db)

    stmt = select(TeamState).where(TeamState.team_id == team_id)
    res = await db.execute(stmt)
    team_state = res.scalar_one_or_none()
    if not team_state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team state for team {team_id} not found")

    if team_state.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    return team_state


@router.get("/teams/{team_id}/coordinate", response_model=TeamStateResponse)
async def get_teams_coordinate_plural(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> TeamStateResponse:
    """Plural alias: Retrieve team coordination snapshot state."""
    return await get_team_coordinate(team_id, db, current_user)


@router.get("/agent/{agent_id}/trace", response_model=List[AgentActionTraceResponse])
async def get_agent_trace(
    agent_id: str,
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> List[AgentActionTraceResponse]:
    """Retrieve trace log of exact action sequences & conformance for a target agent."""
    tenant_id = current_user.workspace_id
    await enforce_authz(current_user.id, tenant_id, "READ", f"agent/{agent_id}/trace", db)

    dna = await MissionLockService.get_mission_dna(agent_id, db)
    if not dna:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

    if dna.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    stmt = (
        select(AgentActionTrace)
        .where(AgentActionTrace.agent_id == agent_id)
        .order_by(AgentActionTrace.timestamp.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    traces = res.scalars().all()

    return list(traces)


@router.get("/agents/{agent_id}/trace", response_model=List[AgentActionTraceResponse])
async def get_agents_trace_plural(
    agent_id: str,
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> List[AgentActionTraceResponse]:
    """Plural alias: Retrieve trace log of exact action sequences & conformance for a target agent."""
    return await get_agent_trace(agent_id, limit, db, current_user)
