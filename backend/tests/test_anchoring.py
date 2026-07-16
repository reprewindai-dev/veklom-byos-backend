import pytest
from backend.services.anchoring import create_merkle_root

def test_create_merkle_root_empty():
    expected = "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert create_merkle_root([]) == expected

def test_create_merkle_root_none():
    expected = "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert create_merkle_root(None) == expected
