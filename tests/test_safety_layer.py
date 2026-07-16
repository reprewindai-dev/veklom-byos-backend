import unittest
from backend.services.safety_layer import (
    BehavioralBaselineService,
    AnomalyDetectionService,
    RequestQuarantineService,
    ApprovalQuorumService
)
from backend.models.mcpapi_v2 import (
    BehavioralBaseline,
    CurrentMetric,
    AnomalyType,
    Severity,
    RecommendedAction
)

class TestSafetyLayer(unittest.TestCase):
    def setUp(self):
        self.baseline_service = BehavioralBaselineService()
        self.anomaly_service = AnomalyDetectionService(self.baseline_service)
        self.quarantine_service = RequestQuarantineService()
        self.quorum_service = ApprovalQuorumService()

    def test_behavioral_baseline_retrieval(self):
        baseline = self.baseline_service.get_baseline("agent_1")
        self.assertIsNone(baseline)

        # Add a baseline
        dummy_baseline = BehavioralBaseline(
            agent_id="agent_1",
            observation_window_days=7,
            avg_requests_per_hour=10.0,
            std_dev_requests_per_hour=2.0,
            avg_failure_rate=0.01,
            std_dev_failure_rate=0.005,
            typical_capabilities={"read": 100},
            typical_time_windows=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            typical_error_types={},
            confidence_score=80.0,
            last_updated="2023-01-01T00:00:00Z",
            is_locked=False
        )
        self.baseline_service.baselines["agent_1"] = dummy_baseline
        retrieved = self.baseline_service.get_baseline("agent_1")
        self.assertEqual(retrieved.agent_id, "agent_1")

    def test_detect_anomalies_no_baseline(self):
        metric = CurrentMetric(
            requests_per_hour=10.0,
            failure_rate=0.0,
            new_capabilities=[],
            time_of_day=10,
            requests_in_window=10
        )
        anomalies = self.anomaly_service.detect_anomalies("agent_1", metric)
        self.assertEqual(len(anomalies), 0)

    def test_detect_anomalies_low_confidence(self):
        dummy_baseline = BehavioralBaseline(
            agent_id="agent_1",
            observation_window_days=7,
            avg_requests_per_hour=10.0,
            std_dev_requests_per_hour=2.0,
            avg_failure_rate=0.01,
            std_dev_failure_rate=0.005,
            typical_capabilities={"read": 100},
            typical_time_windows=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            typical_error_types={},
            confidence_score=40.0,  # Below 50
            last_updated="2023-01-01T00:00:00Z",
            is_locked=False
        )
        self.baseline_service.baselines["agent_1"] = dummy_baseline
        metric = CurrentMetric(
            requests_per_hour=10.0,
            failure_rate=0.0,
            new_capabilities=[],
            time_of_day=10,
            requests_in_window=10
        )
        anomalies = self.anomaly_service.detect_anomalies("agent_1", metric)
        self.assertEqual(len(anomalies), 0)

    def test_detect_anomalies_request_spike(self):
        dummy_baseline = BehavioralBaseline(
            agent_id="agent_1",
            observation_window_days=7,
            avg_requests_per_hour=10.0,
            std_dev_requests_per_hour=2.0,
            avg_failure_rate=0.01,
            std_dev_failure_rate=0.005,
            typical_capabilities={"read": 100},
            typical_time_windows=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            typical_error_types={},
            confidence_score=80.0,
            last_updated="2023-01-01T00:00:00Z",
            is_locked=False
        )
        self.baseline_service.baselines["agent_1"] = dummy_baseline

        # Requests are 16.0, avg is 10.0, std_dev is 2.0. Deviation = 3.0
        # 3.0 > ANOMALY_THRESHOLD (2.0)
        metric = CurrentMetric(
            requests_per_hour=16.0,
            failure_rate=0.0,
            new_capabilities=[],
            time_of_day=10,
            requests_in_window=16
        )
        anomalies = self.anomaly_service.detect_anomalies("agent_1", metric)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0].anomaly_type, AnomalyType.REQUEST_SPIKE)
        self.assertEqual(anomalies[0].deviation_score, 3.0)

    def test_detect_anomalies_new_capability(self):
        dummy_baseline = BehavioralBaseline(
            agent_id="agent_1",
            observation_window_days=7,
            avg_requests_per_hour=10.0,
            std_dev_requests_per_hour=2.0,
            avg_failure_rate=0.01,
            std_dev_failure_rate=0.005,
            typical_capabilities={"read": 100},
            typical_time_windows=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            typical_error_types={},
            confidence_score=80.0,
            last_updated="2023-01-01T00:00:00Z",
            is_locked=False
        )
        self.baseline_service.baselines["agent_1"] = dummy_baseline

        metric = CurrentMetric(
            requests_per_hour=10.0,
            failure_rate=0.0,
            new_capabilities=["write", "delete"],
            time_of_day=10,
            requests_in_window=10
        )
        anomalies = self.anomaly_service.detect_anomalies("agent_1", metric)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0].anomaly_type, AnomalyType.NEW_CAPABILITY_ACCESS)
        self.assertEqual(anomalies[0].deviation_score, 2.0)

    def test_detect_anomalies_off_hours(self):
        dummy_baseline = BehavioralBaseline(
            agent_id="agent_1",
            observation_window_days=7,
            avg_requests_per_hour=10.0,
            std_dev_requests_per_hour=2.0,
            avg_failure_rate=0.01,
            std_dev_failure_rate=0.005,
            typical_capabilities={"read": 100},
            typical_time_windows=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            typical_error_types={},
            confidence_score=80.0,
            last_updated="2023-01-01T00:00:00Z",
            is_locked=False
        )
        self.baseline_service.baselines["agent_1"] = dummy_baseline

        metric = CurrentMetric(
            requests_per_hour=10.0,
            failure_rate=0.0,
            new_capabilities=[],
            time_of_day=3, # Outside typical
            requests_in_window=10
        )
        anomalies = self.anomaly_service.detect_anomalies("agent_1", metric)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0].anomaly_type, AnomalyType.OFF_HOURS_ACTIVITY)
        self.assertEqual(anomalies[0].deviation_score, 1.0)

    def test_request_quarantine_service(self):
        dummy_baseline = BehavioralBaseline(
            agent_id="agent_1",
            observation_window_days=7,
            avg_requests_per_hour=10.0,
            std_dev_requests_per_hour=2.0,
            avg_failure_rate=0.01,
            std_dev_failure_rate=0.005,
            typical_capabilities={"read": 100},
            typical_time_windows=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            typical_error_types={},
            confidence_score=80.0,
            last_updated="2023-01-01T00:00:00Z",
            is_locked=False
        )
        metric = CurrentMetric(
            requests_per_hour=16.0,
            failure_rate=0.0,
            new_capabilities=[],
            time_of_day=10,
            requests_in_window=16
        )
        self.baseline_service.baselines["agent_1"] = dummy_baseline
        anomalies = self.anomaly_service.detect_anomalies("agent_1", metric)

        qr = self.quarantine_service.quarantine({"req": "test"}, anomalies)
        self.assertIsNotNone(qr)
        self.assertEqual(qr.original_request, {"req": "test"})
        self.assertEqual(len(qr.anomalies_detected), 1)

        retrieved = self.quarantine_service.get_quarantined(qr.quarantine_id)
        self.assertEqual(retrieved.quarantine_id, qr.quarantine_id)

    def test_approval_quorum_service(self):
        quorum = self.quorum_service.create_quorum("quarantine_123", ["user_1", "user_2"])
        self.assertEqual(quorum.quarantine_id, "quarantine_123")
        self.assertEqual(quorum.required_approvers, ["user_1", "user_2"])
        self.assertEqual(quorum.required_count, 2)
