from backend.apps.api.routers.vnp_beacon import compute_composite_score

def test_compute_composite_score():
    weights = {"p99_latency": 0.40, "uptime": 0.60}
    
    # Excellent API (20ms latency, 100% uptime)
    # Latency score: 100 - (20/10) = 98
    # 98 * 0.40 = 39.2
    # Uptime score: 100 * 0.60 = 60.0
    # Total = 99.2
    score1 = compute_composite_score(20, 100.0, weights)
    assert score1 == 99.2

    # Poor API (800ms latency, 95% uptime)
    # Latency score: 100 - (800/10) = 20
    # 20 * 0.40 = 8.0
    # Uptime score: 95 * 0.60 = 57.0
    # Total = 65.0
    score2 = compute_composite_score(800, 95.0, weights)
    assert score2 == 65.0

    assert score1 > score2
