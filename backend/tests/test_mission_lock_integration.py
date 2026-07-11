import pytest
from sqlalchemy import ARRAY as GENERIC_ARRAY
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from backend.core.services.mission_lock_service import (
    MissionLockAgent,
    MissionLockService,
    MissionPath,
    TabularPolicy,
)
from backend.core.services.vnp_scoring import update_agent_governance_score
from backend.db.models.mission_lock import (
    AgentMission,
    Base,
    MissionDNA,
    MissionLockAgentState,
    TenantRole,
)


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(PG_ARRAY, "sqlite")
def compile_pg_array_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(GENERIC_ARRAY, "sqlite")
def compile_generic_array_sqlite(type_, compiler, **kw):
    return "TEXT"


@pytest.fixture
async def async_session():
    """Sets up an isolated, in-memory SQLite database for testing the mission lock system."""
    # We use SQLite in-memory database with standard async connection
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        execution_options={"schema_translate_map": {"mission_lock": None}},
    )

    async with engine.begin() as conn:
        # Create all tables associated with Base
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
async def test_tabular_policy_serialization_deserialization():
    """Verify that TabularPolicy correctly serializes and deserializes Q-tables."""
    actions = ["fetch_task", "verify_budget", "execute_task"]
    policy = TabularPolicy(actions=actions)

    # Train policy slightly
    policy.update(
        state="idle",
        action="fetch_task",
        reward=1.0,
        next_state="task_received",
        lr=0.1,
    )
    policy.update(
        state="task_received",
        action="verify_budget",
        reward=2.0,
        next_state="budget_ok",
        lr=0.1,
    )

    # Serialize
    serialized = policy.serialize()
    assert "q_table" in serialized
    assert "actions" in serialized
    assert serialized["actions"] == actions
    assert "idle" in serialized["q_table"]

    # Deserialize
    deserialized = TabularPolicy.deserialize(serialized)
    assert deserialized.actions == actions
    assert (
        deserialized.q_table["idle"]["fetch_task"]
        == policy.q_table["idle"]["fetch_task"]
    )
    assert deserialized.best_action("idle") == "fetch_task"


@pytest.mark.anyio
async def test_mission_lock_agent_reward_shaping():
    """Verify reward shaping: bonuses for conforming path actions and penalties for deviations."""
    dna = MissionDNA(
        role="executor",
        dominance=0.85,
        plasticity=0.01,
        base_learning_rate=0.08,
        epsilon=0.02,
        mission_bonus=1.0,
        off_path_penalty=0.5,
        safety_weight=1.0,
        forbidden_actions=["exceed_budget"],
    )
    mission_path = MissionPath(
        preferred_actions={"idle": "fetch_task", "task_received": "verify_budget"}
    )

    agent = MissionLockAgent(
        agent_id="test-agent",
        actions=["fetch_task", "verify_budget", "exceed_budget", "idle_action"],
        dna=dna,
        mission=mission_path,
    )

    # Conforming action: reward = base_reward + mission_bonus = 1.0 + 1.0 = 2.0
    conforming_reward = agent.shaped_reward(
        state="idle", action="fetch_task", base_reward=1.0
    )
    assert conforming_reward == 2.0

    # Deviating action: reward = base_reward - off_path_penalty = 1.0 - 0.5 = 0.5
    deviating_reward = agent.shaped_reward(
        state="idle", action="idle_action", base_reward=1.0
    )
    assert deviating_reward == 0.5

    # Forbidden action: reward = base_reward - off_path_penalty - 10 * safety_weight = 1.0 - 0.5 - 10.0 = -9.5
    forbidden_reward = agent.shaped_reward(
        state="idle", action="exceed_budget", base_reward=1.0
    )
    assert forbidden_reward == -9.5


@pytest.mark.anyio
async def test_stateless_service_save_and_load_agent_state(async_session):
    """Verify stateless saving and reloading of agent dual-policies and metrics out-of-process."""
    agent_id = "agent-11"
    tenant_id = "tenant-test"
    actions = ["fetch_task", "verify_budget", "execute_task"]

    # Pre-register DNA and Mission Path
    dna = MissionDNA(
        agent_id=agent_id,
        tenant_id=tenant_id,
        role="executor",
        dominance=0.90,
        plasticity=0.01,
        base_learning_rate=0.05,
        epsilon=0.03,
        allowed_actions=actions,
        forbidden_actions=["forbidden_action"],
    )
    mission = AgentMission(
        agent_id=agent_id,
        tenant_id=tenant_id,
        mission_name="Test Mission Path",
        preferred_transitions={"idle": "fetch_task"},
        active=True,
    )
    async_session.add(dna)
    async_session.add(mission)
    await async_session.commit()

    # Load agent
    agent = await MissionLockService.load_agent_state(
        agent_id=agent_id, actions=actions, db=async_session
    )
    assert agent is not None
    assert agent.dna.dominance == 0.90
    assert agent.dna.epsilon == 0.03

    # Update agent state policy and save
    agent.dominant_policy.update("idle", "fetch_task", 1.5, "task_received", 0.1)
    await MissionLockService.save_agent_state(
        agent=agent,
        db=async_session,
        last_action="fetch_task",
        last_state="idle",
        last_episode_return=1.5,
        path_conformance=1.0,
    )
    await async_session.commit()

    # Reload agent and check state is persisted
    reloaded_agent = await MissionLockService.load_agent_state(
        agent_id=agent_id, actions=actions, db=async_session
    )
    assert reloaded_agent is not None
    assert reloaded_agent.dominant_policy.q_table["idle"]["fetch_task"] > 0.0
    assert reloaded_agent.dna.dominance == 0.90


@pytest.mark.anyio
async def test_continuous_authz_gate(async_session):
    """Verify Zero-Trust Continuous Authz Gate allows owners/admins and blocks analysts from writes."""
    user_id = "user-11"
    tenant_id = "tenant-alpha"

    # Pre-register user's tenant role
    role = TenantRole(tenant_id=tenant_id, user_id=user_id, role="owner")
    async_session.add(role)
    await async_session.commit()

    # 1. Clear OWNER for write
    granted, reason = await MissionLockService.continuous_authz_gate(
        user_id=user_id,
        tenant_id=tenant_id,
        action="WRITE",
        resource="dna_update",
        db=async_session,
    )
    assert granted
    assert "continuous clearance" in reason

    # 2. Add an analyst user
    analyst_user = "user-analyst"
    role_analyst = TenantRole(tenant_id=tenant_id, user_id=analyst_user, role="analyst")
    async_session.add(role_analyst)
    await async_session.commit()

    # 3. ANALYST should pass READ
    granted_read, reason_read = await MissionLockService.continuous_authz_gate(
        user_id=analyst_user,
        tenant_id=tenant_id,
        action="READ",
        resource="dna_view",
        db=async_session,
    )
    assert granted_read

    # 4. ANALYST should fail WRITE
    granted_write, reason_write = await MissionLockService.continuous_authz_gate(
        user_id=analyst_user,
        tenant_id=tenant_id,
        action="WRITE",
        resource="dna_update",
        db=async_session,
    )
    assert not granted_write
    assert "denied" in reason_write


@pytest.mark.anyio
async def test_idempotency_key_caching(async_session):
    """Verify that idempotency key mechanism correctly caches and prevents duplicate requests."""
    key = "idem-key-999"
    response_payload = {"status": "success", "tx": "0xabc123"}

    # Save key
    await MissionLockService.save_idempotency(
        key=key, response=response_payload, db=async_session
    )
    await async_session.commit()

    # Validate checking retrieves the exact cached response
    cached_resp = await MissionLockService.check_idempotency(key=key, db=async_session)
    assert cached_resp == response_payload


@pytest.mark.anyio
async def test_compile_time_gpc_constraint_extraction_and_registration(async_session):
    """Verify that compiling GPC graph automatically registers the newborn agent, DNA, and conformance path."""
    pipeline_id = "gpc-pipeline-01"
    tenant_id = "tenant-beta"

    class MockGPCNode:
        def __init__(self, node_type, config):
            self.node_type = node_type
            self.config = config

    nodes = [
        MockGPCNode("Input", {"forbidden_actions": ["leak_keys"]}),
        MockGPCNode("Transform", {"preferred_transitions": {"processing": "encrypt"}}),
    ]

    await MissionLockService.extract_and_register_gpc_constraints(
        pipeline_id=pipeline_id,
        name="Security Verification Planner Pipeline",
        description="A high security pipeline. Forbidden: exfiltrate_db. Prefer: idle -> check_auth.",
        nodes=nodes,
        tenant_id=tenant_id,
        db=async_session,
    )
    await async_session.commit()

    # 1. Assert DNA exists and has correct extracted role & forbidden actions
    stmt_dna = select(MissionDNA).where(MissionDNA.agent_id == pipeline_id)
    res_dna = await async_session.execute(stmt_dna)
    dna = res_dna.scalar_one_or_none()

    assert dna is not None
    assert dna.role == "planner"  # Extracted from pipeline name "Planner"
    assert "leak_keys" in dna.forbidden_actions  # Extracted from node configuration
    assert (
        "exfiltrate_db" in dna.forbidden_actions
    )  # Extracted from pipeline description text

    # 2. Assert Conformance Path exists and is active
    stmt_mission = select(AgentMission).where(
        AgentMission.agent_id == pipeline_id, AgentMission.active
    )
    res_mission = await async_session.execute(stmt_mission)
    mission = res_mission.scalar_one_or_none()

    assert mission is not None
    assert (
        mission.preferred_transitions["idle"] == "check_auth"
    )  # Extracted from description text "idle -> check_auth"
    assert (
        mission.preferred_transitions["processing"] == "encrypt"
    )  # Extracted from node configuration


@pytest.mark.anyio
async def test_vnp_governance_scoring_model(async_session):
    """Verify path-conformance signals and safety violations correctly adjust trust score metrics in VNP."""
    agent_id = "governed-agent-88"
    tenant_id = "tenant-gamma"

    # Create newborn DNA
    dna = MissionDNA(
        agent_id=agent_id, tenant_id=tenant_id, role="executor", dominance=0.85
    )
    async_session.add(dna)
    await async_session.commit()

    # 1. Ideal conforming state (100% path conformance, 0 violations)
    state = MissionLockAgentState(
        agent_id=agent_id,
        path_conformance=1.0,  # 100%
        safety_violations=0,
        current_dominance=0.85,
    )
    async_session.add(state)
    await async_session.commit()

    score = await update_agent_governance_score(
        session=async_session, agent_id=agent_id
    )
    assert score == 100.0  # Perfect conforming trust

    # 2. Non-conforming state with safety violations (80% conformance, 2 safety violations)
    state.path_conformance = 0.80
    state.safety_violations = 2
    await async_session.commit()

    score_degraded = await update_agent_governance_score(
        session=async_session, agent_id=agent_id
    )
    # Expected trust: 80.0 (conformance) - (2 * 15.0) (penalties) = 50.0
    assert score_degraded == 50.0
