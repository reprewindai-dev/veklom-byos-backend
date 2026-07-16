import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from backend.services.uacp_v3_context import UacpV3Contextualizer

@pytest.mark.asyncio
async def test_contextualize_plan_http_fallback_to_mock():
    # Arrange
    with patch("backend.services.uacp_v3_context.settings") as mock_settings:
        mock_settings.UACPV3_MODE = "http"
        mock_settings.UACPV3_BASE_URL = "http://fake-uacp-url"
        mock_settings.UACPV3_TIMEOUT_MS = 1000
        mock_settings.UPSTREAM_GATEWAY_SECRET = "secret"

        contextualizer = UacpV3Contextualizer()

        intent = {"action": "test"}
        v2_plan = {"steps": ["step1"]}
        expected_mock_result = {"status": "mocked_context"}

        # Patch the internal methods
        with patch.object(contextualizer, '_contextualize_http', new_callable=AsyncMock) as mock_http, \
             patch.object(contextualizer, '_contextualize_mock', new_callable=AsyncMock) as mock_fallback:

            # Make the HTTP method raise an exception to trigger the fallback
            mock_http.side_effect = Exception("Simulated HTTP failure")
            mock_fallback.return_value = expected_mock_result

            # Act
            result = await contextualizer.contextualize_plan(intent, v2_plan)

            # Assert
            mock_http.assert_called_once_with(intent, v2_plan)
            mock_fallback.assert_called_once_with(intent, v2_plan)
            assert result == expected_mock_result
