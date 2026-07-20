import pytest
from backend.services.intelligence_layer import RiskScoringService

@pytest.fixture
def service():
    return RiskScoringService()

def test_calculate_risk_score_green(service):
    # Score = 100 * 0.5 + 0 * 10 = 50 -> Green (<=50)
    factors = {"anomaly_score": 100, "behavioral_deviation": 0}
    result = service.calculate_risk_score("test-agent", factors)

    assert result["overall_risk_score"] == 50
    assert result["threat_level"] == "green"

def test_calculate_risk_score_yellow(service):
    # Score = 50 * 0.5 + 5 * 10 = 25 + 50 = 75 -> Yellow (50 < score <= 75)
    factors = {"anomaly_score": 50, "behavioral_deviation": 5}
    result = service.calculate_risk_score("test-agent", factors)

    assert result["overall_risk_score"] == 75
    assert result["threat_level"] == "yellow"

def test_calculate_risk_score_red(service):
    # Score = 60 * 0.5 + 5 * 10 = 30 + 50 = 80 -> Red (>75)
    factors = {"anomaly_score": 60, "behavioral_deviation": 5}
    result = service.calculate_risk_score("test-agent", factors)

    assert result["overall_risk_score"] == 80
    assert result["threat_level"] == "red"

def test_calculate_risk_score_capped_at_100(service):
    # Score = 200 * 0.5 + 10 * 10 = 100 + 100 = 200 -> Capped at 100, Red
    factors = {"anomaly_score": 200, "behavioral_deviation": 10}
    result = service.calculate_risk_score("test-agent", factors)

    assert result["overall_risk_score"] == 100
    assert result["threat_level"] == "red"

def test_calculate_risk_score_missing_factors(service):
    # Missing factors should default to 0. Score = 0 -> Green
    factors = {}
    result = service.calculate_risk_score("test-agent", factors)

    assert result["overall_risk_score"] == 0
    assert result["threat_level"] == "green"

def test_calculate_risk_score_partial_factors(service):
    # Only anomaly_score provided
    # Score = 40 * 0.5 + 0 * 10 = 20 -> Green
    factors = {"anomaly_score": 40}
    result = service.calculate_risk_score("test-agent", factors)

    assert result["overall_risk_score"] == 20
    assert result["threat_level"] == "green"

    # Only behavioral_deviation provided
    # Score = 0 * 0.5 + 6 * 10 = 60 -> Yellow
    factors = {"behavioral_deviation": 6}
    result = service.calculate_risk_score("test-agent", factors)

    assert result["overall_risk_score"] == 60
    assert result["threat_level"] == "yellow"
