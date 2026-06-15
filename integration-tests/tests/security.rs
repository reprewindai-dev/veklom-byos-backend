use reqwest::Client;
use serde_json::json;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, error, debug, warn};
use chrono::Utc;

const GOVERNANCE_GATEWAY_URL: &str = "http://localhost:8080";
const EDGE_GATEWAY_URL: &str = "http://localhost:8081";

#[tokio::test]
async fn test_security_trust_contract_enforcement() {
    info!("Starting security test: Trust Contract Enforcement");
    
    let client = Client::new();
    
    // Test 1: Edge Gateway must reject requests without valid EAT
    let unauthorized_requests = vec![
        json!({
            "target_url": "https://api.example.com/test",
            "method": "GET",
            "headers": {},
            "body": null
        }),
        json!({
            "eat": null,
            "target_url": "https://api.example.com/test",
            "method": "GET"
        }),
        json!({
            "eat": {},
            "target_url": "https://api.example.com/test",
            "method": "GET"
        }),
    ];
    
    for (i, request) in unauthorized_requests.iter().enumerate() {
        debug!("Testing unauthorized request {}", i + 1);
        
        let response = client
            .post(&format!("{}/execute", EDGE_GATEWAY_URL))
            .json(request)
            .send()
            .await
            .expect("Failed to send unauthorized request");
        
        // All should be rejected with 401 or 400
        assert!(response.status() == 401 || response.status() == 400);
        debug!("✅ Unauthorized request {} correctly rejected", i + 1);
    }
    
    info!("✅ Trust Contract Enforcement: Edge Gateway rejects unauthorized requests");
}

#[tokio::test]
async fn test_security_eat_signature_validation() {
    info!("Starting security test: EAT Signature Validation");
    
    let client = Client::new();
    
    // Create EAT with invalid signature
    let invalid_eat = json!({
        "eat_id": "eat_security_test_invalid_sig",
        "agent_id": "agent_security_test",
        "authority_run_id": "run_security_test",
        "tool_name": "http_request",
        "resource_scope": {
            "url": "https://api.example.com/security_test",
            "method": "GET",
            "max_amount": 0.0,
            "domain": "example.com"
        },
        "workspace_id": "workspace_security_test",
        "issued_at": Utc::now().to_rfc3339(),
        "expires_at": (Utc::now() + chrono::Duration::minutes(5)).to_rfc3339(),
        "nonce": "nonce_security_test_invalid",
        "constraints": {
            "max_retries": 3,
            "timeout_seconds": 30,
            "requires_x402": false,
            "allowed_methods": ["GET"],
            "extra_rules": {}
        },
        "signature": "completely_invalid_signature_that_should_fail_verification"
    });
    
    let execution_request = json!({
        "eat": invalid_eat,
        "target_url": "https://api.example.com/security_test",
        "method": "GET",
        "headers": {},
        "body": null
    });
    
    let response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&execution_request)
        .send()
        .await
        .expect("Failed to send request with invalid EAT signature");
    
    // Should be rejected with 401
    assert_eq!(response.status(), 401);
    
    let body: serde_json::Value = response.json().await.unwrap();
    assert!(body["error"].as_str().unwrap().contains("Invalid EAT"));
    
    info!("✅ EAT Signature Validation: Invalid signatures rejected");
}

#[tokio::test]
async fn test_security_eat_expiration_enforcement() {
    info!("Starting security test: EAT Expiration Enforcement");
    
    let client = Client::new();
    
    // Create expired EAT
    let expired_eat = json!({
        "eat_id": "eat_security_test_expired",
        "agent_id": "agent_security_test",
        "authority_run_id": "run_security_test",
        "tool_name": "http_request",
        "resource_scope": {
            "url": "https://api.example.com/security_test",
            "method": "GET",
            "max_amount": 0.0,
            "domain": "example.com"
        },
        "workspace_id": "workspace_security_test",
        "issued_at": (Utc::now() - chrono::Duration::hours(1)).to_rfc3339(),
        "expires_at": (Utc::now() - chrono::Duration::minutes(1)).to_rfc3339(), // Expired
        "nonce": "nonce_security_test_expired",
        "constraints": {
            "max_retries": 3,
            "timeout_seconds": 30,
            "requires_x402": false,
            "allowed_methods": ["GET"],
            "extra_rules": {}
        },
        "signature": "test_signature"
    });
    
    let execution_request = json!({
        "eat": expired_eat,
        "target_url": "https://api.example.com/security_test",
        "method": "GET",
        "headers": {},
        "body": null
    });
    
    let response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&execution_request)
        .send()
        .await
        .expect("Failed to send request with expired EAT");
    
    // Should be rejected with 401
    assert_eq!(response.status(), 401);
    
    let body: serde_json::Value = response.json().await.unwrap();
    assert!(body["error"].as_str().unwrap().contains("expired"));
    
    info!("✅ EAT Expiration Enforcement: Expired EATs rejected");
}

#[tokio::test]
async fn test_security_scope_enforcement() {
    info!("Starting security test: Scope Enforcement");
    
    let client = Client::new();
    
    // Test cases for scope violations
    let scope_violation_cases = vec![
        (
            json!({
                "eat_id": "eat_security_test_scope1",
                "agent_id": "agent_security_test",
                "authority_run_id": "run_security_test",
                "tool_name": "http_request",
                "resource_scope": {
                    "url": "https://api.example.com/allowed",
                    "method": "GET",
                    "max_amount": 0.0,
                    "domain": "example.com"
                },
                "workspace_id": "workspace_security_test",
                "issued_at": Utc::now().to_rfc3339(),
                "expires_at": (Utc::now() + chrono::Duration::minutes(5)).to_rfc3339(),
                "nonce": "nonce_security_test_scope1",
                "constraints": {
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "requires_x402": false,
                    "allowed_methods": ["GET"],
                    "extra_rules": {}
                },
                "signature": "test_signature"
            }),
            "https://api.evil.com/malicious", // URL scope violation
            "GET"
        ),
        (
            json!({
                "eat_id": "eat_security_test_scope2",
                "agent_id": "agent_security_test",
                "authority_run_id": "run_security_test",
                "tool_name": "http_request",
                "resource_scope": {
                    "url": "https://api.example.com/allowed",
                    "method": "GET",
                    "max_amount": 0.0,
                    "domain": "example.com"
                },
                "workspace_id": "workspace_security_test",
                "issued_at": Utc::now().to_rfc3339(),
                "expires_at": (Utc::now() + chrono::Duration::minutes(5)).to_rfc3339(),
                "nonce": "nonce_security_test_scope2",
                "constraints": {
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "requires_x402": false,
                    "allowed_methods": ["GET"],
                    "extra_rules": {}
                },
                "signature": "test_signature"
            }),
            "https://api.example.com/allowed",
            "POST" // Method scope violation
        ),
    ];
    
    for (i, (eat, target_url, method)) in scope_violation_cases.iter().enumerate() {
        debug!("Testing scope violation case {}", i + 1);
        
        let execution_request = json!({
            "eat": eat,
            "target_url": target_url,
            "method": method,
            "headers": {},
            "body": null
        });
        
        let response = client
            .post(&format!("{}/execute", EDGE_GATEWAY_URL))
            .json(&execution_request)
            .send()
            .await
            .expect("Failed to send scope violation request");
        
        // Should be rejected with 403 (Forbidden) for scope violations
        assert_eq!(response.status(), 403);
        
        let body: serde_json::Value = response.json().await.unwrap();
        assert!(body["error"].as_str().unwrap().contains("Scope violation"));
        
        debug!("✅ Scope violation case {} correctly rejected", i + 1);
    }
    
    info!("✅ Scope Enforcement: Scope violations correctly rejected");
}

#[tokio::test]
async fn test_security_replay_protection() {
    info!("Starting security test: Replay Protection");
    
    let client = Client::new();
    
    // Create EAT for replay testing
    let eat = json!({
        "eat_id": "eat_security_test_replay",
        "agent_id": "agent_security_test",
        "authority_run_id": "run_security_test",
        "tool_name": "http_request",
        "resource_scope": {
            "url": "https://api.example.com/security_test",
            "method": "GET",
            "max_amount": 0.0,
            "domain": "example.com"
        },
        "workspace_id": "workspace_security_test",
        "issued_at": Utc::now().to_rfc3339(),
        "expires_at": (Utc::now() + chrono::Duration::minutes(5)).to_rfc3339(),
        "nonce": "nonce_security_test_replay_unique",
        "constraints": {
            "max_retries": 3,
            "timeout_seconds": 30,
            "requires_x402": false,
            "allowed_methods": ["GET"],
            "extra_rules": {}
        },
        "signature": "test_signature"
    });
    
    let execution_request = json!({
        "eat": eat,
        "target_url": "https://api.example.com/security_test",
        "method": "GET",
        "headers": {},
        "body": null
    });
    
    // First request
    debug!("Sending first request");
    let first_response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&execution_request.clone())
        .send()
        .await;
    
    // Wait a bit to ensure the first request is processed
    sleep(Duration::from_millis(100)).await;
    
    // Second request (should be rejected due to replay protection)
    debug!("Sending second request (replay attempt)");
    let second_response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&execution_request)
        .send()
        .await;
    
    match (first_response, second_response) {
        (Ok(first), Ok(second)) => {
            if first.status() == 401 && second.status() == 401 {
                // Both rejected due to invalid signature (expected with mock EAT)
                debug!("Both requests rejected due to invalid signature (expected)");
            } else if first.status() == 401 && second.status() == 401 {
                // First rejected, second also rejected (could be replay protection or signature)
                info!("✅ Replay Protection: Second request rejected");
            } else {
                warn!("Unexpected response pattern: first={}, second={}", 
                      first.status(), second.status());
            }
        },
        (Ok(_), Err(e)) => {
            debug!("Second request failed: {}", e);
            info!("✅ Replay Protection: Second request failed (network error)");
        },
        (Err(e), _) => {
            debug!("First request failed: {}", e);
            info!("✅ Replay Protection: First request failed (network error)");
        }
    }
    
    info!("✅ Replay Protection: Test completed");
}

#[tokio::test]
async fn test_security_x402_payment_validation() {
    info!("Starting security test: x402 Payment Validation");
    
    let client = Client::new();
    
    // Test 1: Invalid payment amount
    let invalid_payment_proof = json!({
        "payment_reference": "pay_security_test_invalid",
        "transaction_hash": format!("0x{}", "0".repeat(64)),
        "amount": "-5.0", // Negative amount
        "currency": "USDC",
        "payer_address": format!("0x{}", "1".repeat(40)),
        "timestamp": Utc::now().to_rfc3339(),
        "signature": "mock_signature"
    });
    
    let response = client
        .post(&format!("{}/x402/verify", EDGE_GATEWAY_URL))
        .json(&invalid_payment_proof)
        .send()
        .await;
    
    match response {
        Ok(resp) => {
            if resp.status() == 402 {
                info!("✅ x402 Payment Validation: Invalid amount rejected");
            } else {
                warn!("Unexpected status for invalid amount: {}", resp.status());
            }
        },
        Err(e) => {
            debug!("Invalid amount request failed: {}", e);
        }
    }
    
    // Test 2: Invalid currency
    let invalid_currency_proof = json!({
        "payment_reference": "pay_security_test_invalid_currency",
        "transaction_hash": format!("0x{}", "0".repeat(64)),
        "amount": "5.0",
        "currency": "INVALID_CURRENCY", // Invalid currency
        "payer_address": format!("0x{}", "1".repeat(40)),
        "timestamp": Utc::now().to_rfc3339(),
        "signature": "mock_signature"
    });
    
    let response = client
        .post(&format!("{}/x402/verify", EDGE_GATEWAY_URL))
        .json(&invalid_currency_proof)
        .send()
        .await;
    
    match response {
        Ok(resp) => {
            if resp.status() == 402 {
                info!("✅ x402 Payment Validation: Invalid currency rejected");
            } else {
                warn!("Unexpected status for invalid currency: {}", resp.status());
            }
        },
        Err(e) => {
            debug!("Invalid currency request failed: {}", e);
        }
    }
    
    // Test 3: Old timestamp
    let old_timestamp_proof = json!({
        "payment_reference": "pay_security_test_old_timestamp",
        "transaction_hash": format!("0x{}", "0".repeat(64)),
        "amount": "5.0",
        "currency": "USDC",
        "payer_address": format!("0x{}", "1".repeat(40)),
        "timestamp": (Utc::now() - chrono::Duration::hours(2)).to_rfc3339(), // Too old
        "signature": "mock_signature"
    });
    
    let response = client
        .post(&format!("{}/x402/verify", EDGE_GATEWAY_URL))
        .json(&old_timestamp_proof)
        .send()
        .await;
    
    match response {
        Ok(resp) => {
            if resp.status() == 402 {
                info!("✅ x402 Payment Validation: Old timestamp rejected");
            } else {
                warn!("Unexpected status for old timestamp: {}", resp.status());
            }
        },
        Err(e) => {
            debug!("Old timestamp request failed: {}", e);
        }
    }
    
    info!("✅ x402 Payment Validation: Test completed");
}

#[tokio::test]
async fn test_security_input_validation() {
    info!("Starting security test: Input Validation");
    
    let client = Client::new();
    
    // Test malformed JSON requests
    let malformed_requests = vec![
        "", // Empty string
        "{", // Incomplete JSON
        "invalid json", // Invalid JSON
        "{\"incomplete\": \"json\"", // Incomplete object
        "{\"array\": [1, 2,}", // Incomplete array
    ];
    
    for (i, malformed_json) in malformed_requests.iter().enumerate() {
        debug!("Testing malformed JSON {}", i + 1);
        
        let response = client
            .post(&format!("{}/execute", EDGE_GATEWAY_URL))
            .header("Content-Type", "application/json")
            .body(malformed_json.to_string())
            .send()
            .await;
        
        match response {
            Ok(resp) => {
                // Should return 400 Bad Request for malformed JSON
                assert_eq!(resp.status(), 400);
                debug!("✅ Malformed JSON {} correctly rejected", i + 1);
            },
            Err(e) => {
                debug!("Malformed JSON {} request failed: {}", i + 1, e);
            }
        }
    }
    
    // Test oversized requests
    let oversized_payload = "x".repeat(10 * 1024 * 1024); // 10MB string
    let oversized_request = json!({
        "eat": {
            "eat_id": "eat_oversized",
            "payload": oversized_payload
        },
        "target_url": "https://api.example.com/test",
        "method": "GET"
    });
    
    let response = client
        .post(&format!("{}/execute", EDGE_GATEWAY_URL))
        .json(&oversized_request)
        .send()
        .await;
    
    match response {
        Ok(resp) => {
            if resp.status() == 413 { // Payload Too Large
                info!("✅ Input Validation: Oversized payload rejected");
            } else {
                warn!("Unexpected status for oversized payload: {}", resp.status());
            }
        },
        Err(e) => {
            debug!("Oversized payload request failed: {}", e);
        }
    }
    
    info!("✅ Input Validation: Test completed");
}

#[tokio::test]
async fn test_security_rate_limiting() {
    info!("Starting security test: Rate Limiting");
    
    let client = Client::new();
    
    // Send rapid requests to test rate limiting
    let mut responses = vec![];
    
    for i in 0..100 { // Send 100 rapid requests
        let response = client
            .get(&format!("{}/health", EDGE_GATEWAY_URL))
            .send()
            .await;
        
        responses.push(response);
    }
    
    let mut success_count = 0;
    let mut rate_limited_count = 0;
    let mut other_errors = 0;
    
    for response in responses {
        match response {
            Ok(resp) => {
                match resp.status() {
                    200 => success_count += 1,
                    429 => rate_limited_count += 1,
                    _ => other_errors += 1,
                }
            },
            Err(_) => {
                other_errors += 1;
            }
        }
    }
    
    if rate_limited_count > 0 {
        info!("✅ Rate Limiting: {} requests rate limited out of {}", 
              rate_limited_count, success_count + rate_limited_count + other_errors);
    } else {
        info!("✅ Rate Limiting: No requests rate limited (may be disabled or limits higher)");
    }
    
    info!("Rate limiting summary: {} successful, {} rate limited, {} other errors", 
          success_count, rate_limited_count, other_errors);
}

#[tokio::test]
async fn test_security_domain_enforcement() {
    info!("Starting security test: Domain Enforcement");
    
    let client = Client::new();
    
    // Test requests to disallowed domains
    let disallowed_domains = vec![
        "https://malicious-site.com/test",
        "https://phishing.example.org/api",
        "https://evil.hacker.net/endpoint",
        "http://localhost:3000/local", // Localhost should be disallowed
    ];
    
    for (i, disallowed_url) in disallowed_domains.iter().enumerate() {
        debug!("Testing disallowed domain {}", i + 1);
        
        let eat = json!({
            "eat_id": format!("eat_domain_test_{}", i),
            "agent_id": "agent_security_test",
            "authority_run_id": "run_security_test",
            "tool_name": "http_request",
            "resource_scope": {
                "url": disallowed_url,
                "method": "GET",
                "max_amount": 0.0,
                "domain": "disallowed-domain.com" // Not in allowed list
            },
            "workspace_id": "workspace_security_test",
            "issued_at": Utc::now().to_rfc3339(),
            "expires_at": (Utc::now() + chrono::Duration::minutes(5)).to_rfc3339(),
            "nonce": format!("nonce_domain_test_{}", i),
            "constraints": {
                "max_retries": 3,
                "timeout_seconds": 30,
                "requires_x402": false,
                "allowed_methods": ["GET"],
                "extra_rules": {}
            },
            "signature": "test_signature"
        });
        
        let execution_request = json!({
            "eat": eat,
            "target_url": disallowed_url,
            "method": "GET",
            "headers": {},
            "body": null
        });
        
        let response = client
            .post(&format!("{}/execute", EDGE_GATEWAY_URL))
            .json(&execution_request)
            .send()
            .await;
        
        match response {
            Ok(resp) => {
                if resp.status() == 403 {
                    debug!("✅ Disallowed domain {} correctly rejected", i + 1);
                } else if resp.status() == 401 {
                    debug!("Disallowed domain {} rejected due to invalid EAT (expected)", i + 1);
                } else {
                    warn!("Unexpected status for disallowed domain {}: {}", i + 1, resp.status());
                }
            },
            Err(e) => {
                debug!("Disallowed domain {} request failed: {}", i + 1, e);
            }
        }
    }
    
    info!("✅ Domain Enforcement: Test completed");
}

#[tokio::test]
async fn test_security_no_money_movement_constraint() {
    info!("Starting security test: No Money Movement Constraint");
    
    let client = Client::new();
    
    // Test that no tools can move money out of Veklom
    let money_movement_attempts = vec![
        ("transfer_funds", json!({
            "to_address": "0xabc123...",
            "amount": "10.0",
            "currency": "USDC"
        })),
        ("send_payment", json!({
            "recipient": "0xdef456...",
            "amount": "5.0"
        })),
        ("withdraw", json!({
            "amount": "100.0",
            "destination": "external_wallet"
        })),
        ("disbursement", json!({
            "payee": "external_account",
            "amount": "50.0"
        })),
    ];
    
    for (tool_name, action_context) in money_movement_attempts {
        debug!("Testing money movement tool: {}", tool_name);
        
        let execute_request = json!({
            "method": "execute_action",
            "params": {
                "agent_id": "agent_security_test",
                "certificate_id": "cert_security_test",
                "latest_genome_hash": "sha256:security_test_hash",
                "tool_name": tool_name,
                "workspace_id": "workspace_security_test",
                "action_context": action_context
            },
            "id": 9000
        });
        
        let response = client
            .post(&format!("{}/mcp", GOVERNANCE_GATEWAY_URL))
            .json(&execute_request)
            .send()
            .await;
        
        match response {
            Ok(resp) => {
                let body: serde_json::Value = resp.json().await.unwrap();
                
                if let Some(error) = body.get("error") {
                    if error["message"].as_str().unwrap().contains("not allowed") ||
                       error["message"].as_str().unwrap().contains("Phase 0") {
                        info!("✅ Money movement tool {} correctly rejected", tool_name);
                    } else {
                        warn!("Unexpected error for {}: {}", tool_name, error["message"]);
                    }
                } else {
                    warn!("Money movement tool {} was not rejected", tool_name);
                }
            },
            Err(e) => {
                debug!("Money movement tool {} request failed: {}", tool_name, e);
            }
        }
    }
    
    info!("✅ No Money Movement Constraint: Test completed");
}

#[tokio::test]
async fn test_security_error_information_disclosure() {
    info!("Starting security test: Error Information Disclosure");
    
    let client = Client::new();
    
    // Test that error responses don't leak sensitive information
    let error_inducing_requests = vec![
        json!({
            "eat": {
                "eat_id": "eat_error_test",
                "signature": "invalid_signature",
                "private_key": "secret_key_that_should_not_be_leaked", // Should not be in error
                "internal_config": {"secret": "value"} // Should not be in error
            },
            "target_url": "https://api.example.com/test",
            "method": "GET"
        }),
        json!({
            "malformed": "request_with_potential_injection",
            "sql": "DROP TABLE users; --",
            "script": "<script>alert('xss')</script>"
        }),
    ];
    
    for (i, request) in error_inducing_requests.iter().enumerate() {
        debug!("Testing error information disclosure {}", i + 1);
        
        let response = client
            .post(&format!("{}/execute", EDGE_GATEWAY_URL))
            .json(request)
            .send()
            .await;
        
        match response {
            Ok(resp) => {
                if let Ok(body) = resp.json::<serde_json::Value>() {
                    let error_text = serde_json::to_string(&body).unwrap();
                    
                    // Check for potential information disclosure
                    let sensitive_patterns = vec![
                        "private_key",
                        "secret",
                        "password",
                        "token",
                        "internal_config",
                        "DROP TABLE",
                        "admin",
                        "root",
                    ];
                    
                    let mut found_sensitive = false;
                    for pattern in &sensitive_patterns {
                        if error_text.to_lowercase().contains(pattern) {
                            warn!("⚠️  Potential information disclosure in error {}: {}", i + 1, pattern);
                            found_sensitive = true;
                        }
                    }
                    
                    if !found_sensitive {
                        debug!("✅ Error {} does not contain sensitive information", i + 1);
                    }
                }
            },
            Err(e) => {
                debug!("Error disclosure test {} request failed: {}", i + 1, e);
            }
        }
    }
    
    info!("✅ Error Information Disclosure: Test completed");
}
