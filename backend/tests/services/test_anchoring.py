import hashlib
from backend.services.anchoring import create_merkle_root

def test_create_merkle_root_empty():
    assert create_merkle_root([]) == "0x0000000000000000000000000000000000000000000000000000000000000000"

def test_create_merkle_root_single():
    h = "a" * 64
    assert create_merkle_root([h]) == "0x" + h

def test_create_merkle_root_even():
    h1 = "a" * 64
    h2 = "b" * 64
    expected_hash = hashlib.sha256((h1 + h2).encode('utf-8')).hexdigest()
    assert create_merkle_root([h1, h2]) == "0x" + expected_hash

def test_create_merkle_root_odd():
    h1 = "a" * 64
    h2 = "b" * 64
    h3 = "c" * 64

    # First level pairs: (h1, h2), (h3, h3)
    l2_1 = hashlib.sha256((h1 + h2).encode('utf-8')).hexdigest()
    l2_2 = hashlib.sha256((h3 + h3).encode('utf-8')).hexdigest()

    # Second level pair: (l2_1, l2_2)
    expected_hash = hashlib.sha256((l2_1 + l2_2).encode('utf-8')).hexdigest()

    assert create_merkle_root([h1, h2, h3]) == "0x" + expected_hash
