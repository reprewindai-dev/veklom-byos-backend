from backend.core.ml.vnp_scoring import compute_vnp_score

def test_compute_composite_score():
    weights = {
        "latency": 0.40, 
        "availability": 0.60,
        "security": 0.0,
        "m2m": 0.0,
        "integrity": 0.0
    }
    
    # Excellent API (20ms latency, 100% uptime)
    score1 = compute_vnp_score(
        p50_latency_ms=20, 
        p99_latency_ms=20, 
        availability_percent=100.0, 
        weights=weights
    )
    assert score1 > 90.0

    # Poor API (800ms latency, 95% uptime)
    score2 = compute_vnp_score(
        p50_latency_ms=800, 
        p99_latency_ms=800, 
        availability_percent=95.0, 
        weights=weights
    )
    assert score2 < score1

