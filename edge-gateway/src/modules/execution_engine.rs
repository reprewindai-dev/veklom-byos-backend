use crate::{
    errors::EdgeGatewayError,
    models::{ExecutionRequestPayload, ExecutionResult, ExecutionStatus},
    modules::eat_verification,
    AppState,
};
use chrono::Utc;
use std::time::Instant;
use tracing::{info, debug, warn, error};
use tokio::time::timeout;

pub struct ExecutionEngine;

impl ExecutionEngine {
    /// Execute a request with EAT verification and scope enforcement
    pub async fn execute_with_eat(
        request: ExecutionRequestPayload,
        state: &AppState,
    ) -> Result<ExecutionResult, EdgeGatewayError> {
        let start_time = Instant::now();
        info!("Executing request with EAT: {}", request.eat.eat_id);
        
        // Step 1: Verify EAT
        eat_verification::EATVerificationModule::verify_eat(&request.eat, state).await?;
        
        // Step 2: Verify scope
        eat_verification::EATVerificationModule::verify_scope(
            &request.eat,
            &request.eat.tool_name,
            &request.target_url,
            &request.method,
        )?;
        
        // Step 3: Check x402 requirements
        if eat_verification::EATVerificationModule::requires_x402_payment(&request.eat) {
            return Err(EdgeGatewayError::X402PaymentRequired);
        }
        
        // Step 4: Execute the request
        let execution_result = Self::execute_http_request(&request, &start_time, state).await?;
        
        info!("Execution completed: {} -> {}", request.eat.eat_id, execution_result.status);
        Ok(execution_result)
    }
    
    /// Execute HTTP request with timeout and size limits
    async fn execute_http_request(
        request: &ExecutionRequestPayload,
        start_time: &Instant,
        state: &AppState,
    ) -> Result<ExecutionResult, EdgeGatewayError> {
        let timeout_seconds = eat_verification::EATVerificationModule::get_timeout_seconds(&request.eat);
        let max_retries = eat_verification::EATVerificationModule::get_max_retries(&request.eat);
        
        let mut last_error = None;
        
        for attempt in 1..=max_retries {
            debug!("Execution attempt {} for EAT: {}", attempt, request.eat.eat_id);
            
            match Self::attempt_http_request(request, timeout_seconds, state).await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    warn!("Execution attempt {} failed: {}", attempt, e);
                    last_error = Some(e);
                    
                    // Don't retry on certain errors
                    if matches!(last_error.as_ref().unwrap(), 
                        EdgeGatewayError::ScopeViolation(_) | 
                        EdgeGatewayError::InvalidEAT(_) |
                        EdgeGatewayError::Unauthorized) {
                        break;
                    }
                    
                    // Wait before retry (exponential backoff)
                    if attempt < max_retries {
                        tokio::time::sleep(tokio::time::Duration::from_millis(100 * 2_u64.pow(attempt - 1))).await;
                    }
                }
            }
        }
        
        // All attempts failed
        Err(last_error.unwrap_or(EdgeGatewayError::ExecutionFailed(
            "All execution attempts failed".to_string()
        )))
    }
    
    /// Attempt a single HTTP request
    async fn attempt_http_request(
        request: &ExecutionRequestPayload,
        timeout_seconds: u64,
        state: &AppState,
    ) -> Result<ExecutionResult, EdgeGatewayError> {
        let execution_start = Instant::now();
        
        // Validate URL
        let url = url::Url::parse(&request.target_url)
            .map_err(|e| EdgeGatewayError::InvalidRequest(
                format!("Invalid URL: {}", e)
            ))?;
        
        // Validate domain against allowed domains
        Self::validate_domain(&url, &state.config.execution_config.allowed_domains)?;
        
        // Build HTTP request
        let mut http_request = state.http_client.request(
            match request.method.to_uppercase().as_str() {
                "GET" => reqwest::Method::GET,
                "POST" => reqwest::Method::POST,
                "PUT" => reqwest::Method::PUT,
                "DELETE" => reqwest::Method::DELETE,
                "PATCH" => reqwest::Method::PATCH,
                "HEAD" => reqwest::Method::HEAD,
                _ => return Err(EdgeGatewayError::InvalidRequest(
                    format!("Unsupported HTTP method: {}", request.method)
                )),
            },
            url.clone()
        );
        
        // Add headers
        for (key, value) in &request.headers {
            http_request = http_request.header(key, value);
        }
        
        // Add body if present
        if let Some(body) = &request.body {
            http_request = http_request.body(body.clone());
        }
        
        // Set timeout
        let timeout_duration = std::time::Duration::from_secs(
            request.timeout_seconds.unwrap_or(timeout_seconds)
        );
        
        // Execute request with timeout
        let response = timeout(timeout_duration, http_request.send()).await
            .map_err(|_| EdgeGatewayError::ExecutionTimeout)?
            .map_err(|e| EdgeGatewayError::ExecutionFailed(
                format!("HTTP request failed: {}", e)
            ))?;
        
        // Get response details
        let status_code = response.status().as_u16();
        let response_headers = response.headers().iter()
            .filter_map(|(k, v)| v.to_str().ok().map(|v| (k.to_string(), v.to_string())))
            .collect();
        
        // Read response body with size limit
        let response_body = Self::read_response_body(response, &state.config).await?;
        
        let execution_time_ms = execution_start.elapsed().as_millis() as u64;
        
        // Determine execution status
        let status = if status_code < 400 {
            ExecutionStatus::Success
        } else if status_code < 500 {
            ExecutionStatus::Rejected
        } else {
            ExecutionStatus::Error
        };
        
        Ok(ExecutionResult {
            eat_id: request.eat.eat_id.clone(),
            authority_run_id: request.eat.authority_run_id.clone(),
            status,
            response_code: Some(status_code),
            response_body: Some(response_body),
            response_headers: Some(response_headers),
            execution_time_ms,
            error_message: None,
            x402_payment_reference: None,
            completed_at: Utc::now(),
        })
    }
    
    /// Read response body with size limit
    async fn read_response_body(
        response: reqwest::Response,
        config: &crate::config::Config,
    ) -> Result<String, EdgeGatewayError> {
        let content_length = response.content_length().unwrap_or(0);
        
        if content_length > config.execution_config.max_response_size_bytes as u64 {
            return Err(EdgeGatewayError::ExecutionFailed(
                format!("Response too large: {} bytes", content_length)
            ));
        }
        
        let body = response.text().await
            .map_err(|e| EdgeGatewayError::ExecutionFailed(
                format!("Failed to read response body: {}", e)
            ))?;
        
        if body.len() > config.execution_config.max_response_size_bytes {
            return Err(EdgeGatewayError::ExecutionFailed(
                format!("Response body too large: {} bytes", body.len())
            ));
        }
        
        Ok(body)
    }
    
    /// Validate domain against allowed domains
    fn validate_domain(
        url: &url::Url,
        allowed_domains: &[String],
    ) -> Result<(), EdgeGatewayError> {
        if let Some(host) = url.host_str() {
            let is_allowed = allowed_domains.iter().any(|allowed| {
                host.ends_with(allowed) || host == allowed
            });
            
            if !is_allowed {
                return Err(EdgeGatewayError::ScopeViolation(
                    format!("Domain not allowed: {}", host)
                ));
            }
        } else {
            return Err(EdgeGatewayError::InvalidRequest(
                "URL must have a valid host".to_string()
            ));
        }
        
        Ok(())
    }
    
    /// Execute a paid endpoint (requires x402 payment)
    pub async fn execute_paid_endpoint(
        request: ExecutionRequestPayload,
        payment_reference: String,
        state: &AppState,
    ) -> Result<ExecutionResult, EdgeGatewayError> {
        let start_time = Instant::now();
        info!("Executing paid endpoint with payment: {}", payment_reference);
        
        // Verify EAT first
        eat_verification::EATVerificationModule::verify_eat(&request.eat, state).await?;
        
        // Verify scope
        eat_verification::EATVerificationModule::verify_scope(
            &request.eat,
            &request.eat.tool_name,
            &request.target_url,
            &request.method,
        )?;
        
        // Execute the request
        let mut result = Self::execute_http_request(&request, &start_time, state).await?;
        
        // Add payment reference to result
        result.x402_payment_reference = Some(payment_reference);
        
        Ok(result)
    }
    
    /// Create execution receipt for audit trail
    pub fn create_execution_receipt(
        result: &ExecutionResult,
    ) -> crate::models::ExecutionReceipt {
        crate::models::ExecutionReceipt {
            eat_id: result.eat_id.clone(),
            authority_run_id: result.authority_run_id.clone(),
            status: result.status.clone(),
            response_summary: result.response_body.as_ref().map(|body| {
                if body.len() > 1000 {
                    format!("{}... (truncated)", &body[..1000])
                } else {
                    body.clone()
                }
            }),
            response_hash: result.response_body.as_ref().map(|body| {
                use sha2::{Sha256, Digest};
                let mut hasher = Sha256::new();
                hasher.update(body.as_bytes());
                format!("sha256:{}", hex::encode(hasher.finalize()))
            }),
            execution_time_ms: result.execution_time_ms,
            x402_payment_reference: result.x402_payment_reference.clone(),
            error_details: result.error_message.clone(),
            completed_at: result.completed_at,
        }
    }
    
    /// Check if execution should be retried based on error
    pub fn should_retry(error: &EdgeGatewayError) -> bool {
        match error {
            EdgeGatewayError::ExecutionTimeout |
            EdgeGatewayError::ExecutionFailed(_) |
            EdgeGatewayError::HttpClientError(_) => true,
            
            EdgeGatewayError::InvalidEAT(_) |
            EdgeGatewayError::EATVerificationFailed(_) |
            EdgeGatewayError::EATExpired |
            EdgeGatewayError::EATReused |
            EdgeGatewayError::ScopeViolation(_) |
            EdgeGatewayError::X402PaymentRequired |
            EdgeGatewayError::X402VerificationFailed(_) |
            EdgeGatewayError::RateLimitExceeded |
            EdgeGatewayError::Unauthorized => false,
            
            _ => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{ExecutionAuthorizationToken, ResourceScope, TokenConstraints};
    use chrono::{Duration, Utc};
    
    fn create_test_request() -> ExecutionRequestPayload {
        ExecutionRequestPayload {
            eat: ExecutionAuthorizationToken {
                eat_id: "test_eat".to_string(),
                agent_id: "test_agent".to_string(),
                authority_run_id: "test_run".to_string(),
                tool_name: "http_request".to_string(),
                resource_scope: ResourceScope {
                    url: Some("https://api.example.com/test".to_string()),
                    method: Some("GET".to_string()),
                    max_amount: 0.0,
                    domain: Some("example.com".to_string()),
                    route: None,
                },
                workspace_id: "test_workspace".to_string(),
                issued_at: Utc::now(),
                expires_at: Utc::now() + Duration::minutes(5),
                nonce: "test_nonce".to_string(),
                constraints: TokenConstraints {
                    max_retries: 3,
                    timeout_seconds: 30,
                    requires_x402: false,
                    allowed_methods: vec!["GET".to_string()],
                    extra_rules: serde_json::json!({}),
                },
                signature: "test_signature".to_string(),
            },
            target_url: "https://api.example.com/test".to_string(),
            method: "GET".to_string(),
            headers: std::collections::HashMap::new(),
            body: None,
            timeout_seconds: Some(30),
        }
    }
    
    #[test]
    fn test_validate_domain_allowed() {
        let url = url::Url::parse("https://api.example.com/test").unwrap();
        let allowed_domains = vec!["example.com".to_string()];
        
        assert!(ExecutionEngine::validate_domain(&url, &allowed_domains).is_ok());
    }
    
    #[test]
    fn test_validate_domain_not_allowed() {
        let url = url::Url::parse("https://api.evil.com/test").unwrap();
        let allowed_domains = vec!["example.com".to_string()];
        
        assert!(ExecutionEngine::validate_domain(&url, &allowed_domains).is_err());
    }
    
    #[test]
    fn test_should_retry() {
        assert!(ExecutionEngine::should_retry(&EdgeGatewayError::ExecutionTimeout));
        assert!(ExecutionEngine::should_retry(&EdgeGatewayError::ExecutionFailed("test".to_string())));
        
        assert!(!ExecutionEngine::should_retry(&EdgeGatewayError::InvalidEAT("test".to_string())));
        assert!(!ExecutionEngine::should_retry(&EdgeGatewayError::ScopeViolation("test".to_string())));
        assert!(!ExecutionEngine::should_retry(&EdgeGatewayError::Unauthorized));
    }
    
    #[test]
    fn test_create_execution_receipt() {
        let result = ExecutionResult {
            eat_id: "test_eat".to_string(),
            authority_run_id: "test_run".to_string(),
            status: ExecutionStatus::Success,
            response_code: Some(200),
            response_body: Some("test response".to_string()),
            response_headers: None,
            execution_time_ms: 100,
            error_message: None,
            x402_payment_reference: None,
            completed_at: Utc::now(),
        };
        
        let receipt = ExecutionEngine::create_execution_receipt(&result);
        
        assert_eq!(receipt.eat_id, "test_eat");
        assert_eq!(receipt.authority_run_id, "test_run");
        assert_eq!(receipt.status, ExecutionStatus::Success);
        assert_eq!(receipt.execution_time_ms, 100);
        assert!(receipt.response_summary.is_some());
        assert!(receipt.response_hash.is_some());
    }
}
