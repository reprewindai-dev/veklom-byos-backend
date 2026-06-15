use crate::{
    errors::GatewayError,
    models::{
        ExecutionAuthorizationToken, EATPayload, ResourceScope, 
        TokenConstraints, IdentityContext, PolicyCheckResponse
    },
    AppState,
};
use chrono::{Duration, Utc};
use serde_json::json;
use sha2::{Sha256, Digest};
use tracing::{info, debug, error};
use uuid::Uuid;

pub struct EATMintingModule;

impl EATMintingModule {
    /// Mint an Execution Authorization Token for an approved action
    pub async fn mint_eat(
        identity_context: &IdentityContext,
        authority_run_id: &str,
        tool_name: &str,
        workspace_id: &str,
        policy_response: &PolicyCheckResponse,
        action_context: &serde_json::Value,
        state: &AppState,
    ) -> Result<ExecutionAuthorizationToken, GatewayError> {
        info!("Minting EAT for tool: {}, agent: {}", tool_name, identity_context.agent_id);
        
        // Generate EAT components
        let eat_id = format!("eat_{}", Uuid::new_v4().to_string().replace("-", "")[..16].to_string());
        let nonce = Self::generate_nonce();
        let issued_at = Utc::now();
        let expires_at = issued_at + Duration::seconds(120); // 2 minutes TTL
        
        // Build resource scope based on tool and context
        let resource_scope = Self::build_resource_scope(tool_name, action_context, policy_response)?;
        
        // Build constraints based on policy and tool
        let constraints = Self::build_constraints(tool_name, policy_response, action_context)?;
        
        // Create canonical payload for signing
        let payload = EATPayload {
            eat_id: eat_id.clone(),
            agent_id: identity_context.agent_id.clone(),
            authority_run_id: authority_run_id.to_string(),
            tool_name: tool_name.to_string(),
            resource_scope: resource_scope.clone(),
            workspace_id: workspace_id.to_string(),
            issued_at,
            expires_at,
            nonce: nonce.clone(),
            constraints: constraints.clone(),
        };
        
        // Sign the payload
        let signature = Self::sign_payload(&payload, &state.config).await?;
        
        let eat = ExecutionAuthorizationToken {
            eat_id,
            agent_id: identity_context.agent_id.clone(),
            authority_run_id: authority_run_id.to_string(),
            tool_name: tool_name.to_string(),
            resource_scope,
            workspace_id: workspace_id.to_string(),
            issued_at,
            expires_at,
            nonce,
            constraints,
            signature,
        };
        
        debug!("EAT minted successfully: {}", eat.eat_id);
        Ok(eat)
    }
    
    fn build_resource_scope(
        tool_name: &str,
        action_context: &serde_json::Value,
        policy_response: &PolicyCheckResponse,
    ) -> Result<ResourceScope, GatewayError> {
        match tool_name {
            "http_request" => {
                let url = action_context.get("url")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| GatewayError::InvalidRequest("Missing URL in action context".to_string()))?;
                    
                let method = action_context.get("method")
                    .and_then(|v| v.as_str())
                    .unwrap_or("GET")
                    .to_string();
                
                // Parse URL to extract domain
                let domain = url::Url::parse(url)
                    .ok()
                    .and_then(|parsed| parsed.host_str())
                    .map(|s| s.to_string());
                
                Ok(ResourceScope {
                    url: Some(url.to_string()),
                    method: Some(method),
                    max_amount: 0.0, // No money movement in Phase 0 & 1
                    domain,
                    route: None,
                })
            },
            "webhook_trigger" => {
                let webhook_url = action_context.get("webhook_url")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| GatewayError::InvalidRequest("Missing webhook_url in action context".to_string()))?;
                
                let domain = url::Url::parse(webhook_url)
                    .ok()
                    .and_then(|parsed| parsed.host_str())
                    .map(|s| s.to_string());
                
                Ok(ResourceScope {
                    url: Some(webhook_url.to_string()),
                    method: Some("POST".to_string()),
                    max_amount: 0.0,
                    domain,
                    route: None,
                })
            },
            "browser_session" => {
                Ok(ResourceScope {
                    url: None,
                    method: None,
                    max_amount: 0.0,
                    domain: None,
                    route: Some("/browser/session".to_string()),
                })
            },
            "paid_endpoint_access" => {
                let endpoint = action_context.get("endpoint")
                    .and_then(|v| v.as_str())
                    .unwrap_or("/api/v1/premium");
                
                Ok(ResourceScope {
                    url: None,
                    method: Some("GET".to_string()),
                    max_amount: action_context.get("max_cost")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                    domain: None,
                    route: Some(endpoint.to_string()),
                })
            },
            _ => {
                // Default scope for unknown tools
                Ok(ResourceScope {
                    url: None,
                    method: None,
                    max_amount: 0.0,
                    domain: None,
                    route: None,
                })
            }
        }
    }
    
    fn build_constraints(
        tool_name: &str,
        policy_response: &PolicyCheckResponse,
        action_context: &serde_json::Value,
    ) -> Result<TokenConstraints, GatewayError> {
        let mut constraints = TokenConstraints {
            max_retries: 3,
            timeout_seconds: 30,
            requires_x402: false,
            allowed_methods: vec!["GET".to_string(), "POST".to_string()],
            extra_rules: json!({}),
        };
        
        // Tool-specific constraints
        match tool_name {
            "http_request" => {
                if let Some(method) = action_context.get("method").and_then(|v| v.as_str()) {
                    constraints.allowed_methods = vec![method.to_string()];
                }
                constraints.timeout_seconds = action_context.get("timeout")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(30);
            },
            "webhook_trigger" => {
                constraints.allowed_methods = vec!["POST".to_string()];
                constraints.timeout_seconds = 60; // Webhooks might need more time
            },
            "browser_session" => {
                constraints.timeout_seconds = 300; // 5 minutes for browser sessions
                constraints.max_retries = 1; // No retries for browser sessions
            },
            "paid_endpoint_access" => {
                constraints.requires_x402 = true;
                constraints.timeout_seconds = 120;
            },
            _ => {
                // Default constraints
            }
        }
        
        // Apply policy-based constraints
        if let Some(reason) = &policy_response.reason {
            constraints.extra_rules["policy_reason"] = json!(reason);
        }
        
        Ok(constraints)
    }
    
    fn generate_nonce() -> String {
        Uuid::new_v4().to_string().replace("-", "")[..16].to_string()
    }
    
    async fn sign_payload(payload: &EATPayload, config: &crate::config::Config) -> Result<String, GatewayError> {
        // In a real implementation, this would use a proper cryptographic key
        // For Phase 0A, we'll use a simple HMAC-style signature
        
        let canonical_json = serde_json::to_string(payload)
            .map_err(|e| GatewayError::SerializationError(e))?;
            
        let mut hasher = Sha256::new();
        hasher.update(canonical_json.as_bytes());
        
        // In production, use actual private key signing
        // For now, we'll use a deterministic approach based on configuration
        let config_hash = format!("{}:{}:{}", 
            config.backend_url, 
            config.authority_url, 
            config.pgl_url
        );
        hasher.update(config_hash.as_bytes());
        
        let result = hasher.finalize();
        Ok(format!("sig_{}", hex::encode(result)))
    }
    
    /// Verify an EAT signature (for edge MCP use)
    pub async fn verify_eat_signature(
        eat: &ExecutionAuthorizationToken,
        config: &crate::config::Config,
    ) -> Result<bool, GatewayError> {
        // Create payload without signature
        let payload = EATPayload {
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
        
        // Recreate signature
        let expected_signature = Self::sign_payload(&payload, config).await?;
        
        Ok(eat.signature == expected_signature)
    }
    
    /// Check if an EAT is still valid (not expired)
    pub fn is_eat_valid(eat: &ExecutionAuthorizationToken) -> bool {
        let now = Utc::now();
        eat.expires_at > now && eat.issued_at <= now
    }
    
    /// Check if an EAT matches the requested execution parameters
    pub fn validate_eat_scope(
        eat: &ExecutionAuthorizationToken,
        requested_tool: &str,
        requested_resource: &str,
        requested_method: &str,
    ) -> Result<bool, GatewayError> {
        // Check tool name
        if eat.tool_name != requested_tool {
            return Ok(false);
        }
        
        // Check resource scope
        if let Some(scope_url) = &eat.resource_scope.url {
            if requested_resource != *scope_url {
                return Ok(false);
            }
        }
        
        if let Some(scope_route) = &eat.resource_scope.route {
            if !requested_resource.contains(scope_route) {
                return Ok(false);
            }
        }
        
        // Check method constraints
        if !eat.constraints.allowed_methods.is_empty() {
            if !eat.constraints.allowed_methods.contains(&requested_method.to_string()) {
                return Ok(false);
            }
        }
        
        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{IdentityContext, PolicyDecision, PolicyCheckResponse};
    
    #[test]
    fn test_generate_nonce() {
        let nonce1 = EATMintingModule::generate_nonce();
        let nonce2 = EATMintingModule::generate_nonce();
        
        assert_eq!(nonce1.len(), 16);
        assert_eq!(nonce2.len(), 16);
        assert_ne!(nonce1, nonce2);
    }
    
    #[test]
    fn test_eat_validity() {
        let now = Utc::now();
        let valid_eat = ExecutionAuthorizationToken {
            eat_id: "test".to_string(),
            agent_id: "agent".to_string(),
            authority_run_id: "run".to_string(),
            tool_name: "test_tool".to_string(),
            resource_scope: ResourceScope {
                url: None,
                method: None,
                max_amount: 0.0,
                domain: None,
                route: None,
            },
            workspace_id: "workspace".to_string(),
            issued_at: now - Duration::seconds(60),
            expires_at: now + Duration::seconds(60),
            nonce: "nonce".to_string(),
            constraints: TokenConstraints {
                max_retries: 3,
                timeout_seconds: 30,
                requires_x402: false,
                allowed_methods: vec!["GET".to_string()],
                extra_rules: json!({}),
            },
            signature: "sig".to_string(),
        };
        
        assert!(EATMintingModule::is_eat_valid(&valid_eat));
        
        let expired_eat = ExecutionAuthorizationToken {
            expires_at: now - Duration::seconds(1),
            ..valid_eat.clone()
        };
        
        assert!(!EATMintingModule::is_eat_valid(&expired_eat));
    }
    
    #[test]
    fn test_validate_eat_scope() {
        let eat = ExecutionAuthorizationToken {
            eat_id: "test".to_string(),
            agent_id: "agent".to_string(),
            authority_run_id: "run".to_string(),
            tool_name: "http_request".to_string(),
            resource_scope: ResourceScope {
                url: Some("https://api.example.com/data".to_string()),
                method: Some("GET".to_string()),
                max_amount: 0.0,
                domain: Some("api.example.com".to_string()),
                route: None,
            },
            workspace_id: "workspace".to_string(),
            issued_at: Utc::now(),
            expires_at: Utc::now() + Duration::seconds(60),
            nonce: "nonce".to_string(),
            constraints: TokenConstraints {
                max_retries: 3,
                timeout_seconds: 30,
                requires_x402: false,
                allowed_methods: vec!["GET".to_string()],
                extra_rules: json!({}),
            },
            signature: "sig".to_string(),
        };
        
        // Valid match
        assert!(EATMintingModule::validate_eat_scope(
            &eat, 
            "http_request", 
            "https://api.example.com/data", 
            "GET"
        ).unwrap());
        
        // Invalid tool name
        assert!(!EATMintingModule::validate_eat_scope(
            &eat, 
            "different_tool", 
            "https://api.example.com/data", 
            "GET"
        ).unwrap());
        
        // Invalid method
        assert!(!EATMintingModule::validate_eat_scope(
            &eat, 
            "http_request", 
            "https://api.example.com/data", 
            "POST"
        ).unwrap());
    }
}
