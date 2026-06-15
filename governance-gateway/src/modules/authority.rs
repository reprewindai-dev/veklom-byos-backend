use crate::{
    errors::GatewayError,
    models::{IdentityContext, PolicyCheckRequest, PolicyCheckResponse, PolicyDecision},
    AppState,
};
use reqwest::Client;
use serde_json::{json, Value};
use tracing::{info, error, debug};
use uuid::Uuid;

pub struct AuthorityModule;

impl AuthorityModule {
    /// 0A.3 Policy Gate Tool (UACP integration)
    /// Call UACP with identity + action + context and enforce decision
    pub async fn check_action(
        identity_context: &IdentityContext,
        authority_bundle_id: &str,
        tool_name: &str,
        workspace_id: &str,
        action_context: Option<Value>,
        state: &AppState,
    ) -> Result<PolicyCheckResponse, GatewayError> {
        info!(
            "Checking policy for tool: {}, bundle: {}, agent: {}",
            tool_name, authority_bundle_id, identity_context.agent_id
        );
        
        // Build policy check request
        let policy_request = PolicyCheckRequest {
            identity_context: identity_context.clone(),
            authority_bundle_id: authority_bundle_id.to_string(),
            tool_name: tool_name.to_string(),
            workspace_id: workspace_id.to_string(),
            action_context,
        };
        
        // Call UACP / authority service via internal HTTP
        let response = Self::call_authority_service(&policy_request, &state.http_client, &state.config.authority_url).await?;
        
        debug!("Policy check response: {:?}", response);
        
        Ok(response)
    }
    
    async fn call_authority_service(
        request: &PolicyCheckRequest,
        client: &Client,
        authority_url: &str,
    ) -> Result<PolicyCheckResponse, GatewayError> {
        let url = format!("{}/check", authority_url);
        
        debug!("Calling authority service at: {}", url);
        
        let request_body = json!({
            "identity_context": {
                "agent_id": request.identity_context.agent_id,
                "certificate_id": request.identity_context.certificate_id,
                "jurisdiction": request.identity_context.jurisdiction,
                "risk_level": request.identity_context.risk_level,
                "lineage_summary": request.identity_context.lineage_summary,
                "latest_genome_hash": request.identity_context.latest_genome_hash,
                "status": request.identity_context.status
            },
            "authority_bundle_id": request.authority_bundle_id,
            "tool_name": request.tool_name,
            "workspace_id": request.workspace_id,
            "action_context": request.action_context
        });
        
        let response = client
            .post(&url)
            .json(&request_body)
            .send()
            .await
            .map_err(|e| GatewayError::PolicyCheckFailed(format!("Failed to call authority service: {}", e)))?;
            
        if !response.status().is_success() {
            return Err(GatewayError::PolicyCheckFailed(
                format!("Authority service returned status: {}", response.status())
            ));
        }
        
        let response_data: Value = response
            .json()
            .await
            .map_err(|e| GatewayError::PolicyCheckFailed(format!("Failed to parse authority response: {}", e)))?;
            
        // Parse response
        let decision_str = response_data["decision"]
            .as_str()
            .ok_or_else(|| GatewayError::PolicyCheckFailed("Missing decision in authority response".to_string()))?;
            
        let decision = match decision_str {
            "allow" => PolicyDecision::Allow,
            "deny" => PolicyDecision::Deny,
            "needs_approval" => PolicyDecision::NeedsApproval,
            _ => return Err(GatewayError::PolicyCheckFailed(
                format!("Invalid decision value: {}", decision_str)
            )),
        };
        
        let reason = response_data["reason"].as_str().map(|s| s.to_string());
        let approver_role = response_data["approver_role"].as_str().map(|s| s.to_string());
        
        Ok(PolicyCheckResponse {
            decision,
            reason,
            approver_role,
        })
    }
    
    /// Get authority bundle ID for an agent based on their identity
    pub fn get_authority_bundle_id(identity_context: &IdentityContext) -> String {
        // In a real implementation, this would be derived from the agent's birth certificate
        // or from a mapping service. For Phase 0A, we'll use a simple pattern.
        format!("bundle_{}", identity_context.agent_id.replace("agent_", ""))
    }
    
    /// Check if a tool requires approval based on policy response
    pub fn requires_approval(response: &PolicyCheckResponse) -> bool {
        matches!(response.decision, PolicyDecision::NeedsApproval)
    }
    
    /// Check if a tool is allowed based on policy response
    pub fn is_allowed(response: &PolicyCheckResponse) -> bool {
        matches!(response.decision, PolicyDecision::Allow)
    }
    
    /// Get human-readable decision description
    pub fn get_decision_description(response: &PolicyCheckResponse) -> String {
        match &response.decision {
            PolicyDecision::Allow => "Allowed".to_string(),
            PolicyDecision::Deny => {
                if let Some(reason) = &response.reason {
                    format!("Denied: {}", reason)
                } else {
                    "Denied".to_string()
                }
            },
            PolicyDecision::NeedsApproval => {
                if let Some(approver) = &response.approver_role {
                    format!("Needs approval from {}", approver)
                } else {
                    "Needs approval".to_string()
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::IdentityContext;
    
    #[test]
    fn test_get_authority_bundle_id() {
        let identity = IdentityContext {
            agent_id: "agent_12345".to_string(),
            certificate_id: "cert_abc".to_string(),
            jurisdiction: "US".to_string(),
            risk_level: "medium".to_string(),
            lineage_summary: "lineage://test".to_string(),
            latest_genome_hash: "hash123".to_string(),
            status: "active".to_string(),
        };
        
        let bundle_id = AuthorityModule::get_authority_bundle_id(&identity);
        assert_eq!(bundle_id, "bundle_12345");
    }
    
    #[test]
    fn test_policy_decision_helpers() {
        let allow_response = PolicyCheckResponse {
            decision: PolicyDecision::Allow,
            reason: None,
            approver_role: None,
        };
        
        let deny_response = PolicyCheckResponse {
            decision: PolicyDecision::Deny,
            reason: Some("Tool not permitted".to_string()),
            approver_role: None,
        };
        
        let approval_response = PolicyCheckResponse {
            decision: PolicyDecision::NeedsApproval,
            reason: None,
            approver_role: Some("admin".to_string()),
        };
        
        assert!(AuthorityModule::is_allowed(&allow_response));
        assert!(!AuthorityModule::is_allowed(&deny_response));
        assert!(!AuthorityModule::is_allowed(&approval_response));
        
        assert!(!AuthorityModule::requires_approval(&allow_response));
        assert!(!AuthorityModule::requires_approval(&deny_response));
        assert!(AuthorityModule::requires_approval(&approval_response));
        
        assert_eq!(AuthorityModule::get_decision_description(&allow_response), "Allowed");
        assert_eq!(AuthorityModule::get_decision_description(&deny_response), "Denied: Tool not permitted");
        assert_eq!(AuthorityModule::get_decision_description(&approval_response), "Needs approval from admin");
    }
}
