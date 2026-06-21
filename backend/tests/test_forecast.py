import pytest
from backend.services.forecast import (
    _ewma,
    _linear_slope,
    _stddev,
    _confidence,
    project_total,
    _fit,
    MIN_SAMPLES,
    MIN_DAYS_FOR_TREND,
    EWMA_ALPHA,
)

def test_ewma_empty():
    assert _ewma([]) == 0.0

def test_ewma_single():
    assert _ewma([5.0]) == 5.0

def test_ewma_multiple():
    # alpha = 0.3
    # v[0] = 10.0 -> level = 10.0
    # v[1] = 20.0 -> level = 0.3 * 20.0 + 0.7 * 10.0 = 6.0 + 7.0 = 13.0
    # v[2] = 30.0 -> level = 0.3 * 30.0 + 0.7 * 13.0 = 9.0 + 9.1 = 18.1
    assert abs(_ewma([10.0, 20.0, 30.0], alpha=0.3) - 18.1) < 1e-6

def test_linear_slope_insufficient_days():
    # Should return (0.0, last_value) or (0.0, 0.0) if empty
    assert _linear_slope([]) == (0.0, 0.0)
    assert _linear_slope([10.0]) == (0.0, 10.0)
    assert _linear_slope([10.0, 20.0]) == (0.0, 20.0)

def test_linear_slope_flat():
    slope, intercept = _linear_slope([10.0, 10.0, 10.0, 10.0])
    assert abs(slope) < 1e-6
    assert abs(intercept - 10.0) < 1e-6

def test_linear_slope_positive():
    # xs: 0, 1, 2, 3
    # ys: 10, 20, 30, 40
    # Slope should be 10, intercept 10
    slope, intercept = _linear_slope([10.0, 20.0, 30.0, 40.0])
    assert abs(slope - 10.0) < 1e-6
    assert abs(intercept - 10.0) < 1e-6

def test_stddev_insufficient_samples():
    assert _stddev([]) == 0.0
    assert _stddev([10.0]) == 0.0

def test_stddev_calculation():
    # Values: 2, 4, 4, 4, 5, 5, 7, 9 -> mean is 5
    # Variances: 9, 1, 1, 1, 0, 0, 4, 16 -> sum = 32
    # pop var = 32 / 8 = 4 -> stddev = 2
    assert abs(_stddev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]) - 2.0) < 1e-6

def test_confidence_insufficient_samples():
    assert _confidence(MIN_SAMPLES - 1, [10.0] * (MIN_SAMPLES - 1)) == 0.0

def test_confidence_calculation():
    # With min samples, stable: CV=0, stability=1, volume=MIN_SAMPLES/200
    daily = [10.0] * 10 # 10 samples
    conf = _confidence(10, daily)
    # volume = 10 / 200 = 0.05
    # stability = 1.0 (mean > 0, stddev = 0)
    # confidence = 0.4 * 0.05 + 0.55 * 1.0 = 0.02 + 0.55 = 0.57
    assert abs(conf - 0.57) < 1e-6

def test_confidence_high_volume():
    # High volume, maxes at 200 samples
    daily = [10.0] * 250
    conf = _confidence(250, daily)
    # volume = 200/200 = 1.0 (capped)
    # stability = 1.0
    # confidence = 0.4 * 1.0 + 0.55 * 1.0 = 0.95
    assert abs(conf - 0.95) < 1e-6

def test_project_total_insufficient_data():
    assert project_total({"method": "insufficient_data"}, 10) == 0.0
    assert project_total({}, 10) == 0.0

def test_project_total():
    # level = 10.0, slope = 2.0
    # day 1: 10 + 2 = 12
    # day 2: 10 + 4 = 14
    # day 3: 10 + 6 = 16
    # Total = 12 + 14 + 16 = 42
    params = {"method": "ewma_linear", "ewma": 10.0, "slope": 2.0}
    assert project_total(params, 3) == 42.0

def test_project_total_negative_slope():
    # level = 10.0, slope = -5.0
    # day 1: 10 - 5 = 5
    # day 2: 10 - 10 = 0
    # day 3: 10 - 15 = -5 (capped at 0)
    # Total = 5 + 0 + 0 = 5.0
    params = {"method": "ewma_linear", "ewma": 10.0, "slope": -5.0}
    assert project_total(params, 3) == 5.0

def test_fit_insufficient_samples():
    daily = [10.0] * (MIN_SAMPLES - 1)
    result = _fit(daily, MIN_SAMPLES - 1)
    assert result["method"] == "insufficient_data"
    assert result["daily_avg"] == 10.0
    assert result["ewma"] == 0.0

def test_fit_success():
    daily = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0] # 10 samples
    result = _fit(daily, 10)
    assert result["method"] == "ewma_linear"
    assert result["daily_avg"] == 55.0
    assert result["slope"] == 10.0
    assert result["intercept"] == 10.0
    # ewma calculation:
    # level = 10
    # v=20: 0.3*20 + 0.7*10 = 13
    # v=30: 0.3*30 + 0.7*13 = 18.1
    # ... ewma will be around 74.something
    assert result["ewma"] > 0.0
    assert result["sample_count"] == 10
