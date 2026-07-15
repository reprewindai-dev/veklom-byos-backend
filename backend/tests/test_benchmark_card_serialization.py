import enum

from backend.apps.api.routers.benchmarks import _enum_value


class ExampleState(str, enum.Enum):
    open = "open"


def test_benchmark_card_enum_value_accepts_enums_and_plain_strings():
    assert _enum_value(ExampleState.open) == "open"
    assert _enum_value("open") == "open"
    assert _enum_value(None) is None
