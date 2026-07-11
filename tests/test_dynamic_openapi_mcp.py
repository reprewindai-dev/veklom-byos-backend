import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend.apps.api.main import app
from backend.core.config.settings import settings

# Mock OpenAPI specification schema
MOCK_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Air Intercept API", "version": "1.0.0"},
    "paths": {
        "/deploy": {
            "post": {
                "summary": "Deploy a new service instance",
                "operationId": "deploy_service",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "service_name": {"type": "string"},
                                    "region": {"type": "string"}
                                },
                                "required": ["service_name"]
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "Successful deployment"}}
            }
        }
    }
}

@pytest.mark.asyncio
async def test_openapi_compiler():
    from backend.core.ai.openapi_ingest import OpenAPICompiler
    
    # Test translate schema
    manifests = OpenAPICompiler.compile_manifest(MOCK_OPENAPI_SPEC, "air-intercept", "https://api.airintercept.com/openapi.json")
    assert len(manifests) == 1
    tool = manifests[0]
    assert tool["tool_name"] == "air-intercept__deploy_service"
    assert tool["method"] == "POST"
    assert tool["path_template"] == "/deploy"
    assert "service_name" in tool["input_schema"]["properties"]
    assert "required" in tool["input_schema"]
    assert "service_name" in tool["input_schema"]["required"]
    assert tool["server_id"] == "air-intercept"

@pytest.mark.asyncio
@patch("backend.core.ai.openapi_ingest.OpenAPICompiler.fetch_schema")
async def test_mcp_gateway_registration_and_invoke(mock_fetch_schema):
    mock_fetch_schema.return_value = MOCK_OPENAPI_SPEC
    
    client = TestClient(app)
    
    # 1. Register MCP server
    reg_payload = {
        "server_id": "air-intercept",
        "name": "Air Intercept SaaS",
        "openapi_url": "https://api.airintercept.com/openapi.json",
        "base_url": "https://api.airintercept.com/v1",
        "auth_headers": {"X-Air-Token": "secret_saas_token_abc"}
    }
    
    # Override authentication dependencies
    mock_user = AsyncMock()
    mock_user.id = "user_123"
    mock_user.workspace_id = "ws_test_mcp"
    
    from backend.core.security.auth import get_current_user, get_current_user_optional
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_optional] = lambda: mock_user
    
    headers = {"Authorization": "Bearer mock_token"}
    
    with patch("backend.core.security.middlewares.verify_token") as mock_verify:
        mock_verify.return_value = {"sub": "user_123"}
        
        try:
            response = client.post("/api/v1/mcp/servers", json=reg_payload, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "air-intercept" in data["message"]
    
            # 2. Get registered servers
            list_resp = client.get("/api/v1/mcp/servers", headers=headers)
            assert list_resp.status_code == 200
            servers = list_resp.json()
            
            assert len(servers) > 0
            assert any(s["server_id"] == "air-intercept" for s in servers)
    
            # 3. Verify tools are returned in /tools endpoint
            tools_resp = client.get("/api/v1/mcp/tools", headers=headers)
            assert tools_resp.status_code == 200
            tools = tools_resp.json()
            assert any(t["tool_name"] == "air-intercept__deploy_service" for t in tools)
    
            # 4. Test proxy routing execution (governed via :invoke endpoint)
            invoke_body = {
                "parameters": {
                    "service_name": "backend-core",
                    "region": "us-east"
                }
            }
        
            # Mock downstream HTTPX call and governance process_request
            with patch("httpx.AsyncClient.request") as mock_request, \
                 patch("backend.security.mcp_gateway.EnhancedMCPAPIRuntime.process_request") as mock_gov:
                
                mock_gov.return_value = {"status": "ALLOWED", "evidence_hash": "mock_merkle_evidence_0x"}
                
                mock_response = MagicMock()
                mock_response.status_code = 201
                mock_response.content = b'{"instance_id":"inst_999","status":"running"}'
                mock_response.headers = {"Content-Type": "application/json"}
                mock_request.return_value = mock_response
                
                # Exec invoke endpoint
                proxy_resp = client.post(
                    "/api/v1/mcp/tools/air-intercept__deploy_service:invoke",
                    json=invoke_body,
                    headers={"X-Veklom-Nonce": "nonce_999", "Authorization": "Bearer mock_token"}
                )
                
                assert proxy_resp.status_code == 201
                assert proxy_resp.json()["instance_id"] == "inst_999"
                assert proxy_resp.headers["X-VNP-Stake-Result"] == "verified"
                assert proxy_resp.headers["X-Veklom-Receipt-ID"] == "mock_merkle_evidence_0x"
                
                # Verify custom auth header was injected in the downstream call
                args, kwargs = mock_request.call_args
                assert kwargs["headers"]["X-Air-Token"] == "secret_saas_token_abc"
                
                # Verify body was sent as JSON correctly
                assert kwargs["json"]["service_name"] == "backend-core"
                
        finally:
            app.dependency_overrides.clear()
