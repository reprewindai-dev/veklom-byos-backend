import pytest
from backend.services.forecast import _ewma

def test_ewma_empty():
    """Test EWMA boundary condition with empty list."""
    assert _ewma([]) == 0.0

def test_ewma_single():
    """Test EWMA with a single element."""
    assert _ewma([5.0]) == 5.0

def test_ewma_multiple():
    """Test EWMA with multiple elements."""
    # level = 10.0
    # next: 0.3 * 20.0 + 0.7 * 10.0 = 6.0 + 7.0 = 13.0
    # next: 0.3 * 30.0 + 0.7 * 13.0 = 9.0 + 9.1 = 18.1
    assert abs(_ewma([10.0, 20.0, 30.0], alpha=0.3) - 18.1) < 1e-6

def test_ewma_zero_alpha():
    """Test EWMA with alpha=0 (ignores new values, keeps initial level)."""
    assert _ewma([10.0, 20.0, 30.0], alpha=0.0) == 10.0

def test_ewma_one_alpha():
    """Test EWMA with alpha=1 (only keeps newest value)."""
    assert _ewma([10.0, 20.0, 30.0], alpha=1.0) == 30.0
