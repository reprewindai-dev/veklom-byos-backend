import uuid
import hashlib
import json

from backend.services.pgl_client import _hash_event

def test_hash_event_no_prev():
    payload = {"key1": "value1", "key2": 2}
    expected_hash = "5474f93e6ccfb674022e544d7ba1acec291ad195e41f1190f940d6cd80e08748"
    result = _hash_event(payload, None)
    assert result == expected_hash

def test_hash_event_with_prev():
    payload = {"key1": "value1"}
    prev_hash = "abc123def456"
    expected_hash = "ce82d887674357ae2a68f62a662d5d8920e44127fc91298b78bc7efd86291f44"
    result = _hash_event(payload, prev_hash)
    assert result == expected_hash

def test_hash_event_deterministic_key_order():
    payload1 = {"a": 1, "b": 2, "c": 3}
    payload2 = {"c": 3, "a": 1, "b": 2}
    hash1 = _hash_event(payload1, None)
    hash2 = _hash_event(payload2, None)
    assert hash1 == hash2
