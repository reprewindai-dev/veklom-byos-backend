from datetime import datetime, timedelta, timezone

def _route_for_provider(provider: str | None) -> str:
    value = (provider or "").strip().lower()
    if value in {"anthropic", "bedrock", "aws"}:
        return "aws-burst"
    return "hetzner"

def _routing_history(rows: list, now: datetime) -> list[dict]:
    buckets = {
        hour: {"hour": f"{hour:02d}", "hetzner": 0, "aws": 0}
        for hour in range(24)
    }
    for row in rows:
        created_at = row.created_at
        if not created_at:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        hour_age = int((now - created_at).total_seconds() // 3600)
        if hour_age < 0 or hour_age > 23:
            continue
        bucket = buckets[created_at.hour]
        if _route_for_provider(row.provider) == "aws-burst":
            bucket["aws"] += 1
        else:
            bucket["hetzner"] += 1
    return list(buckets.values())

class DummyRow:
    def __init__(self, created_at, provider):
        self.created_at = created_at
        self.provider = provider

now = datetime.now(timezone.utc)
rows = [
    DummyRow(now - timedelta(hours=1), "aws"),
    DummyRow(now - timedelta(hours=2), "hetzner"),
]

print(_routing_history(rows, now))
