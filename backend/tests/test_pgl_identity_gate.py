import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from collections import namedtuple

from backend.core.services.pgl_identity_gate import PGLIdentityGate, PGLIdentityExpired, AgentKind
from backend.db.models.pgl import PGLIdentity, PGLCertificate

@pytest.mark.asyncio
@patch("backend.core.database.redis_client.redis_client", new_callable=AsyncMock)
async def test_require_hard_expired_identity_raises_exception(mock_redis):
    session = AsyncMock()

    mock_identity = PGLIdentity(
        id="test-pgl-id",
        tenant_id="test-actor",
        primary_public_key="key",
        created_at=datetime.now(timezone.utc) - timedelta(days=400),
        metadata_json={}
    )

    MockResult = namedtuple("MockResult", ["scalar_one_or_none", "one_or_none", "scalars"])

    async def mock_execute(*args, **kwargs):
        return MockResult(
            scalar_one_or_none=lambda: None,
            one_or_none=lambda: (0, 0),
            scalars=lambda: None
        )

    session.execute = mock_execute

    with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._resolve_registered_agent", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = mock_identity

        with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._check_status", new_callable=MagicMock) as mock_check_status:
            mock_check_status.return_value = None

            with pytest.raises(PGLIdentityExpired) as exc_info:
                await PGLIdentityGate.require(
                    db=session,
                    actor_id="test-actor",
                    action="test-action",
                    payload={"key": "val"},
                    kind=AgentKind.REGISTERED,
                    scope="test-scope"
                )

    assert exc_info.value.actor_id == "test-actor"
    assert "Identity is hard-blocked and must be re-registered" in exc_info.value.reason or "expired" in exc_info.value.reason.lower()


@pytest.mark.asyncio
@patch("backend.core.database.redis_client.redis_client", new_callable=AsyncMock)
async def test_require_lifecycle_failure_raises_exception(mock_redis):
    session = AsyncMock()

    mock_identity = PGLIdentity(
        id="test-pgl-id",
        tenant_id="test-actor",
        primary_public_key="key",
        created_at=datetime.now(timezone.utc),
        metadata_json={}
    )

    async def mock_execute(*args, **kwargs):
        raise ValueError("Simulated DB failure inside stats fetching")

    session.execute = mock_execute

    with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._resolve_registered_agent", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = mock_identity

        with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._check_status", new_callable=MagicMock) as mock_check_status:
            mock_check_status.return_value = None

            from backend.core.services.pgl_identity_gate import PGLIdentityError
            with patch("backend.services.pgl_client.PGLClient.commit_intent", new_callable=AsyncMock) as mock_commit_intent:
                with pytest.raises(PGLIdentityError) as exc_info:
                    await PGLIdentityGate.require(
                        db=session,
                        actor_id="test-actor",
                        action="test-action",
                        payload={"key": "val"},
                        kind=AgentKind.REGISTERED,
                        scope="test-scope"
                    )
                mock_commit_intent.assert_not_called()

    assert exc_info.value.actor_id == "test-actor"
    assert "Simulated DB failure" not in exc_info.value.reason
    assert "Identity lifecycle evaluation unavailable" in exc_info.value.reason


@pytest.mark.asyncio
@patch("backend.core.database.redis_client.redis_client", new_callable=AsyncMock)
async def test_require_lifecycle_module_failure_fails_closed_before_commit(mock_redis):
    from backend.core.services.pgl_identity_gate import PGLIdentityError

    session = AsyncMock()
    mock_identity = PGLIdentity(
        id="test-pgl-id",
        tenant_id="test-actor",
        primary_public_key="key",
        created_at=datetime.now(timezone.utc),
        metadata_json={},
    )

    stats_result = MagicMock()
    stats_result.one_or_none.return_value = (0, 0)
    session.execute = AsyncMock(return_value=stats_result)

    with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._resolve_registered_agent", new_callable=AsyncMock) as mock_resolve, \
         patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._check_status"), \
         patch("backend.core.services.pgl_identity_lifecycle.compute_lifecycle", side_effect=RuntimeError("lifecycle module unavailable")), \
         patch("backend.services.pgl_client.PGLClient.commit_intent", new_callable=AsyncMock) as mock_commit_intent:
        mock_resolve.return_value = mock_identity

        with pytest.raises(PGLIdentityError) as exc_info:
            await PGLIdentityGate.require(
                db=session,
                actor_id="test-actor",
                action="test-action",
                payload={"key": "val"},
                kind=AgentKind.REGISTERED,
                scope="test-scope",
            )

        mock_commit_intent.assert_not_called()

    assert exc_info.value.reason == "Identity lifecycle evaluation unavailable"
    assert "lifecycle module unavailable" not in exc_info.value.reason


@pytest.mark.asyncio
@patch("backend.core.database.redis_client.redis_client", new_callable=AsyncMock)
async def test_require_healthy_active_identity_reaches_commit_intent(mock_redis):
    from backend.core.services.pgl_identity_lifecycle import TrustLevel

    session = AsyncMock()
    mock_identity = PGLIdentity(
        id="test-pgl-id",
        tenant_id="test-workspace",
        primary_public_key="key",
        created_at=datetime.now(timezone.utc) - timedelta(days=120),
        metadata_json={"genome_hash": "genome", "constitution_hash": "constitution"},
    )

    stats_result = MagicMock()
    stats_result.one_or_none.return_value = (5, 0)
    no_agent_result = MagicMock()
    no_agent_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[stats_result, no_agent_result])

    lifecycle = MagicMock()
    lifecycle.trust_level = TrustLevel.ACTIVE
    lifecycle.renewal_due_at = datetime.now(timezone.utc) + timedelta(days=30)
    lifecycle.days_until_renewal = 30

    pre_cert = {
        "pre_execution_certificate_id": "pre-cert-1",
        "persisted": True,
        "signature": "test-signature",
        "expires_at": None,
    }

    with patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._resolve_registered_agent", new_callable=AsyncMock) as mock_resolve, \
         patch("backend.core.services.pgl_identity_gate.PGLIdentityGate._check_status"), \
         patch("backend.core.services.pgl_identity_lifecycle.compute_lifecycle", return_value=lifecycle), \
         patch("backend.core.services.pgl_notifications.notify_active") as mock_notify_active, \
         patch("backend.services.pgl_client.PGLClient.commit_intent", new_callable=AsyncMock) as mock_commit_intent:
        mock_resolve.return_value = mock_identity
        mock_notify_active.return_value.to_dict.return_value = {"status": "active"}
        mock_commit_intent.return_value = pre_cert

        context = await PGLIdentityGate.require(
            db=session,
            actor_id="test-actor",
            action="test-action",
            payload={"key": "val"},
            kind=AgentKind.REGISTERED,
            scope="test-scope",
        )

    mock_commit_intent.assert_awaited_once()
    assert context.actor_id == "test-actor"
    assert context.workspace_id == "test-workspace"
    assert context.pre_execution_cert_id == "pre-cert-1"
    assert context.trust_level == TrustLevel.ACTIVE.value
