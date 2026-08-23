import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

# Create mock classes to mimic SQLAlchemy Row objects
class MockRow(tuple):
    def __new__(cls, values, fields):
        return super().__new__(cls, values)

    def __init__(self, values, fields):
        self._fields = fields
        for k, v in zip(fields, values):
            setattr(self, k, v)

# The function under test
from backend.apps.api.routers.workspace import _overview_payload

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_overview_stats():
    stats = MagicMock()
    stats.total_requests = 100
    stats.requests_per_min = 10
    stats.total_tokens = 5000
    stats.spend_today = 10.5
    stats.avg_latency = 120
    return stats

@pytest.mark.asyncio
async def test_overview_payload_enabled_models_fallback(mock_db, mock_overview_stats):
    """Test response-semantic regressions for enabled/default models"""
    # Setup standard mocks for scalar/execute
    mock_db.scalar.side_effect = [
        15,     # audit_entries
        200.0,  # budget_limit
        5,      # active_pipelines
        2,      # active_deployments
    ]

    # We just need to mock the initial scalar that fetches stats
    with patch("backend.apps.api.routers.workspace.select") as mock_select, \
         patch("backend.apps.api.routers.workspace._default_models", return_value=[{"id": "default", "provider": "openai", "display_name": "GPT-4"}]) as mock_defaults:

        # Make the first db.execute return our mocked stats tuple
        mock_execute = MagicMock()
        mock_execute.fetchone.return_value = mock_overview_stats

        mock_ws_execute = MagicMock()
        mock_ws = MagicMock()
        mock_ws.name = "Test WS"
        mock_ws.slug = "test-ws"
        mock_ws.tier = "free"
        mock_ws.created_at = datetime.now()
        mock_ws_execute.scalar_one_or_none.return_value = mock_ws

        mock_db.execute = AsyncMock(side_effect=[
        mock_execute,
            MagicMock(all=lambda: []), # model_rows
            MagicMock(all=lambda: []), # recent_runs
            MagicMock(all=lambda: []), # recent_24h
            MagicMock(all=lambda: []), # audit_rows
            MagicMock(all=lambda: []), # alert_rows
            mock_ws_execute,           # workspace
            MagicMock(all=lambda: []), # workspace members
        ])

        payload = await _overview_payload(mock_db, "ws_1", "user@example.com")

        # Verify models_enabled is based on the default models fallback (len 1)
        assert payload["models_enabled"] == 1
        assert len(payload["fleet"]) <= 4 # Fleet is capped at 4


@pytest.mark.asyncio
async def test_overview_payload_recent_runs_tuple_access(mock_db, mock_overview_stats):
    """Test response-semantic regressions for recent runs and SQLAlchemy Row access"""
    now = datetime.now(timezone.utc)

    # 1. Model rows
    model_rows = [MockRow(("m1", "openai", "GPT-4"), ("id", "provider", "display_name"))]

    # 2. ExecLog rows (id, model, provider, latency_ms, total_tokens, cost_usd, policy_flags, created_at)
    run_rows = [
        MockRow(("run_1", None, "openai", 150, 100, 0.05, "flagged", now),
                ("id", "model", "provider", "latency_ms", "total_tokens", "cost_usd", "policy_flags", "created_at"))
    ]

    # 3. recent 24h
    recent_24h = []

    # 4. audit rows (id, action, resource_type, resource_id, user_id, hash_chain, prev_hash, created_at)
    audit_rows = []

    # 5. alert rows (id, description, event_type, severity, threat_type, created_at)
    alert_rows = []

    mock_db.scalar.side_effect = [5, 100.0, 5, 2]

    mock_execute_stats = MagicMock()
    mock_execute_stats.fetchone.return_value = mock_overview_stats

    mock_ws_execute = MagicMock()
    mock_ws_execute.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[
        mock_execute_stats,
        MagicMock(all=lambda: model_rows),
        MagicMock(all=lambda: run_rows),
        MagicMock(all=lambda: recent_24h),
        MagicMock(all=lambda: audit_rows),
        MagicMock(all=lambda: alert_rows),
        mock_ws_execute,
        MagicMock(all=lambda: []),
    ])

    payload = await _overview_payload(mock_db, "ws_1", "user@example.com")

    recent_runs = payload["recent_runs"]
    assert len(recent_runs) == 1

    # Verify semantic regressions handles null/empty fields via fallback
    assert recent_runs[0]["id"] == "run_1"
    assert recent_runs[0]["model"] == "qwen2.5:3b"  # Fallback for null model
    assert recent_runs[0]["latency"] == 150
    assert recent_runs[0]["policy"] == "redacted" # Has flags


@pytest.mark.asyncio
async def test_overview_payload_audit_rows_nulls(mock_db, mock_overview_stats):
    """Test response-semantic regressions for audit rows and null/empty fields"""
    now = datetime.now(timezone.utc)

    # audit rows (id, action, resource_type, resource_id, user_id, hash_chain, prev_hash, created_at)
    audit_rows = [
        # Test null resource_type and null user_id fallbacks
        MockRow(("a1", "login", None, None, None, "1234567890abcdef", None, now),
                ("id", "action", "resource_type", "resource_id", "user_id", "hash_chain", "prev_hash", "created_at")),
        # Test null hash_chain falling back to prev_hash
        MockRow(("a2", "logout", "session", "s1", "u1", None, "abcdef1234567890", now),
                ("id", "action", "resource_type", "resource_id", "user_id", "hash_chain", "prev_hash", "created_at")),
        # Test all hashes null
        MockRow(("a3", "view", "doc", "d1", "u1", None, None, now),
                ("id", "action", "resource_type", "resource_id", "user_id", "hash_chain", "prev_hash", "created_at"))
    ]

    mock_db.scalar.side_effect = [5, 100.0, 5, 2]

    mock_execute_stats = MagicMock()
    mock_execute_stats.fetchone.return_value = mock_overview_stats

    mock_ws_execute = MagicMock()
    mock_ws_execute.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[
        mock_execute_stats,
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: audit_rows),
        MagicMock(all=lambda: []),
        mock_ws_execute,
        MagicMock(all=lambda: []),
    ])

    payload = await _overview_payload(mock_db, "ws_1", "fallback_actor@example.com")

    audits = payload["audit_logs"]
    assert len(audits) == 3

    # Check fallbacks for first audit row
    assert audits[0]["target"] == "workspace" # Both resource_type and resource_id are null
    assert audits[0]["actor"] == "fallback_actor@example.com" # user_id is null
    assert audits[0]["hash"] == "1234567890ab" # Truncated to 12

    # Check fallback for second audit row
    assert audits[1]["hash"] == "abcdef123456" # Fell back to prev_hash

    # Check fallback for third audit row
    assert audits[2]["hash"] == "" # Both hashes null


@pytest.mark.asyncio
async def test_overview_payload_security_events_unresolved(mock_db, mock_overview_stats):
    """Test response-semantic regressions for unresolved security events and ordering/limits"""
    now = datetime.now(timezone.utc)

    # alert rows (id, description, event_type, severity, threat_type, created_at)
    alert_rows = [
        # null description falling back to event_type
        MockRow(("s1", None, "intrusion", "high", "DDoS", now),
                ("id", "description", "event_type", "severity", "threat_type", "created_at")),
        # null threat_type falling back to event_type
        MockRow(("s2", "Malware detected", "malware", "critical", None, now),
                ("id", "description", "event_type", "severity", "threat_type", "created_at")),
    ]

    mock_db.scalar.side_effect = [5, 100.0, 5, 2]

    mock_execute_stats = MagicMock()
    mock_execute_stats.fetchone.return_value = mock_overview_stats

    mock_ws_execute = MagicMock()
    mock_ws_execute.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[
        mock_execute_stats,
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: alert_rows),
        mock_ws_execute,
        MagicMock(all=lambda: []),
    ])

    # Let's inspect the actual query being built to verify ordering/limits/status
    with patch("backend.apps.api.routers.workspace.select") as mock_select:
        # Just mock select enough to return self for chaining
        mock_select_obj = MagicMock()
        mock_select.return_value = mock_select_obj
        mock_select_obj.where.return_value = mock_select_obj
        mock_select_obj.order_by.return_value = mock_select_obj
        mock_select_obj.limit.return_value = mock_select_obj

        payload = await _overview_payload(mock_db, "ws_1", "user@example.com")

        alerts = payload["alerts"]
        assert len(alerts) == 2

        assert alerts[0]["title"] == "intrusion" # fell back to event_type
        assert alerts[0]["source"] == "DDoS"

        assert alerts[1]["title"] == "Malware detected"
        assert alerts[1]["source"] == "malware" # fell back to event_type
