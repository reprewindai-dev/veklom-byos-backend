use crate::{
    errors::EdgeGatewayError,
    models::ExecutionAuthorizationToken,
    AppState,
};
use chrono::Utc;
use tracing::{info, debug, warn, error};
use std::collections::HashSet;

pub struct EATVerificationModule;

impl EATVerificationModule {
    /// Verify an Execution Authorization Token according to trust contract
    pub async fn verify_eat(
        eat: &ExecutionAuthorizationToken,
        state: &AppState,
    ) -> Result<(), EdgeGatewayError> {
        info!("Verifying EAT: {}", eat.eat_id);
        
        // Step 1: Check signature (using backend public key)
        Self::verify_signature(eat, &state.config).await?;
        
        // Step 2: Check expiration
        Self::verify_expiration(eat)?;
        
        // Step 3: Check replay protection (EAT ID)
        Self::verify_eat_id_replay(eat, state).await?;
        
        // Step 4: Check nonce replay protection
        Self::verify_nonce_replay(eat, state).await?;
        
        debug!("EAT verification successful: {}", eat.eat_id);
        Ok(())
    }
    
    /// Verify EAT signature using backend public key
    async fn verify_signature(
        eat: &ExecutionAuthorizationToken,
        config: &crate::config::Config,
    ) -> Result<(), EdgeGatewayError> {
        // In a real implementation, this would verify the signature using the backend's public key
        // For now, we'll use the verification method from the governance gateway
        
        // Create payload without signature for verification
        let payload = governance_gateway::models::EATPayload {
            eat_id: eat.eat_id.clone(),
            agent_id: eat.agent_id.clone(),
            authority_run_id: eat.authority_run_id.clone(),
            tool_name: eat.tool_name.clone(),
            resource_scope: eat.resource_scope.clone(),
            workspace_id: eat.workspace_id.clone(),
            issued_at: eat.issued_at,
            expires_at: eat.expires_at,
            nonce: eat.nonce.clone(),
            constraints: eat.constraints.clone(),
        };
        
        // Verify signature using the same method as governance gateway
        let is_valid = governance_gateway::modules::eat_minting::EATMintingModule::verify_eat_signature(
            eat, 
            &governance_gateway::config::Config {
                backend_url: config.backend_url.clone(),
                authority_url: String::new(), // Not needed for signature verification
                pgl_url: String::new(),
                audit_url: String::new(),
                gateway_port: 0,
                log_level: config.log_level.clone(),
            }
        ).await.map_err(|e| EdgeGatewayError::EATVerificationFailed(e.to_string()))?;
        
        if !is_valid {
            return Err(EdgeGatewayError::EATVerificationFailed(
                "Invalid signature".to_string()
            ));
        }
        
        Ok(())
    }
    
    /// Verify EAT is not expired
    fn verify_expiration(eat: &ExecutionAuthorizationToken) -> Result<(), EdgeGatewayError> {
        let now = Utc::now();
        
        if eat.expires_at <= now {
            warn!("EAT expired: {} (expired at: {})", eat.eat_id, eat.expires_at);
            return Err(EdgeGatewayError::EATExpired);
        }
        
        if eat.issued_at > now {
            warn!("EAT issued in the future: {} (issued at: {})", eat.eat_id, eat.issued_at);
            return Err(EdgeGatewayError::InvalidEAT(
                "Token issued in the future".to_string()
            ));
        }
        
        Ok(())
    }
    
    /// Verify EAT ID hasn't been used before (replay protection)
    async fn verify_eat_id_replay(
        eat: &ExecutionAuthorizationToken,
        state: &AppState,
    ) -> Result<(), EdgeGatewayError> {
        let mut used_eat_ids = state.used_eat_ids.write().await;
        
        if used_eat_ids.contains(&eat.eat_id) {
            warn!("EAT ID reuse detected: {}", eat.eat_id);
            return Err(EdgeGatewayError::EATReused);
        }
        
        // Mark this EAT ID as used
        used_eat_ids.insert(eat.eat_id.clone());
        
        // Clean up old EAT IDs (keep only recent ones to prevent memory growth)
        if used_eat_ids.len() > 10000 {
            // In a real implementation, you'd clean up based on timestamp
            // For now, just clear if it gets too large
            used_eat_ids.clear();
        }
        
        Ok(())
    }
    
    /// Verify nonce hasn't been used before (replay protection)
    async fn verify_nonce_replay(
        eat: &ExecutionAuthorizationToken,
        state: &AppState,
    ) -> Result<(), EdgeGatewayError> {
        let mut used_nonces = state.used_nonces.write().await;
        
        if used_nonces.contains(&eat.nonce) {
            warn!("Nonce reuse detected: {}", eat.nonce);
            return Err(EdgeGatewayError::EATReused);
        }
        
        // Mark this nonce as used
        used_nonces.insert(eat.nonce.clone());
        
        // Clean up old nonces (keep only recent ones)
        if used_nonces.len() > 10000 {
            used_nonces.clear();
        }
        
        Ok(())
    }
    
    /// Verify that the requested execution matches the EAT scope
    pub fn verify_scope(
        eat: &ExecutionAuthorizationToken,
        requested_tool: &str,
        requested_url: &str,
        requested_method: &str,
    ) -> Result<(), EdgeGatewayError> {
        // Check tool name
        if eat.tool_name != requested_tool {
            return Err(EdgeGatewayError::ScopeViolation(
                format!("Tool mismatch: expected {}, got {}", eat.tool_name, requested_tool)
            ));
        }
        
        // Check URL scope
        if let Some(scope_url) = &eat.resource_scope.url {
            if requested_url != *scope_url {
                return Err(EdgeGatewayError::ScopeViolation(
                    format!("URL mismatch: expected {}, got {}", scope_url, requested_url)
                ));
            }
        }
        
        // Check route scope (if no exact URL match)
        if let Some(scope_route) = &eat.resource_scope.route {
            if !requested_url.contains(scope_route) {
                return Err(EdgeGatewayError::ScopeViolation(
                    format!("Route mismatch: expected {}, got {}", scope_route, requested_url)
                ));
            }
        }
        
        // Check method constraints
        if !eat.constraints.allowed_methods.is_empty() {
            if !eat.constraints.allowed_methods.contains(&requested_method.to_string()) {
                return Err(EdgeGatewayError::ScopeViolation(
                    format!("Method not allowed: {}", requested_method)
                ));
            }
        }
        
        // Check domain constraints
        if let Some(allowed_domain) = &eat.resource_scope.domain {
            if let Ok(parsed_url) = url::Url::parse(requested_url) {
                if let Some(host) = parsed_url.host_str() {
                    if !host.ends_with(allowed_domain) {
                        return Err(EdgeGatewayError::ScopeViolation(
                            format!("Domain not allowed: {}", host)
                        ));
                    }
                }
            }
        }
        
        Ok(())
    }
    
    /// Check if x402 payment is required for this EAT
    pub fn requires_x402_payment(eat: &ExecutionAuthorizationToken) -> bool {
        eat.constraints.requires_x402 || eat.resource_scope.max_amount > 0.0
    }
    
    /// Get the maximum amount allowed by this EAT
    pub fn get_max_amount(eat: &ExecutionAuthorizationToken) -> f64 {
        eat.resource_scope.max_amount
    }
    
    /// Get timeout constraints from EAT
    pub fn get_timeout_seconds(eat: &ExecutionAuthorizationToken) -> u64 {
        eat.constraints.timeout_seconds
    }
    
    /// Get retry limit from EAT
    pub fn get_max_retries(eat: &ExecutionAuthorizationToken) -> u32 {
        eat.constraints.max_retries
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{ResourceScope, TokenConstraints};
    use chrono::{Duration, Utc};
    
    fn create_test_eat() -> ExecutionAuthorizationToken {
        ExecutionAuthorizationToken {
            eat_id: "test_eat_123".to_string(),
            agent_id: "agent_123".to_string(),
            authority_run_id: "run_456".to_string(),
            tool_name: "http_request".to_string(),
            resource_scope: ResourceScope {
                url: Some("https://api.example.com/test".to_string()),
                method: Some("GET".to_string()),
                max_amount: 0.0,
                domain: Some("example.com".to_string()),
                route: None,
            },
            workspace_id: "workspace_789".to_string(),
            issued_at: Utc::now(),
            expires_at: Utc::now() + Duration::minutes(5),
            nonce: "nonce_123".to_string(),
            constraints: TokenConstraints {
                max_retries: 3,
                timeout_seconds: 30,
                requires_x402: false,
                allowed_methods: vec!["GET".to_string(), "POST".to_string()],
                extra_rules: serde_json::json!({}),
            },
            signature: "test_signature".to_string(),
        }
    }
    
    #[test]
    fn test_verify_expiration_valid() {
        let eat = create_test_eat();
        assert!(EATVerificationModule::verify_expiration(&eat).is_ok());
    }
    
    #[test]
    fn test_verify_expiration_expired() {
        let mut eat = create_test_eat();
        eat.expires_at = Utc::now() - Duration::minutes(1);
        
        let result = EATVerificationModule::verify_expiration(&eat);
        assert!(matches!(result, Err(EdgeGatewayError::EATExpired)));
    }
    
    #[test]
    fn test_verify_scope_valid() {
        let eat = create_test_eat();
        assert!(EATVerificationModule::verify_scope(
            &eat, 
            "http_request", 
            "https://api.example.com/test", 
            "GET"
        ).is_ok());
    }
    
    #[test]
    fn test_verify_scope_invalid_tool() {
        let eat = create_test_eat();
        let result = EATVerificationModule::verify_scope(
            &eat, 
            "different_tool", 
            "https://api.example.com/test", 
            "GET"
        );
        assert!(matches!(result, Err(EdgeGatewayError::ScopeViolation(_))));
    }
    
    #[test]
    fn test_verify_scope_invalid_method() {
        let mut eat = create_test_eat();
        eat.constraints.allowed_methods = vec!["GET".to_string()];
        
        let result = EATVerificationModule::verify_scope(
            &eat, 
            "http_request", 
            "https://api.example.com/test", 
            "POST"
        );
        assert!(matches!(result, Err(EdgeGatewayError::ScopeViolation(_))));
    }
    
    #[test]
    fn test_requires_x402_payment() {
        let mut eat = create_test_eat();
        assert!(!EATVerificationModule::requires_x402_payment(&eat));
        
        eat.constraints.requires_x402 = true;
        assert!(EATVerificationModule::requires_x402_payment(&eat));
        
        eat.constraints.requires_x402 = false;
        eat.resource_scope.max_amount = 10.0;
        assert!(EATVerificationModule::requires_x402_payment(&eat));
    }
}
