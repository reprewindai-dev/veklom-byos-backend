import pytest
from backend.services.smart_router import _model_fit, ModelCandidate

@pytest.fixture
def candidate():
    return ModelCandidate(
        node_id="test-node",
        provider="test-provider",
        model="test-model",
        cost_per_1k=0.01,
        quality_prior=0.85,
        latency_ms_prior=500,
        security_level=2,
        max_context=8000,
        max_complexity=7
    )

def test_model_fit_quality_criteria(candidate):
    """Test criteria that directly return quality_prior."""
    for criterion in ("accuracy", "risk", "creativity"):
        assert _model_fit(candidate, criterion, max_cost=0.05, max_latency=1000) == 0.85

def test_model_fit_reasoning(candidate):
    """Test reasoning criterion which scales max_complexity."""
    # max_complexity is 7, so 7 / 10.0 = 0.7
    assert _model_fit(candidate, "reasoning", max_cost=0.05, max_latency=1000) == 0.7

def test_model_fit_cost_standardization_normal(candidate):
    """Test cost and standardization criteria with max_cost > 0."""
    # eff_cost = 0.01, max_cost = 0.05
    # 1.0 - (0.01 / 0.05) = 1.0 - 0.2 = 0.8
    for criterion in ("cost", "standardization"):
        assert _model_fit(candidate, criterion, max_cost=0.05, max_latency=1000) == 0.8

def test_model_fit_cost_standardization_zero_max_cost(candidate):
    """Test cost and standardization criteria with max_cost == 0 (edge case)."""
    for criterion in ("cost", "standardization"):
        assert _model_fit(candidate, criterion, max_cost=0.0, max_latency=1000) == 1.0

def test_model_fit_time_normal(candidate):
    """Test time criterion with max_latency > 0."""
    # eff_latency = 500, max_latency = 1000
    # 1.0 - (500 / 1000) = 1.0 - 0.5 = 0.5
    assert _model_fit(candidate, "time", max_cost=0.05, max_latency=1000) == 0.5

def test_model_fit_time_zero_max_latency(candidate):
    """Test time criterion with max_latency == 0 (edge case)."""
    assert _model_fit(candidate, "time", max_cost=0.05, max_latency=0) == 1.0

def test_model_fit_unknown_criterion(candidate):
    """Test an unknown criterion which should return 0.0."""
    assert _model_fit(candidate, "unknown_criterion", max_cost=0.05, max_latency=1000) == 0.0
