import pytest
from backend.services.intelligence_layer import CostAttributionService

class TestCostAttributionService:
    def setup_method(self):
        self.service = CostAttributionService()
        self.service.vnp_ledger = {
            "rich_agent": 100.0,
            "poor_agent": 5.0,
            "exact_agent": 10.0,
            "zero_agent": 0.0,
        }

    def test_can_afford_request_sufficient_balance(self):
        # 100.0 balance, 10.0 cost -> True
        assert self.service.can_afford_request("rich_agent", "some_capability", 10.0) is True

    def test_can_afford_request_exact_balance(self):
        # 10.0 balance, 10.0 cost -> True
        assert self.service.can_afford_request("exact_agent", "some_capability", 10.0) is True

    def test_can_afford_request_insufficient_balance(self):
        # 5.0 balance, 10.0 cost -> False
        assert self.service.can_afford_request("poor_agent", "some_capability", 10.0) is False

    def test_can_afford_request_unknown_agent_cost_zero(self):
        # 0.0 balance (default), 0.0 cost -> True
        assert self.service.can_afford_request("unknown_agent", "some_capability", 0.0) is True

    def test_can_afford_request_unknown_agent_cost_positive(self):
        # 0.0 balance (default), 5.0 cost -> False
        assert self.service.can_afford_request("unknown_agent", "some_capability", 5.0) is False

    def test_can_afford_request_zero_agent(self):
        # 0.0 balance, 0.0 cost -> True
        assert self.service.can_afford_request("zero_agent", "some_capability", 0.0) is True

        # 0.0 balance, 5.0 cost -> False
        assert self.service.can_afford_request("zero_agent", "some_capability", 5.0) is False
