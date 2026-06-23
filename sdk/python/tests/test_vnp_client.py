import pytest
from unittest.mock import patch, MagicMock

from veklom.client import VeklomClient
from veklom.vnp_client import VNPRouter

class TestVNPClient:
    def setup_method(self):
        self.sdk = VeklomClient(api_key="test-key", base_url="http://test.local")
        self.vnp = VNPRouter(
            sdk_client=self.sdk,
            project_id="test-proj",
            customer_id="test-cust",
            policy_id="test-policy"
        )
        
    @patch("httpx.Client.post")
    def test_dispatch_success(self, mock_post):
        # Mock VNP Beacon response
        self.sdk._get = MagicMock(return_value={
            "candidates": [
                {
                    "api_id": "test-api",
                    "provider_id": "provider-1",
                    "endpoint_url": "https://api.provider1.com/v1"
                }
            ],
            "route_snapshot_id": "snap-123",
            "ttl_seconds": 60
        })
        
        # Mock Usage Ingestion to do nothing
        self.sdk._post = MagicMock()
        
        # Mock httpx Provider response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "usage": {"total_tokens": 42}}
        mock_post.return_value = mock_resp
        
        res = self.vnp.dispatch("test-api", {"prompt": "hello"})
        
        assert res == {"success": True, "usage": {"total_tokens": 42}}
        
        # Verify SDK fetched routes
        self.sdk._get.assert_called_once()
        
        # Verify Provider was called
        mock_post.assert_called_once_with("https://api.provider1.com/v1", json={"prompt": "hello"})
        
        # Verify Usage was emitted
        self.sdk._post.assert_called_once()
        usage_call_args = self.sdk._post.call_args[0][1]
        assert usage_call_args["events"][0]["usage"]["billable_units"] == 42
        assert usage_call_args["events"][0]["usage"]["success"] is True

    @patch("httpx.Client.post")
    def test_dispatch_failover(self, mock_post):
        # Provide two routes. First fails, second succeeds.
        self.sdk._get = MagicMock(return_value={
            "candidates": [
                {
                    "api_id": "test-api",
                    "provider_id": "provider-1",
                    "endpoint_url": "https://bad.com"
                },
                {
                    "api_id": "test-api",
                    "provider_id": "provider-2",
                    "endpoint_url": "https://good.com"
                }
            ],
            "route_snapshot_id": "snap-123",
            "ttl_seconds": 60
        })
        
        self.sdk._post = MagicMock()
        
        def mock_provider_call(url, **kwargs):
            mock_resp = MagicMock()
            if "bad.com" in url:
                mock_resp.status_code = 500
                mock_resp.json.return_value = {"error": "fail"}
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"success": True, "usage": {"total_tokens": 10}}
            return mock_resp
            
        mock_post.side_effect = mock_provider_call
        
        res = self.vnp.dispatch("test-api", {"prompt": "hello"})
        
        assert res == {"success": True, "usage": {"total_tokens": 10}}
        
        # Ensure httpx was called twice (initial + 1 failover)
        assert mock_post.call_count == 2
        
        # Usage emission should be called twice (one for failure, one for success)
        assert self.sdk._post.call_count == 2
        
        fail_usage = self.sdk._post.call_args_list[0][0][1]["events"][0]
        assert fail_usage["usage"]["success"] is False
        assert fail_usage["usage"]["failover_count"] == 0
        assert fail_usage["request"]["provider_id"] == "provider-1"
        
        success_usage = self.sdk._post.call_args_list[1][0][1]["events"][0]
        assert success_usage["usage"]["success"] is True
        assert success_usage["usage"]["failover_count"] == 1
        assert success_usage["request"]["provider_id"] == "provider-2"
