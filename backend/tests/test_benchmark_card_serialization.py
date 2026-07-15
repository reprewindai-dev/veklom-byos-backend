import enum

from uuid import UUID

from backend.apps.api.routers.benchmarks import _enum_value, _uuid_or_none


class ExampleState(str, enum.Enum):
    open = "open"


def test_benchmark_card_enum_value_accepts_enums_and_plain_strings():
    assert _enum_value(ExampleState.open) == "open"
    assert _enum_value("open") == "open"
    assert _enum_value(None) is None


def test_benchmark_card_identifier_accepts_live_metrics_uuid_ids():
    live_metrics_id = "d06b8cc0-b8a2-4153-9243-da5894c0265f"
    assert _uuid_or_none(live_metrics_id) == UUID(live_metrics_id)
    assert _uuid_or_none("did:veklom:guard") is None
