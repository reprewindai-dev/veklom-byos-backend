import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.apps.api.routers.capi import (
    ExecutionIntent,
    evaluate_intent_governed,
    governed_execution_intercept,
    router,
    stream_run,
)
from backend.db.models.agent import AgentIdentity
from backend.db.models.authority import AuthorityBundle, AuthorityRun


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.workspace_id = "test-workspace"
    user.id = "test-user-id"
    return user


@pytest.fixture
def base_intent():
    return ExecutionIntent(
        agent_id="agent-001",
        pgl_id="pgl_sig_test",
        mission_id="mission-001",
        target_protocol="mcp",
        action="fs.read",
        payload={"path": "/app/data.txt", "random": str(uuid.uuid4())},
    )


@pytest.mark.anyio
async def test_capi_gate_unknown_agent(mock_db, base_intent):
    async def mock_execute(query):
        mock_val = MagicMock()
        mock_val.scalar_one_or_none.return_value = None
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(
        base_intent, mock_db, "test-workspace"
    )

    assert not is_approved
    assert reason == "AGENT_NOT_FOUND"
    assert failure_phase == 1
    assert phase_results["1"] == "FAILED: Agent identity not found in registry"


@pytest.mark.anyio
async def test_capi_gate_missing_sig(mock_db, base_intent):
    agent_id_mock = AgentIdentity(
        id="agent-001",
        tenant_id="test-workspace",
        name="Test Agent",
        created_by_pgl_id="user-01",
        metadata_json={"trust_score": 90},
    )

    async def mock_execute(query):
        mock_val = MagicMock()
        mock_val.scalar_one_or_none.return_value = agent_id_mock
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    base_intent.pgl_id = ""
    is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(
        base_intent, mock_db, "test-workspace"
    )

    assert not is_approved
    assert reason == "MISSING_PGL_SIGNATURE"
    assert failure_phase == 1


@pytest.mark.anyio
async def test_capi_gate_bad_sig(mock_db, base_intent):
    agent_id_mock = AgentIdentity(
        id="agent-001",
        tenant_id="test-workspace",
        name="Test Agent",
        created_by_pgl_id="user-01",
        metadata_json={"trust_score": 90},
    )

    async def mock_execute(query):
        mock_val = MagicMock()
        mock_val.scalar_one_or_none.return_value = agent_id_mock
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    base_intent.pgl_id = "badsig"
    is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(
        base_intent, mock_db, "test-workspace"
    )

    assert not is_approved
    assert reason == "CRYPTOGRAPHIC_SIGNATURE_INVALID"
    assert failure_phase == 1


@pytest.mark.anyio
async def test_capi_gate_system_veto_root(mock_db, base_intent):
    agent_id_mock = AgentIdentity(
        id="agent-001",
        tenant_id="test-workspace",
        name="Test Agent",
        created_by_pgl_id="user-01",
        metadata_json={"trust_score": 90},
    )

    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query).lower()
        if "agent_identities" in query_str:
            mock_val.scalar_one_or_none.return_value = agent_id_mock
        else:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    base_intent.target_protocol = "syscall_execute"
    base_intent.payload = {
        "command": "sudo rm -rf /",
        "random": str(__import__("uuid").uuid4()),
    }

    is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(
        base_intent, mock_db, "test-workspace"
    )

    assert not is_approved
    assert reason == "SYSTEM_POLICY_VETO"
    assert failure_phase == 2


@pytest.mark.anyio
async def test_capi_gate_implicit_deny(mock_db, base_intent):
    agent_id_mock = AgentIdentity(
        id="agent-001",
        tenant_id="test-workspace",
        name="Test Agent",
        created_by_pgl_id="user-01",
        metadata_json={"trust_score": 90},
    )
    bundle_mock = AuthorityBundle(
        id="bundle-1",
        workspace_id="test-workspace",
        creator_id="user-01",
        tool_permissions={"other_tool": "ALLOW"},
    )

    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query).lower()
        if "agent_identities" in query_str:
            mock_val.scalar_one_or_none.return_value = agent_id_mock
        elif "authority_bundles" in query_str:
            mock_val.scalar_one_or_none.return_value = bundle_mock
        else:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(
        base_intent, mock_db, "test-workspace"
    )

    assert not is_approved
    assert reason == "NO_EXPLICIT_ALLOW_RULE"
    assert failure_phase == 2


@pytest.mark.anyio
async def test_capi_gate_approval_escalation(mock_db, base_intent):
    agent_id_mock = AgentIdentity(
        id="agent-001",
        tenant_id="test-workspace",
        name="Test Agent",
        created_by_pgl_id="user-01",
        metadata_json={"trust_score": 90},
    )
    bundle_mock = AuthorityBundle(
        id="bundle-1",
        workspace_id="test-workspace",
        creator_id="user-01",
        tool_permissions={"db.drop_tables": "ALLOW"},
    )

    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query).lower()
        if "agent_identities" in query_str:
            mock_val.scalar_one_or_none.return_value = agent_id_mock
        elif "authority_bundles" in query_str:
            mock_val.scalar_one_or_none.return_value = bundle_mock
        else:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    base_intent.action = "db.drop_tables"
    is_approved, reason, failure_phase, phase_results = await evaluate_intent_governed(
        base_intent, mock_db, "test-workspace"
    )

    assert not is_approved
    assert reason == "PENDING_APPROVAL"
    assert failure_phase == 5


@pytest.mark.anyio
async def test_capi_execution_approved(mock_db, base_intent, monkeypatch):
    agent_id_mock = AgentIdentity(
        id="agent-001",
        tenant_id="test-workspace",
        name="Test Agent",
        created_by_pgl_id="user-01",
        metadata_json={"trust_score": 90},
    )
    bundle_mock = AuthorityBundle(
        id="bundle-1",
        workspace_id="test-workspace",
        creator_id="user-01",
        tool_permissions={"mcp": "ALLOW"},
    )
    run_mock = AuthorityRun(
        id="run-1",
        authority_bundle_id="bundle-1",
        agent_id="agent-001",
        workspace_id="test-workspace",
        executor_id="test-user-id",
    )

    # Ensure db async methods are awaitable
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.rollback = AsyncMock()

    async def mock_execute(query):
        mock_val = MagicMock()
        query_str = str(query).lower()
        if "agent_identities" in query_str:
            mock_val.scalar_one_or_none.return_value = agent_id_mock
        elif "authority_bundles" in query_str:
            mock_val.scalar_one_or_none.return_value = bundle_mock
        elif "authority_runs" in query_str:
            mock_val.scalar_one_or_none.return_value = run_mock
        elif "evidence_packs" in query_str:
            mock_val.scalar_one_or_none.return_value = "prev-hash-123"
        else:
            mock_val.scalar_one_or_none.return_value = None
        return mock_val

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    monkeypatch.setattr("backend.apps.api.routers.capi.redis_cache.enabled", False)
    monkeypatch.setattr("backend.apps.api.routers.capi.redis_cache.client", None)
    router.local_intent_cache = {}
    principal = {"workspace_id": "test-workspace", "sub": "test-user-id"}
    execution = await governed_execution_intercept(
        intent=base_intent,
        db=mock_db,
        principal=principal,
    )
    assert execution["run_id"]
    assert execution["stream_token"]

    response = await stream_run(
        run_id=execution["run_id"],
        db=mock_db,
        principal=principal,
    )

    receipt_data = None
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunk_str = chunk.decode("utf-8")
        else:
            chunk_str = chunk

        for line in chunk_str.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                parsed = json.loads(line[6:])
                if parsed.get("event") == "run.receipt":
                    receipt_data = parsed.get("payload")

    assert (
        receipt_data is not None
    ), "Receipt data was not found in the StreamingResponse stream"
    assert receipt_data["settlement_status"] == "yielded"
    assert receipt_data["receipt_id"].startswith("EV-")
    assert receipt_data["amount_vnp"] > 0
