import pytest
import hashlib
from backend.services.anchoring import create_merkle_root

def test_create_merkle_root_empty():
    assert create_merkle_root([]) == "0x0000000000000000000000000000000000000000000000000000000000000000"

def test_create_merkle_root_single():
    h = hashlib.sha256(b"A").hexdigest()
    assert create_merkle_root([h]) == "0x" + h

def test_create_merkle_root_even():
    h1 = hashlib.sha256(b"A").hexdigest()
    h2 = hashlib.sha256(b"B").hexdigest()
    expected = "0x" + hashlib.sha256((h1 + h2).encode('utf-8')).hexdigest()
    assert create_merkle_root([h1, h2]) == expected

def test_create_merkle_root_odd():
    h1 = hashlib.sha256(b"A").hexdigest()
    h2 = hashlib.sha256(b"B").hexdigest()
    h3 = hashlib.sha256(b"C").hexdigest()

    # First level pairs
    l1_h12 = hashlib.sha256((h1 + h2).encode('utf-8')).hexdigest()
    l1_h33 = hashlib.sha256((h3 + h3).encode('utf-8')).hexdigest() # Odd node paired with itself

    # Second level
    expected = "0x" + hashlib.sha256((l1_h12 + l1_h33).encode('utf-8')).hexdigest()
    assert create_merkle_root([h1, h2, h3]) == expected
