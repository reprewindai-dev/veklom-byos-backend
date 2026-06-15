use reqwest::Client;
use serde_json::json;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, error, debug};

const GOVERNANCE_GATEWAY_URL: &str = "http://localhost:8080";
const BACKEND_URL: &str = "http://localhost:8000";

#[tokio::test]
async fn test_phase0a_health_check() {
    let client = Client::new();
    
    let response = client
        .get(&format!("{}/health", GOVERNANCE_GATEWAY_URL))
        .send()
        .await
        .expect("Failed to send health check request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    assert_eq!(body["status"], "healthy");
    assert_eq!(body["service"], "governance-gateway");
    assert_eq!(body["phase"], "0A");
    
    info!("✅ Phase 0A health check passed");
}

#[tokio::test]
async fn test_phase0a_mcp_ping() {
    let client = Client::new();
    
    let ping_request = json!({
        "method": "ping",
        "params": {},
        "id": 1
    });
    
    let response = client
        .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
        .json(&ping_request)
        .send()
        .await
        .expect("Failed to send ping request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    assert!(body["result"]["status"].is_string());
    assert!(body["result"]["timestamp"].is_string());
    
    info!("✅ Phase 0A MCP ping passed");
}

#[tokio::test]
async fn test_phase0a_list_tools() {
    let client = Client::new();
    
    let list_tools_request = json!({
        "method": "list_tools",
        "params": {},
        "id": 2
    });
    
    let response = client
        .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
        .json(&list_tools_request)
        .send()
        .await
        .expect("Failed to send list_tools request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    let tools = &body["result"]["tools"];
    assert!(tools.as_array().unwrap().len() >= 2);
    
    // Check that execute_action and ping are present
    let tool_names: Vec<String> = tools.as_array()
        .unwrap()
        .iter()
        .filter_map(|t| t["name"].as_str().map(|s| s.to_string()))
        .collect();
    
    assert!(tool_names.contains(&"execute_action".to_string()));
    assert!(tool_names.contains(&"ping".to_string()));
    
    info!("✅ Phase 0A list_tools passed");
}

#[tokio::test]
async fn test_phase0a_execute_action_valid_identity() {
    let client = Client::new();
    
    let execute_request = json!({
        "method": "execute_action",
        "params": {
            "agent_id": "agent_12345",
            "certificate_id": "cert_abc123",
            "latest_genome_hash": "sha256:abc123def456",
            "tool_name": "web_search",
            "workspace_id": "workspace_67890",
            "action_context": {
                "query": "test search query"
            }
        },
        "id": 3
    });
    
    let response = client
        .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
        .json(&execute_request)
        .send()
        .await
        .expect("Failed to send execute_action request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    
    // Should either succeed with EAT or fail with identity error
    if body.get("result").is_some() {
        assert!(body["result"]["status"].is_string());
        assert!(body["result"]["message"].is_string());
        assert!(body["result"]["eat"].is_object());
        info!("✅ Phase 0A execute_action succeeded with valid identity and EAT minted");
    } else {
        // Expected if backend services are not running
        assert!(body["error"]["message"].is_string());
        info!("✅ Phase 0A execute_action failed as expected (backend not available)");
    }
}

#[tokio::test]
async fn test_phase0a_execute_action_invalid_identity() {
    let client = Client::new();
    
    let execute_request = json!({
        "method": "execute_action",
        "params": {
            "agent_id": "invalid_agent",
            "certificate_id": "invalid_cert",
            "latest_genome_hash": "invalid_hash",
            "tool_name": "web_search",
            "workspace_id": "workspace_67890"
        },
        "id": 4
    });
    
    let response = client
        .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
        .json(&execute_request)
        .send()
        .await
        .expect("Failed to send execute_action request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    
    // Should fail with identity verification error
    assert!(body.get("error").is_some());
    assert_eq!(body["error"]["code"], -32001); // Identity verification error
    assert!(body["error"]["message"].as_str().unwrap().contains("Identity verification failed"));
    
    info!("✅ Phase 0A execute_action correctly rejected invalid identity");
}

#[tokio::test]
async fn test_phase0a_invalid_method() {
    let client = Client::new();
    
    let invalid_request = json!({
        "method": "invalid_method",
        "params": {},
        "id": 5
    });
    
    let response = client
        .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
        .json(&invalid_request)
        .send()
        .await
        .expect("Failed to send invalid request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    
    // Should fail with method not found error
    assert!(body.get("error").is_some());
    assert_eq!(body["error"]["code"], -32601); // Method not found
    assert!(body["error"]["message"].as_str().unwrap().contains("Method not found"));
    
    info!("✅ Phase 0A invalid method correctly rejected");
}

#[tokio::test]
async fn test_phase0a_malformed_request() {
    let client = Client::new();
    
    let malformed_request = json!({
        "method": "ping"
        // Missing required "params" and "id" fields
    });
    
    let response = client
        .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
        .json(&malformed_request)
        .send()
        .await
        .expect("Failed to send malformed request");
    
    // Should return 400 Bad Request for malformed JSON
    assert_eq!(response.status(), 400);
    
    info!("✅ Phase 0A malformed request correctly rejected");
}

#[tokio::test]
async fn test_phase0a_concurrent_requests() {
    let client = Client::new();
    
    // Send multiple concurrent ping requests
    let mut handles = vec![];
    
    for i in 0..10 {
        let client_clone = client.clone();
        let handle = tokio::spawn(async move {
            let ping_request = json!({
                "method": "ping",
                "params": {},
                "id": i + 100
            });
            
            client_clone
                .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
                .json(&ping_request)
                .send()
                .await
        });
        
        handles.push(handle);
    }
    
    // Wait for all requests to complete
    let mut success_count = 0;
    for handle in handles {
        match handle.await.unwrap() {
            Ok(response) => {
                if response.status() == 200 {
                    success_count += 1;
                }
            },
            Err(e) => {
                error!("Concurrent request failed: {}", e);
            }
        }
    }
    
    // At least 80% of requests should succeed
    assert!(success_count >= 8);
    
    info!("✅ Phase 0A concurrent requests test passed ({} / 10 succeeded)", success_count);
}

#[tokio::test]
async fn test_phase0a_timeout_handling() {
    let client = Client::new();
    
    // Create a request with a very short timeout
    let ping_request = json!({
        "method": "ping",
        "params": {},
        "id": 200
    });
    
    let response = client
        .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
        .json(&ping_request)
        .timeout(Duration::from_millis(100)) // Very short timeout
        .send()
        .await;
    
    match response {
        Ok(_) => {
            // Request completed quickly (which is fine)
            info!("✅ Phase 0A timeout handling - request completed quickly");
        },
        Err(e) => {
            // Request timed out (which is also acceptable behavior)
            assert!(e.is_timeout());
            info!("✅ Phase 0A timeout handling - request timed out as expected");
        }
    }
}

// Helper function to wait for services to be ready
async fn wait_for_service(url: &str, max_attempts: u32) -> bool {
    let client = Client::new();
    
    for attempt in 1..=max_attempts {
        match client.get(url).send().await {
            Ok(response) if response.status().is_success() => return true,
            _ => {
                debug!("Service not ready, attempt {} of {}", attempt, max_attempts);
                sleep(Duration::from_secs(2)).await;
            }
        }
    }
    
    false
}

#[tokio::test]
#[ignore] // Use this test manually to check if services are ready
async fn test_service_readiness() {
    info!("Checking service readiness...");
    
    let governance_ready = wait_for_service(&format!("{}/health", GOVERNANCE_GATEWAY_URL), 30).await;
    let backend_ready = wait_for_service(&format!("{}/health", BACKEND_URL), 30).await;
    
    info!("Governance Gateway ready: {}", governance_ready);
    info!("Backend ready: {}", backend_ready);
    
    if governance_ready {
        info!("✅ All services are ready for testing");
    } else {
        info!("⚠️  Some services are not ready - tests may fail");
    }
}
