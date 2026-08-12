from collections import namedtuple
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.services.pgl_identity_gate import AgentKind, PGLIdentityExpired, PGLIdentityGate
from backend.db.models.pgl import PGLIdentity


@pytest.mark.asyncio
@patch("backend.core.database.redis_client.redis_client", new_callable=AsyncMock)
async def test_require_hard_expired_identity_raises_exception(mock_redis):
    # Setup mock db session
    session = AsyncMock()

    # Setup mock identity to be older than RENEWAL_INTERVAL_DAYS + GRACE_PERIOD_DAYS
    # 365 + 14 = 379 days
    mock_identity = PGLIdentity(
        id="test-pgl-id",
        tenant_id="test-actor",
        primary_public_key="key",
        created_at=datetime.now(timezone.utc) - timedelta(days=400),
        metadata_json={}
    )

    MockResult = namedtuple("MockResult", ["scalar_one_or_none", "one_or_none", "scalars"])

    # Provide the execution behavior.
    # The first call in PGLIdentityGate.require is for stats_result (since we mock _resolve_registered_agent)
    # The new optimized query returns a row tuple using one_or_none()
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
            mock_check_status.return_value = None # Doesn't raise exception

            with pytest.raises(PGLIdentityExpired) as exc_info:
                await PGLIdentityGate.require(
                    db=session,
                    actor_id="test-actor",
                    action="test-action",
                    payload={"key": "val"},
                    kind=AgentKind.REGISTERED,
                    scope="test-scope"
                )

    # Verify the exception is raised due to hard expiration
    assert exc_info.value.actor_id == "test-actor"
    assert "Identity is hard-blocked and must be re-registered" in exc_info.value.reason or "expired" in exc_info.value.reason.lower()

@pytest.mark.asyncio
@patch("backend.core.database.redis_client.redis_client", new_callable=AsyncMock)
async def test_require_lifecycle_failure_raises_exception(mock_redis):
    # Ensures a generic exception inside the lifecycle block raises PGLIdentityError
    session = AsyncMock()

    mock_identity = PGLIdentity(
        id="test-pgl-id",
        tenant_id="test-actor",
        primary_public_key="key",
        created_at=datetime.now(timezone.utc),
        metadata_json={}
    )

    MockResult = namedtuple("MockResult", ["scalar_one_or_none", "one_or_none", "scalars"])

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
                # Assert commit_intent is not reached when lifecycle fails
                mock_commit_intent.assert_not_called()

    assert exc_info.value.actor_id == "test-actor"
    # Assert the internal error is NOT leaked to the caller
    assert "Simulated DB failure" not in exc_info.value.reason
    assert "Identity lifecycle evaluation unavailable" in exc_info.value.reason
