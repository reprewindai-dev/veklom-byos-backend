import pytest
from backend.core.security.schema_moat import verify_schema_depth

def test_verify_schema_depth_shallow():
    # Base cases
    verify_schema_depth("string")
    verify_schema_depth(123)
    verify_schema_depth({"a": 1, "b": "string"})
    verify_schema_depth([1, 2, 3])

def test_verify_schema_depth_nested_dict_pass():
    # Should pass up to depth 6.
    # Data is evaluated as follows:
    # depth 1: {"a": ...}
    # depth 2: {"b": ...}
    # depth 3: {"c": ...}
    # depth 4: {"d": ...}
    # depth 5: {"e": ...}
    # depth 6: "value" (scalar) -> verified at depth 6!
    data = {"a": {"b": {"c": {"d": {"e": "value"}}}}}
    verify_schema_depth(data, max_depth=6)

def test_verify_schema_depth_nested_dict_fail():
    # Should fail at depth 7
    # depth 1: {"a": ...}
    # depth 2: {"b": ...}
    # depth 3: {"c": ...}
    # depth 4: {"d": ...}
    # depth 5: {"e": ...}
    # depth 6: {"f": ...}
    # depth 7: "value" (scalar) -> verified at depth 7 (fails if max_depth=6)
    data = {"a": {"b": {"c": {"d": {"e": {"f": "value"}}}}}}
    with pytest.raises(ValueError, match="Schema depth limit exceeded"):
        verify_schema_depth(data, max_depth=6)

def test_verify_schema_depth_nested_list_pass():
    # Lists
    # depth 1: [...]
    # depth 2: [...]
    # depth 3: [...]
    # depth 4: [...]
    # depth 5: [...]
    # depth 6: "value"
    data = [[[[["value"]]]]]
    verify_schema_depth(data, max_depth=6)

def test_verify_schema_depth_nested_list_fail():
    # Lists
    # depth 1: [...]
    # depth 2: [...]
    # depth 3: [...]
    # depth 4: [...]
    # depth 5: [...]
    # depth 6: [...]
    # depth 7: "value"
    data = [[[[[["value"]]]]]]
    with pytest.raises(ValueError, match="Schema depth limit exceeded"):
        verify_schema_depth(data, max_depth=6)

def test_verify_schema_depth_mixed_pass():
    # Mixed lists and dicts
    # depth 1: dict {"a": ...}
    # depth 2: list [...]
    # depth 3: dict {"b": ...}
    # depth 4: list [...]
    # depth 5: integer 1 -> passes max_depth 5
    data = {"a": [{"b": [1, 2, 3]}]}
    verify_schema_depth(data, max_depth=5)

def test_verify_schema_depth_mixed_fail():
    # Mixed lists and dicts
    # depth 1: dict {"a": ...}
    # depth 2: list [...]
    # depth 3: dict {"b": ...}
    # depth 4: dict {"c": ...}
    # depth 5: list [...]
    # depth 6: dict {"d": 1}
    # depth 7: 1 (fails at max_depth 4 earlier)
    data = {"a": [{"b": {"c": [{"d": 1}]}}]}
    with pytest.raises(ValueError, match="Schema depth limit exceeded"):
        verify_schema_depth(data, max_depth=4)

def test_verify_schema_depth_custom_max_depth():
    # depth 1: dict {"a": ...}
    # depth 2: dict {"b": 1}
    # depth 3: 1 -> fails if max_depth=2, passes if max_depth=3!
    data = {"a": {"b": 1}}
    verify_schema_depth(data, max_depth=3)
    with pytest.raises(ValueError, match="Schema depth limit exceeded"):
        verify_schema_depth(data, max_depth=2)
