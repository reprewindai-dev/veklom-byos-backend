use crate::{
    errors::GatewayError,
    models::{MCPRequest, MCPResponse, MCPError, ExecuteActionParams},
    modules::{identity, authority, audit_ledger, eat_minting},
    AppState,
};
use serde_json::{json, Value};
use tracing::{info, error, debug, warn};
use std::collections::HashMap;

pub struct MCPInterfaceModule;

impl MCPInterfaceModule {
    /// 0A.5 MCP "execute_action" without real side effects
    /// Main MCP tool that uses policy_gate internally
    pub async fn handle_execute_action(
        params: ExecuteActionParams,
        state: &AppState,
    ) -> Result<MCPResponse, GatewayError> {
        info!(
            "Handling execute_action for agent: {}, tool: {}",
            params.agent_id, params.tool_name
        );
        
        // Generate authority run ID for this session
        let authority_run_id = identity::IdentityModule::generate_authority_run_id();
        
        // Step 1: Verify identity (0A.2)
        let identity_context = match identity::IdentityModule::verify_session(
            &params.agent_id,
            &params.certificate_id,
            &params.latest_genome_hash,
            state,
        ).await {
            Ok(context) => {
                // Record successful session verification
                if let Err(e) = audit_ledger::AuditLedgerModule::record_session_verified(
                    &params.agent_id,
                    &authority_run_id,
                    &params.certificate_id,
                    state,
                ).await {
                    warn!("Failed to record session verification: {}", e);
                }
                context
            },
            Err(e) => {
                // Record failed session verification
                if let Err(audit_err) = audit_ledger::AuditLedgerModule::record_session_rejected(
                    &params.agent_id,
                    &authority_run_id,
                    &params.certificate_id,
                    &e.to_string(),
                    state,
                ).await {
                    warn!("Failed to record session rejection: {}", audit_err);
                }
                
                return Ok(MCPResponse {
                    result: None,
                    error: Some(MCPError {
                        code: -32001,
                        message: format!("Identity verification failed: {}", e),
                        data: None,
                    }),
                    id: None,
                });
            }
        };
        
        // Step 2: Get authority bundle ID
        let authority_bundle_id = authority::AuthorityModule::get_authority_bundle_id(&identity_context);
        
        // Step 3: Record tool call attempt (0A.4)
        if let Err(e) = audit_ledger::AuditLedgerModule::record_tool_call_attempt(
            &params.agent_id,
            &authority_run_id,
            &params.tool_name,
            &params.action_context.unwrap_or(Value::Null),
            state,
        ).await {
            warn!("Failed to record tool call attempt: {}", e);
        }
        
        // Step 4: Policy gate check (0A.3)
        let policy_response = authority::AuthorityModule::check_action(
            &identity_context,
            &authority_bundle_id,
            &params.tool_name,
            &params.workspace_id,
            params.action_context,
            state,
        ).await?;
        
        // Step 5: Handle policy decision and record result
        match policy_response.decision {
            crate::models::PolicyDecision::Allow => {
                // Record allowed decision
                if let Err(e) = audit_ledger::AuditLedgerModule::record_tool_call_allowed(
                    &params.agent_id,
                    &authority_run_id,
                    &params.tool_name,
                    policy_response.reason.as_deref(),
                    state,
                ).await {
                    warn!("Failed to record tool call allowed: {}", e);
                }
                
                // Mint a real EAT token for the allowed action!
                let action_ctx = params.action_context.clone().unwrap_or(Value::Null);
                let eat = match eat_minting::EATMintingModule::mint_eat(
                    &identity_context,
                    &authority_run_id,
                    &params.tool_name,
                    &params.workspace_id,
                    &policy_response,
                    &action_ctx,
                    state,
                ).await {
                    Ok(token) => token,
                    Err(e) => {
                        error!("Failed to mint EAT token: {}", e);
                        return Ok(MCPResponse {
                            result: None,
                            error: Some(MCPError {
                                code: -32004,
                                message: format!("Failed to mint Execution Authorization Token: {}", e),
                                data: None,
                            }),
                            id: None,
                        });
                    }
                };

                let result = json!({
                    "status": "allowed",
                    "message": format!("Execution authorized for tool: {}", params.tool_name),
                    "authority_run_id": authority_run_id,
                    "decision": authority::AuthorityModule::get_decision_description(&policy_response),
                    "eat": eat
                });
                
                Ok(MCPResponse {
                    result: Some(result),
                    error: None,
                    id: None,
                })
            },
            crate::models::PolicyDecision::Deny => {
                // Record denied decision
                if let Err(e) = audit_ledger::AuditLedgerModule::record_tool_call_denied(
                    &params.agent_id,
                    &authority_run_id,
                    &params.tool_name,
                    policy_response.reason.as_deref().unwrap_or("No reason provided"),
                    state,
                ).await {
                    warn!("Failed to record tool call denied: {}", e);
                }
                
                Ok(MCPResponse {
                    result: None,
                    error: Some(MCPError {
                        code: -32002,
                        message: format!(
                            "Tool call denied: {}", 
                            authority::AuthorityModule::get_decision_description(&policy_response)
                        ),
                        data: Some(json!({
                            "authority_run_id": authority_run_id,
                            "tool_name": params.tool_name,
                            "reason": policy_response.reason
                        })),
                    }),
                    id: None,
                })
            },
            crate::models::PolicyDecision::NeedsApproval => {
                // Record needs approval decision
                if let Err(e) = audit_ledger::AuditLedgerModule::record_tool_call_needs_approval(
                    &params.agent_id,
                    &authority_run_id,
                    &params.tool_name,
                    policy_response.approver_role.as_deref(),
                    policy_response.reason.as_deref(),
                    state,
                ).await {
                    warn!("Failed to record tool call needs approval: {}", e);
                }
                
                Ok(MCPResponse {
                    result: None,
                    error: Some(MCPError {
                        code: -32003,
                        message: format!(
                            "Tool call requires approval: {}", 
                            authority::AuthorityModule::get_decision_description(&policy_response)
                        ),
                        data: Some(json!({
                            "authority_run_id": authority_run_id,
                            "tool_name": params.tool_name,
                            "approver_role": policy_response.approver_role,
                            "reason": policy_response.reason
                        })),
                    }),
                    id: None,
                })
            }
        }
    }
    
    /// Parse incoming MCP request
    pub fn parse_mcp_request(data: &[u8]) -> Result<MCPRequest, GatewayError> {
        let request_str = String::from_utf8(data.to_vec())
            .map_err(|e| GatewayError::InvalidRequest(format!("Invalid UTF-8: {}", e)))?;
            
        let request: MCPRequest = serde_json::from_str(&request_str)?;
        Ok(request)
    }
    
    /// Serialize MCP response
    pub fn serialize_mcp_response(response: MCPResponse) -> Result<Vec<u8>, GatewayError> {
        let response_json = serde_json::to_string(&response)?;
        Ok(response_json.into_bytes())
    }
    
    /// Handle MCP request routing
    pub async fn handle_mcp_request(
        request: MCPRequest,
        state: &AppState,
    ) -> Result<MCPResponse, GatewayError> {
        debug!("Handling MCP request: {}", request.method);
        
        match request.method.as_str() {
            "execute_action" => {
                let params: ExecuteActionParams = serde_json::from_value(request.params)
                    .map_err(|e| GatewayError::InvalidRequest(format!("Invalid params: {}", e)))?;
                    
                Self::handle_execute_action(params, state).await
            },
            "ping" => {
                // Simple ping for connectivity testing
                Ok(MCPResponse {
                    result: Some(json!({
                        "status": "pong",
                        "timestamp": chrono::Utc::now().to_rfc3339(),
                        "version": "0.1.0"
                    })),
                    error: None,
                    id: request.id,
                })
            },
            "list_tools" => {
                // List available MCP tools
                Ok(MCPResponse {
                    result: Some(json!({
                        "tools": [
                            {
                                "name": "execute_action",
                                "description": "Execute a governed action with identity verification and policy checking",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "agent_id": {"type": "string"},
                                        "certificate_id": {"type": "string"},
                                        "latest_genome_hash": {"type": "string"},
                                        "tool_name": {"type": "string"},
                                        "workspace_id": {"type": "string"},
                                        "action_context": {"type": "object"}
                                    },
                                    "required": ["agent_id", "certificate_id", "latest_genome_hash", "tool_name", "workspace_id"]
                                }
                            },
                            {
                                "name": "ping",
                                "description": "Test connectivity to the governance gateway",
                                "parameters": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            }
                        ]
                    })),
                    error: None,
                    id: request.id,
                })
            },
            _ => {
                Ok(MCPResponse {
                    result: None,
                    error: Some(MCPError {
                        code: -32601,
                        message: format!("Method not found: {}", request.method),
                        data: None,
                    }),
                    id: request.id,
                })
            }
        }
    }
    
    /// Validate MCP request format
    pub fn validate_request(request: &MCPRequest) -> Result<(), GatewayError> {
        if request.method.is_empty() {
            return Err(GatewayError::InvalidRequest("Method cannot be empty".to_string()));
        }
        
        // Additional validation can be added here
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{MCPRequest, PolicyDecision, PolicyCheckResponse};
    use serde_json::json;
    
    #[test]
    fn test_parse_mcp_request() {
        let request_json = json!({
            "method": "ping",
            "params": {},
            "id": 1
        });
        
        let request_data = request_json.to_string().into_bytes();
        let request = MCPInterfaceModule::parse_mcp_request(&request_data).unwrap();
        
        assert_eq!(request.method, "ping");
        assert_eq!(request.id, Some(json!(1)));
    }
    
    #[test]
    fn test_serialize_mcp_response() {
        let response = MCPResponse {
            result: Some(json!({"status": "pong"})),
            error: None,
            id: Some(json!(1)),
        };
        
        let response_data = MCPInterfaceModule::serialize_mcp_response(response).unwrap();
        let response_str = String::from_utf8(response_data).unwrap();
        
        assert!(response_str.contains("pong"));
    }
    
    #[test]
    fn test_validate_request() {
        let valid_request = MCPRequest {
            method: "ping".to_string(),
            params: json!({}),
            id: None,
        };
        
        assert!(MCPInterfaceModule::validate_request(&valid_request).is_ok());
        
        let invalid_request = MCPRequest {
            method: "".to_string(),
            params: json!({}),
            id: None,
        };
        
        assert!(MCPInterfaceModule::validate_request(&invalid_request).is_err());
    }
}
