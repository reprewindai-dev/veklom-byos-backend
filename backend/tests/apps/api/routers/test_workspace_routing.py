import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from backend.apps.api.routers.workspace import _routing_history, _route_for_provider

def test_routing_history_with_mocked_rows():
    now = datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc)

    class MockRow:
        def __init__(self, provider, created_at):
            self.provider = provider
            self.created_at = created_at

    # Create some mock rows that represent what SQLAlchemy Row objects would contain
    # for the select(ExecLog.provider, ExecLog.created_at) query
    rows = [
        MockRow(provider="anthropic", created_at=now - timedelta(minutes=30)), # hour 11
        MockRow(provider="openai", created_at=now - timedelta(hours=1, minutes=30)), # hour 10
        MockRow(provider="bedrock", created_at=now - timedelta(hours=2)), # hour 10
        MockRow(provider="ollama", created_at=now - timedelta(hours=23)), # hour 13 (previous day)
    ]

    history = _routing_history(rows, now)

    assert len(history) == 24

    # Check hour 11
    hour_11 = next(b for b in history if b["hour"] == "11")
    assert hour_11["aws"] == 1
    assert hour_11["hetzner"] == 0

    # Check hour 10
    hour_10 = next(b for b in history if b["hour"] == "10")
    assert hour_10["aws"] == 1
    assert hour_10["hetzner"] == 1

    # Check hour 13
    hour_13 = next(b for b in history if b["hour"] == "13")
    assert hour_13["aws"] == 0
    assert hour_13["hetzner"] == 1

    # Verify exact provider routing logic
    assert _route_for_provider("anthropic") == "aws-burst"
    assert _route_for_provider("bedrock") == "aws-burst"
    assert _route_for_provider("aws") == "aws-burst"
    assert _route_for_provider("openai") == "hetzner"
    assert _route_for_provider("ollama") == "hetzner"

    # Also verify Hetzner/AWS counts calculate identical as original logic
    hetzner_count = sum(1 for row in rows if _route_for_provider(row.provider) == "hetzner")
    aws_count = sum(1 for row in rows if _route_for_provider(row.provider) == "aws-burst")

    assert hetzner_count == 2
    assert aws_count == 2
