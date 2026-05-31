"""Locust validation tests for UACP service vs library latency comparison."""

import time
import random
from locust import HttpUser, task, between
from typing import Dict, Any

# Import library shim for comparison
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from backend.services.uacp.lib import get_uacp_library


class UACPServiceUser(HttpUser):
    """Load test for UACP HTTP service."""
    
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        """Initialize auth token."""
        # In production, this would fetch a real JWT
        self.auth_token = "Bearer test_token"
    
    @task(3)
    def decide_low_risk(self):
        """Test low-risk decision (should be APPROVED)."""
        payload = {
            "input": {
                "intent": "Generate a summary of the document",
                "v2_plan": {
                    "policy_checkable_frame": {
                        "risk_tier": "low",
                        "estimated_cost": 0.01,
                        "tools": ["summarize"],
                        "contains_pii": False,
                        "external_destinations": []
                    }
                },
                "v3_context": {
                    "clearance_level": "standard",
                    "budget_remaining": 1000.0,
                    "max_risk_tier": "high",
                    "tool_allowlist": ["summarize", "analyze", "generate"]
                }
            },
            "trace_id": f"trace_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            "workspace_id": "ws_test_123"
        }
        
        with self.client.post(
            "/api/v1/uacp/v1/decide",
            json=payload,
            headers={"Authorization": self.auth_token},
            catch_response=True,
            name="/api/v1/uacp/v1/decide (low risk)"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("decision", {}).get("decision") != "APPROVED":
                    response.failure(f"Unexpected decision: {data.get('decision')}")
            elif response.status_code == 401:
                response.failure("Auth failed (expected in test mode)")
    
    @task(2)
    def decide_high_risk(self):
        """Test high-risk decision (should be HELD)."""
        payload = {
            "input": {
                "intent": "Transfer sensitive data to external service",
                "v2_plan": {
                    "policy_checkable_frame": {
                        "risk_tier": "high",
                        "estimated_cost": 0.5,
                        "tools": ["transfer", "external_api"],
                        "contains_pii": True,
                        "external_destinations": ["external.com"]
                    }
                },
                "v3_context": {
                    "clearance_level": "standard",
                    "budget_remaining": 1000.0,
                    "max_risk_tier": "high",
                    "tool_allowlist": ["summarize", "analyze"]
                }
            },
            "trace_id": f"trace_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            "workspace_id": "ws_test_123"
        }
        
        self.client.post(
            "/api/v1/uacp/v1/decide",
            json=payload,
            headers={"Authorization": self.auth_token},
            name="/api/v1/uacp/v1/decide (high risk)"
        )
    
    @task(1)
    def decide_critical_risk(self):
        """Test critical-risk decision (should be DENIED)."""
        payload = {
            "input": {
                "intent": "Execute arbitrary code with system access",
                "v2_plan": {
                    "policy_checkable_frame": {
                        "risk_tier": "critical",
                        "estimated_cost": 10.0,
                        "tools": ["system_execute", "root_access"],
                        "contains_pii": True,
                        "external_destinations": ["malicious.com"],
                        "constitutional_violations": ["data_sovereignty", "privacy"]
                    }
                },
                "v3_context": {
                    "clearance_level": "standard",
                    "budget_remaining": 1000.0,
                    "max_risk_tier": "high",
                    "tool_allowlist": ["summarize"]
                }
            },
            "trace_id": f"trace_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            "workspace_id": "ws_test_123"
        }
        
        self.client.post(
            "/api/v1/uacp/v1/decide",
            json=payload,
            headers={"Authorization": self.auth_token},
            name="/api/v1/uacp/v1/decide (critical risk)"
        )


class UACPLibraryUser:
    """Load test for UACP library shim (in-process)."""
    
    def __init__(self):
        self.library = get_uacp_library()
        self.latencies = []
    
    @task(3)
    def decide_low_risk(self):
        """Test low-risk decision via library."""
        start = time.time()
        
        result = self.library.decide(
            intent={"text": "Generate a summary"},
            v2_plan={
                "policy_checkable_frame": {
                    "risk_tier": "low",
                    "estimated_cost": 0.01,
                    "tools": ["summarize"],
                    "contains_pii": False,
                    "external_destinations": []
                }
            },
            v3_context={
                "clearance_level": "standard",
                "budget_remaining": 1000.0,
                "max_risk_tier": "high",
                "tool_allowlist": ["summarize"]
            },
            workspace_id="ws_test_123",
            trace_id=f"trace_{int(time.time() * 1000)}"
        )
        
        latency_ms = (time.time() - start) * 1000
        self.latencies.append(latency_ms)
        
        if result.get("decision") != "APPROVED":
            raise Exception(f"Unexpected decision: {result.get('decision')}")
    
    @task(2)
    def decide_high_risk(self):
        """Test high-risk decision via library."""
        start = time.time()
        
        result = self.library.decide(
            intent={"text": "Transfer data"},
            v2_plan={
                "policy_checkable_frame": {
                    "risk_tier": "high",
                    "estimated_cost": 0.5,
                    "tools": ["transfer"],
                    "contains_pii": True,
                    "external_destinations": ["external.com"]
                }
            },
            v3_context={
                "clearance_level": "standard",
                "budget_remaining": 1000.0,
                "max_risk_tier": "high",
                "tool_allowlist": ["summarize"]
            },
            workspace_id="ws_test_123"
        )
        
        latency_ms = (time.time() - start) * 1000
        self.latencies.append(latency_ms)
    
    def get_stats(self):
        """Return latency statistics."""
        if not self.latencies:
            return {}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            "count": n,
            "p50": sorted_latencies[n // 2],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)],
            "avg": sum(self.latencies) / n
        }
