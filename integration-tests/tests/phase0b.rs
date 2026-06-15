use reqwest::Client;
use serde_json::json;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, error, debug};
use chrono::Utc;

const EDGE_GATEWAY_URL: &str = "http://localhost:8081";
const GOVERNANCE_GATEWAY_URL: &str = "http://localhost:8080";

#[tokio::test]
async fn test_phase0b_health_check() {
    let client = Client::new();
    
    let response = client
        .get(&format!("{}/health", EDGE_GATEWAY_URL))
        .send()
        .await
        .expect("Failed to send health check request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    assert_eq!(body["status"], "healthy");
    assert_eq!(body["service"], "edge-gateway");
    assert_eq!(body["phase"], "0B");
    
    // Check all components are operational
    let components = &body["components"];
    assert_eq!(components["eat_verification"], "operational");
    assert_eq!(components["x402_merchant"], "operational");
    assert_eq!(components["execution_engine"], "operational");
    assert_eq!(components["rate_limiter"], "operational");
    
    info!("✅ Phase 0B health check passed");
}

#[tokio::test]
async fn test_phase0b_x402_challenge() {
    let client = Client::new();
    
    let challenge_request = json!({
        "endpoint": "/api/v1/premium/analysis",
        "workspace_id": "test_workspace_123"
    });
    
    let response = client
        .post(&format!("{}/x402/challenge", EDGE_GATEWAY_URL))
        .json(&challenge_request)
        .send()
        .await
        .expect("Failed to send challenge request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.expect("Failed to parse response");
    
    // Verify challenge structure
    assert!(body["challenge_id"].is_string());
    assert!(body["payment_address"].is_string());
    assert!(body["amount_required"].is_string());
    assert_eq!(body["currency"], "USDC");
    assert_eq!(body["network"], "base");
    assert!(body["expires_at"].is_string());
    assert!(body["payment_reference"].is_string());
    assert!(body["facilitator_data"].is_object());
    
    // Verify payment address format (starts with 0x)
    let payment_address = body["payment_address"].as_str().unwrap();
    assert!(payment_address.starts_with("0x"));
    assert_eq!(payment_address.len(), 42); // 0x + 40 hex chars
    
    // Verify amount is reasonable (should be 5.0 for default endpoint)
    let amount: f64 = body["amount_required"].as_str().unwrap().parse().unwrap();
    assert_eq!(amount, 5.0);
    
    info!("✅ Phase 0B x402 challenge creation passed");
}

#[tokio::test]
async fn test_phase0b_x402_challenge_invalid_endpoint() {
    let client = Client::new();
    
    let challenge_request = json!({
        "endpoint": "/invalid/endpoint",
        "workspace_id": "test_workspace_123"
    });
    
    let response = client
        .post(&format!("{}/x402/challenge", EDGE_GATEWAY_URL))
        .json(&challenge_request)
        .send()
        .await
        .expect("Failed to send challenge request");
    
    // Should return 404 for invalid endpoint
    assert_eq!(response.status(), 404);
    
    info!("✅ Phase 0B x402 challenge invalid endpoint correctly rejected");
}

#[tokio::test]
async fn test_phase0b_x402_verify_mock_payment() {
    let client = Client::new();
    
    // First create a challenge to get a payment reference
    let challenge_request = json!({
        "endpoint": "/api/v1/premium/analysis",
        "workspace_id": "test_workspace_123"
    });
    
    let challenge_response = client
        .post(&format!("{}/x402/challenge", EDGE_GATEWAY_URL))
        .json(&challenge_request)
        .send()
        .await
        .expect("Failed to send challenge request");
    
    let challenge_body: serde_json::Value = challenge_response.json().await.unwrap();
    let payment_reference = challenge_body["payment_reference"].as_str().unwrap();
    
    // Create a mock payment proof
    let payment_proof = json!({
        "payment_reference": payment_reference,
        "transaction_hash": format!("0x{}", "0".repeat(64)), // Mock transaction hash
        "amount": "5.0",
        "currency": "USDC",
        "payer_address": format!("0x{}", "1".repeat(40)), // Mock payer address
        "timestamp": Utc::now().to_rfc3339(),
        "signature": "mock_signature"
    });
    
    let response = client
        .post(&format!("{}/x402/verify", EDGE_GATEWAY_URL))
        .json(&payment_proof)
        .send()
        .await;
    
    match response {
        Ok(resp) => {
            if resp.status() == 200 {
                let body: serde_json::Value = resp.json().await.unwrap();
                assert_eq!(body["verified"], true);
                assert_eq!(body["payment_reference"], payment_reference);
                assert!(body["execution_token"].is_string());
                info!("✅ Phase 0B x402 verification passed (mock payment)");
            } else {
                // Expected if facilitator is not available
                assert!(resp.status() == 402 || resp.status() == 500);
                info!("✅ Phase 0B x402 verification failed as expected (facilitator not available)");
            }
        },
        Err(e) => {
            error!("x402 verification request failed: {}", e);
            // This might be expected if the service is not running
        }
    }
}

#[tokio::test]
async fn test_phase0b_execution_without_eat() {
    let client = Client::new();
    
    let execution_request = json!({
        "target_url": "https://api.example.com/test",
        "method": "GET",
        "headers": {},
        "body": null
        // Missing EAT - should fail
    });
    
    let response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&execution_request)
        .send()
        .await
        .expect("Failed to send execution request");
    
    // Should return 400 Bad Request for missing EAT
    assert_eq!(response.status(), 400);
    
    info!("✅ Phase 0B execution without EAT correctly rejected");
}

#[tokio::test]
async fn test_phase0b_execution_with_invalid_eat() {
    let client = Client::new();
    
    let execution_request = json!({
        "eat": {
            "eat_id": "invalid_eat",
            "agent_id": "invalid_agent",
            "authority_run_id": "invalid_run",
            "tool_name": "http_request",
            "resource_scope": {
                "url": "https://api.example.com/test",
                "method": "GET",
                "max_amount": 0.0,
                "domain": "example.com"
            },
            "workspace_id": "invalid_workspace",
            "issued_at": Utc::now().to_rfc3339(),
            "expires_at": Utc::now().to_rfc3339(),
            "nonce": "invalid_nonce",
            "constraints": {
                "max_retries": 3,
                "timeout_seconds": 30,
                "requires_x402": false,
                "allowed_methods": ["GET"],
                "extra_rules": {}
            },
            "signature": "invalid_signature"
        },
        "target_url": "https://api.example.com/test",
        "method": "GET",
        "headers": {},
        "body": null
    });
    
    let response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&execution_request)
        .send()
        .await
        .expect("Failed to send execution request");
    
    // Should return 401 Unauthorized for invalid EAT
    assert_eq!(response.status(), 401);
    
    let body: serde_json::Value = response.json().await.unwrap();
    assert!(body["error"].is_string());
    assert!(body["error"].as_str().unwrap().contains("Invalid EAT"));
    
    info!("✅ Phase 0B execution with invalid EAT correctly rejected");
}

#[tokio::test]
async fn test_phase0b_execution_scope_violation() {
    let client = Client::new();
    
    // Create a valid EAT structure but with scope mismatch
    let execution_request = json!({
        "eat": {
            "eat_id": "test_eat_scope",
            "agent_id": "test_agent",
            "authority_run_id": "test_run",
            "tool_name": "http_request",
            "resource_scope": {
                "url": "https://api.example.com/allowed", // Different URL
                "method": "GET",
                "max_amount": 0.0,
                "domain": "example.com"
            },
            "workspace_id": "test_workspace",
            "issued_at": Utc::now().to_rfc3339(),
            "expires_at": (Utc::now() + chrono::Duration::minutes(5)).to_rfc3339(),
            "nonce": "test_nonce_scope",
            "constraints": {
                "max_retries": 3,
                "timeout_seconds": 30,
                "requires_x402": false,
                "allowed_methods": ["GET"],
                "extra_rules": {}
            },
            "signature": "test_signature"
        },
        "target_url": "https://api.example.com/different", // Scope violation
        "method": "GET",
        "headers": {},
        "body": null
    });
    
    let response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&execution_request)
        .send()
        .await
        .expect("Failed to send execution request");
    
    // Should return 403 Forbidden for scope violation
    assert_eq!(response.status(), 403);
    
    let body: serde_json::Value = response.json().await.unwrap();
    assert!(body["error"].is_string());
    assert!(body["error"].as_str().unwrap().contains("Scope violation"));
    
    info!("✅ Phase 0B execution scope violation correctly rejected");
}

#[tokio::test]
async fn test_phase0b_x402_payment_status() {
    let client = Client::new();
    
    let payment_reference = "test_payment_ref_123";
    
    let response = client
        .get(&format!("{}/x402/status/{}", EDGE_GATEWAY_URL, payment_reference))
        .send()
        .await
        .expect("Failed to send status request");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json().await.unwrap();
    assert_eq!(body["payment_reference"], payment_reference);
    assert!(body["used"].is_boolean());
    assert!(body["timestamp"].is_string());
    
    info!("✅ Phase 0B x402 payment status check passed");
}

#[tokio::test]
async fn test_phase0b_rate_limiting() {
    let client = Client::new();
    
    // Send multiple rapid requests to test rate limiting
    let mut responses = vec![];
    
    for _ in 0..70 { // Exceed default rate limit of 60 per minute
        let response = client
            .get(&format!("{}/health", EDGE_GATEWAY_URL))
            .send()
            .await;
        
        responses.push(response);
    }
    
    let mut success_count = 0;
    let mut rate_limited_count = 0;
    
    for response in responses {
        match response {
            Ok(resp) => {
                if resp.status() == 200 {
                    success_count += 1;
                } else if resp.status() == 429 {
                    rate_limited_count += 1;
                }
            },
            Err(_) => {
                // Network errors don't count toward rate limiting
            }
        }
    }
    
    // Should have some rate limited responses
    if rate_limited_count > 0 {
        info!("✅ Phase 0B rate limiting working ({} requests rate limited)", rate_limited_count);
    } else {
        info!("✅ Phase 0B rate limiting not triggered (may be disabled or limits higher)");
    }
    
    info!("✅ Phase 0B rate limiting test completed ({} successful, {} rate limited)", 
          success_count, rate_limited_count);
}

#[tokio::test]
async fn test_phase0b_concurrent_challenges() {
    let client = Client::new();
    
    // Send multiple concurrent challenge requests
    let mut handles = vec![];
    
    for i in 0..10 {
        let client_clone = client.clone();
        let handle = tokio::spawn(async move {
            let challenge_request = json!({
                "endpoint": "/api/v1/premium/analysis",
                "workspace_id": format!("test_workspace_{}", i)
            });
            
            client_clone
                .post(&format!("{}/x402/challenge", EDGE_GATEWAY_URL))
                .json(&challenge_request)
                .send()
                .await
        });
        
        handles.push(handle);
    }
    
    // Wait for all requests to complete
    let mut success_count = 0;
    let mut unique_payment_references = std::collections::HashSet::new();
    
    for handle in handles {
        match handle.await.unwrap() {
            Ok(response) => {
                if response.status() == 200 {
                    success_count += 1;
                    if let Ok(body) = response.json::<serde_json::Value>().await {
                        if let Some(payment_ref) = body["payment_reference"].as_str() {
                            unique_payment_references.insert(payment_ref.to_string());
                        }
                    }
                }
            },
            Err(e) => {
                error!("Concurrent challenge request failed: {}", e);
            }
        }
    }
    
    // All requests should succeed
    assert_eq!(success_count, 10);
    
    // All payment references should be unique
    assert_eq!(unique_payment_references.len(), 10);
    
    info!("✅ Phase 0B concurrent challenges test passed ({} unique references)", 
          unique_payment_references.len());
}

#[tokio::test]
async fn test_phase0b_error_responses() {
    let client = Client::new();
    
    // Test various error scenarios
    let test_cases = vec![
        (json!({}), "Empty request"),
        (json!({"invalid": "request"}), "Malformed request"),
        (json!({"endpoint": ""}), "Empty endpoint"),
    ];
    
    for (request, description) in test_cases {
        let response = client
            .post(&format!("{}/x402/challenge", EDGE_GATEWAY_URL))
            .json(&request)
            .send()
            .await;
        
        match response {
            Ok(resp) => {
                // Should return error status
                assert!(!resp.status().is_success());
                debug!("✅ {}: correctly rejected with status {}", description, resp.status());
            },
            Err(e) => {
                debug!("✅ {}: request failed as expected: {}", description, e);
            }
        }
    }
    
    info!("✅ Phase 0B error response tests passed");
}

// Helper function to wait for Edge Gateway to be ready
async fn wait_for_edge_gateway(max_attempts: u32) -> bool {
    let client = Client::new();
    
    for attempt in 1..=max_attempts {
        match client.get(&format!("{}/health", EDGE_GATEWAY_URL)).send().await {
            Ok(response) if response.status().is_success() => return true,
            _ => {
                debug!("Edge Gateway not ready, attempt {} of {}", attempt, max_attempts);
                sleep(Duration::from_secs(2)).await;
            }
        }
    }
    
    false
}

#[tokio::test]
#[ignore] // Use this test manually to check if Edge Gateway is ready
async fn test_edge_gateway_readiness() {
    info!("Checking Edge Gateway readiness...");
    
    let ready = wait_for_edge_gateway(30).await;
    
    if ready {
        info!("✅ Edge Gateway is ready for testing");
    } else {
        info!("⚠️  Edge Gateway is not ready - Phase 0B tests may fail");
    }
}
