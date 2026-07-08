import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch

from backend.apps.api.main import app
from backend.core.config.settings import settings
from backend.core.database.database import async_session, engine, Base
from backend.db.models.mission_lock import (
    MissionDNA, MissionLockAgentState, TeamState, AgentActionTrace, TenantRole, AuthzLog
)
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.security import KillSwitchState, AuditLog
from backend.db.models.billing import BudgetRule
from backend.db.models.ai import ExecutionLog
from backend.core.security.auth import get_current_user, create_access_token

class MockUser:
    def __init__(self, user_id: str, workspace_id: str):
        self.id = user_id
        self.workspace_id = workspace_id
        self.email = f"{user_id}@veklom.local"

@pytest.mark.asyncio
async def test_mission_lock_get_endpoints():
    # Save original settings to restore later
    original_mode = settings.X402_TEST_PROOF_MODE
    settings.X402_TEST_PROOF_MODE = True

    # 1. Setup sqlite tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[
                MissionDNA.__table__,
                MissionLockAgentState.__table__,
                TeamState.__table__,
                AgentActionTrace.__table__,
                TenantRole.__table__,
                AuthzLog.__table__,
                User.__table__,
                Workspace.__table__,
                KillSwitchState.__table__,
                BudgetRule.__table__,
                ExecutionLog.__table__,
                AuditLog.__table__
            ]
        ))

    # 2. Seed data for User A in Tenant A (OWNER)
    user_id_a = f"usr_{uuid.uuid4().hex[:8]}"
    tenant_id_a = f"ws_{uuid.uuid4().hex[:8]}"
    user_a = MockUser(user_id=user_id_a, workspace_id=tenant_id_a)

    # Seed data for User B in Tenant B (USER - standard, should be denied by continuous authz)
    user_id_b = f"usr_{uuid.uuid4().hex[:8]}"
    tenant_id_b = f"ws_{uuid.uuid4().hex[:8]}"
    user_b = MockUser(user_id=user_id_b, workspace_id=tenant_id_b)

    # Seed data for User C in Tenant A (ANALYST - read clearance)
    user_id_c = f"usr_{uuid.uuid4().hex[:8]}"
    user_c = MockUser(user_id=user_id_c, workspace_id=tenant_id_a)

    agent_id_a = f"agent_{uuid.uuid4().hex[:8]}"
    team_id_a = f"team_{uuid.uuid4().hex[:8]}"

    # Seed Tenant B data (to verify cross-tenant isolation)
    agent_id_b = f"agent_{uuid.uuid4().hex[:8]}"
    team_id_b = f"team_{uuid.uuid4().hex[:8]}"

    async with async_session() as db:
        # Seed Workspaces
        ws_a = Workspace(
            id=tenant_id_a,
            name="Workspace A",
            slug=f"ws-a-{uuid.uuid4().hex[:6]}",
            is_active=True,
            industry="tech",
            license_tier="sovereign"
        )
        ws_b = Workspace(
            id=tenant_id_b,
            name="Workspace B",
            slug=f"ws-b-{uuid.uuid4().hex[:6]}",
            is_active=True,
            industry="finance",
            license_tier="sovereign"
        )
        db.add_all([ws_a, ws_b])
        await db.flush()

        # Seed Users in User table
        db_user_a = User(
            id=user_id_a,
            email=user_a.email,
            full_name="User A",
            hashed_password="",
            workspace_id=tenant_id_a,
            role="OWNER",
            is_active=True
        )
        db_user_b = User(
            id=user_id_b,
            email=user_b.email,
            full_name="User B",
            hashed_password="",
            workspace_id=tenant_id_b,
            role="OWNER",
            is_active=True
        )
        db_user_c = User(
            id=user_id_c,
            email=user_c.email,
            full_name="User C",
            hashed_password="",
            workspace_id=tenant_id_a,
            role="OWNER",
            is_active=True
        )
        db.add_all([db_user_a, db_user_b, db_user_c])

        # Seed Tenant roles
        role_owner = TenantRole(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id_a,
            user_id=user_id_a,
            role="OWNER"
        )
        role_analyst = TenantRole(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id_a,
            user_id=user_id_c,
            role="ANALYST"
        )
        role_user = TenantRole(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id_b,
            user_id=user_id_b,
            role="USER"
        )
        db.add_all([role_owner, role_analyst, role_user])

        # Seed DNA and state for Tenant A
        dna_a = MissionDNA(
            id=str(uuid.uuid4()),
            agent_id=agent_id_a,
            role="planner",
            tenant_id=tenant_id_a
        )
        db.add(dna_a)
        await db.flush()

        state_a = MissionLockAgentState(
            id=str(uuid.uuid4()),
            agent_id=agent_id_a,
            current_dominance=0.90,
            current_plasticity=0.02,
            current_epsilon=0.05,
            last_episode_return=1.5,
            moving_avg_return=1.2,
            path_conformance=0.95,
            steps_since_recovery=10,
            safety_violations=0,
            last_action="DECIDE",
            last_state="IDLE"
        )
        db.add(state_a)

        # Seed TeamState for Tenant A
        team_a = TeamState(
            id=str(uuid.uuid4()),
            team_id=team_id_a,
            phase="operational",
            alerts=["drift_warn"],
            shared_goal_progress=0.75,
            last_joint_actions={"agent-1": "ACT"},
            tenant_id=tenant_id_a
        )
        db.add(team_a)

        # Seed AgentActionTrace for Tenant A
        trace_1 = AgentActionTrace(
            id=str(uuid.uuid4()),
            agent_id=agent_id_a,
            state="S1",
            action="ACT_A",
            reward=0.5,
            next_state="S2",
            on_path=True,
            cue=False,
            tenant_id=tenant_id_a
        )
        trace_2 = AgentActionTrace(
            id=str(uuid.uuid4()),
            agent_id=agent_id_a,
            state="S2",
            action="ACT_B",
            reward=-0.1,
            next_state="S3",
            on_path=False,
            cue=True,
            tenant_id=tenant_id_a
        )
        db.add_all([trace_1, trace_2])

        # Seed DNA and state for Tenant B (Cross-tenant check targets)
        dna_b = MissionDNA(
            id=str(uuid.uuid4()),
            agent_id=agent_id_b,
            role="verifier",
            tenant_id=tenant_id_b
        )
        db.add(dna_b)
        await db.flush()

        state_b = MissionLockAgentState(
            id=str(uuid.uuid4()),
            agent_id=agent_id_b,
            current_dominance=0.85,
            current_plasticity=0.01,
            current_epsilon=0.02,
            last_episode_return=0.8,
            moving_avg_return=0.8,
            path_conformance=1.0,
            steps_since_recovery=0,
            safety_violations=0
        )
        db.add(state_b)

        team_b = TeamState(
            id=str(uuid.uuid4()),
            team_id=team_id_b,
            phase="calibration",
            tenant_id=tenant_id_b
        )
        db.add(team_b)

        await db.commit()

    # 3. Setup Test Client
    client = TestClient(app)

    # 4. Generate Auth Tokens and Headers
    token_a = create_access_token(data={"sub": user_id_a})
    token_b = create_access_token(data={"sub": user_id_b})
    token_c = create_access_token(data={"sub": user_id_c})

    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Payment": f"test_proof_valid_owner_{uuid.uuid4().hex[:6]}"
    }
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Payment": f"test_proof_valid_user_{uuid.uuid4().hex[:6]}"
    }
    headers_c = {
        "Authorization": f"Bearer {token_c}",
        "X-Payment": f"test_proof_valid_analyst_{uuid.uuid4().hex[:6]}"
    }

    try:
        # ==========================================
        # SCENARIO A: OWNER SUCCESSFUL ACCESSES (Tenant A)
        # ==========================================
        app.dependency_overrides[get_current_user] = lambda: user_a

        # 1. GET /agent/{agent_id}/state
        resp = client.get(f"/api/v1/mission-lock/agent/{agent_id_a}/state", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == agent_id_a
        assert data["current_dominance"] == 0.90
        assert data["path_conformance"] == 0.95
        assert data["last_action"] == "DECIDE"

        # Plural alias /agents/{agent_id}/state
        resp_plural = client.get(f"/api/v1/mission-lock/agents/{agent_id_a}/state", headers=headers_a)
        assert resp_plural.status_code == 200
        assert resp_plural.json() == data

        # 2. GET /team/{team_id}/coordinate
        resp = client.get(f"/api/v1/mission-lock/team/{team_id_a}/coordinate", headers=headers_a)
        assert resp.status_code == 200
        data_team = resp.json()
        assert data_team["team_id"] == team_id_a
        assert data_team["phase"] == "operational"
        assert data_team["shared_goal_progress"] == 0.75

        # Plural alias /teams/{team_id}/coordinate
        resp_plural = client.get(f"/api/v1/mission-lock/teams/{team_id_a}/coordinate", headers=headers_a)
        assert resp_plural.status_code == 200
        assert resp_plural.json() == data_team

        # 3. GET /agent/{agent_id}/trace
        resp = client.get(f"/api/v1/mission-lock/agent/{agent_id_a}/trace", headers=headers_a)
        assert resp.status_code == 200
        traces = resp.json()
        assert len(traces) == 2
        # Should be sorted by timestamp descending, let's verify both elements are traces
        assert traces[0]["agent_id"] == agent_id_a
        assert "on_path" in traces[0]

        # Plural alias /agents/{agent_id}/trace
        resp_plural = client.get(f"/api/v1/mission-lock/agents/{agent_id_a}/trace", headers=headers_a)
        assert resp_plural.status_code == 200
        assert resp_plural.json() == traces

        # ==========================================
        # SCENARIO B: ANALYST READ CLEARANCE (Tenant A)
        # ==========================================
        app.dependency_overrides[get_current_user] = lambda: user_c

        # Analysts should have READ access to GET routes
        resp = client.get(f"/api/v1/mission-lock/agent/{agent_id_a}/state", headers=headers_c)
        assert resp.status_code == 200

        resp = client.get(f"/api/v1/mission-lock/team/{team_id_a}/coordinate", headers=headers_c)
        assert resp.status_code == 200

        resp = client.get(f"/api/v1/mission-lock/agent/{agent_id_a}/trace", headers=headers_c)
        assert resp.status_code == 200

        # ==========================================
        # SCENARIO C: CONTINUOUS AUTHZ DENIED (Tenant B has standard USER role)
        # ==========================================
        app.dependency_overrides[get_current_user] = lambda: user_b

        # Standard USER is unauthorized for non-dna read operations
        resp = client.get(f"/api/v1/mission-lock/agent/{agent_id_b}/state", headers=headers_b)
        assert resp.status_code == 403
        assert "Continuous Authz Denied" in resp.json()["detail"]

        resp = client.get(f"/api/v1/mission-lock/team/{team_id_b}/coordinate", headers=headers_b)
        assert resp.status_code == 403
        assert "Continuous Authz Denied" in resp.json()["detail"]

        # ==========================================
        # SCENARIO D: CROSS-TENANT ISOLATION DENIED (Tenant A OWNER accessing Tenant B)
        # ==========================================
        app.dependency_overrides[get_current_user] = lambda: user_a

        # User A is OWNER in Tenant A, but has no ownership/access to Tenant B's specific agents or teams
        resp = client.get(f"/api/v1/mission-lock/agent/{agent_id_b}/state", headers=headers_a)
        assert resp.status_code == 403
        assert "Cross-tenant access denied" in resp.json()["detail"]

        resp = client.get(f"/api/v1/mission-lock/team/{team_id_b}/coordinate", headers=headers_a)
        assert resp.status_code == 403
        assert "Cross-tenant access denied" in resp.json()["detail"]

        resp = client.get(f"/api/v1/mission-lock/agent/{agent_id_b}/trace", headers=headers_a)
        assert resp.status_code == 403
        assert "Cross-tenant access denied" in resp.json()["detail"]

        # ==========================================
        # SCENARIO E: 404 NOT FOUND (Owner queries non-existent agent/team)
        # ==========================================
        app.dependency_overrides[get_current_user] = lambda: user_a

        resp = client.get(f"/api/v1/mission-lock/agent/non-existent-agent/state", headers=headers_a)
        assert resp.status_code == 404

        resp = client.get(f"/api/v1/mission-lock/team/non-existent-team/coordinate", headers=headers_a)
        assert resp.status_code == 404

    finally:
        # Restore settings and clear overrides
        settings.X402_TEST_PROOF_MODE = original_mode
        app.dependency_overrides.pop(get_current_user, None)
