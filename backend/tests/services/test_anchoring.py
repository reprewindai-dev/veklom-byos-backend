import hashlib
from backend.services.anchoring import create_merkle_root

def test_create_merkle_root_empty():
    """Test with an empty list of hashes."""
    assert create_merkle_root([]) == "0x0000000000000000000000000000000000000000000000000000000000000000"

def test_create_merkle_root_single_hash():
    """Test with a single hash. It should return 0x + the hash without any hashing."""
    h = hashlib.sha256(b"test").hexdigest()
    assert create_merkle_root([h]) == "0x" + h

def test_create_merkle_root_two_hashes():
    """Test with two hashes."""
    h1 = hashlib.sha256(b"test1").hexdigest()
    h2 = hashlib.sha256(b"test2").hexdigest()

    expected = hashlib.sha256((h1 + h2).encode('utf-8')).hexdigest()
    assert create_merkle_root([h1, h2]) == "0x" + expected

def test_create_merkle_root_odd_hashes():
    """Test with an odd number of hashes (e.g. 3). Tests duplication logic."""
    h1 = hashlib.sha256(b"test1").hexdigest()
    h2 = hashlib.sha256(b"test2").hexdigest()
    h3 = hashlib.sha256(b"test3").hexdigest()

    # First level: h1+h2, h3+h3
    level_1_1 = hashlib.sha256((h1 + h2).encode('utf-8')).hexdigest()
    level_1_2 = hashlib.sha256((h3 + h3).encode('utf-8')).hexdigest()

    # Second level: level_1_1 + level_1_2
    expected = hashlib.sha256((level_1_1 + level_1_2).encode('utf-8')).hexdigest()

    assert create_merkle_root([h1, h2, h3]) == "0x" + expected

def test_create_merkle_root_four_hashes():
    """Test with a power-of-two number of hashes (e.g. 4)."""
    h1 = hashlib.sha256(b"test1").hexdigest()
    h2 = hashlib.sha256(b"test2").hexdigest()
    h3 = hashlib.sha256(b"test3").hexdigest()
    h4 = hashlib.sha256(b"test4").hexdigest()

    # First level
    level_1_1 = hashlib.sha256((h1 + h2).encode('utf-8')).hexdigest()
    level_1_2 = hashlib.sha256((h3 + h4).encode('utf-8')).hexdigest()

    # Second level
    expected = hashlib.sha256((level_1_1 + level_1_2).encode('utf-8')).hexdigest()

    assert create_merkle_root([h1, h2, h3, h4]) == "0x" + expected
