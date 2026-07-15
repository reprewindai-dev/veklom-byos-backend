import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.apps.api.routers import monitoring


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _OneRowResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeRedisCache:
    def __init__(self, cached=None):
        self.cached = cached
        self.set_calls = []

    async def get(self, key):
        return self.cached.get(key) if isinstance(self.cached, dict) else self.cached

    async def set(self, key, value, ttl=3600):
        self.set_calls.append((key, json.loads(value), ttl))
        return True


@pytest.fixture
def user():
    mock = MagicMock()
    mock.workspace_id = "workspace-001"
    return mock


@pytest.mark.anyio
async def test_insights_summary_uses_cached_result_without_db(monkeypatch, user):
    cached = {
        "total_requests_today": 12,
        "avg_latency_ms": 88,
        "error_rate_percent": 0.0,
        "top_models": [{"model": "openai", "calls": 12}],
        "provider_split": {"openai": 1.0},
        "total_requests_30d": 12,
        "total_cost_30d": 0.123,
        "avg_tokens_per_request": 0,
        "peak_hour_requests": 0,
    }
    monkeypatch.setattr(
        monitoring,
        "redis_cache",
        _FakeRedisCache({"insights:summary:workspace-001": json.dumps(cached)}),
    )
    db = MagicMock()
    db.execute = AsyncMock()

    result = await monitoring.insights_summary(user=user, db=db)

    assert result == cached
    db.execute.assert_not_called()


@pytest.mark.anyio
async def test_insights_summary_caches_database_result(monkeypatch, user):
    fake_cache = _FakeRedisCache()
    monkeypatch.setattr(monitoring, "redis_cache", fake_cache)
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_RowsResult(
            [
                ("openai", 0.12, 3, 100),
                ("anthropic", 0.08, 1, 200),
            ]
        )
    )

    result = await monitoring.insights_summary(user=user, db=db)

    assert result["total_requests_today"] == 4
    assert result["avg_latency_ms"] == 125
    assert result["provider_split"] == {"openai": 0.75, "anthropic": 0.25}
    assert fake_cache.set_calls == [("insights:summary:workspace-001", result, 300)]


@pytest.mark.anyio
async def test_insights_savings_caches_database_result(monkeypatch, user):
    fake_cache = _FakeRedisCache()
    monkeypatch.setattr(monitoring, "redis_cache", fake_cache)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_OneRowResult((10_000, 0.05)))

    result = await monitoring.insights_savings(user=user, db=db)

    assert result == {
        "total_saved_usd": 0.25,
        "routing_savings": 0.2,
        "caching_savings": 0.05,
        "policy_savings": 0.0,
    }
    assert fake_cache.set_calls == [("insights:savings:workspace-001", result, 300)]


@pytest.mark.anyio
async def test_performance_metrics_caches_database_result(monkeypatch, user):
    fake_cache = _FakeRedisCache()
    monkeypatch.setattr(monitoring, "redis_cache", fake_cache)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_OneRowResult((9, 40)))

    result = await monitoring.performance_metrics(user=user, db=db)

    assert result == {
        "p50_ms": 40,
        "p90_ms": 60,
        "p99_ms": 100,
        "throughput_rps": 9,
        "error_rate": 0.0,
    }
    assert fake_cache.set_calls == [("metrics:performance:workspace-001", result, 300)]
