//! MCP Tool Router — receives tools/call from Covenant MCPBridge
//!
//! Flow:
//!   Covenant MCPBridge
//!     → POST /mcp  { jsonrpc:"2.0", method:"tools/call", params:{ name, arguments } }
//!     → validate Covenant headers
//!     → resolve tool name to registered MCP server
//!     → verify agent identity + mint EAT
//!     → forward call to target MCP server with EAT as bearer
//!     → return { jsonrpc:"2.0", result:{ content:[...] } }
//!
//! The _covenant block injected by MCPBridge carries:
//!   connection_id, agent_id, trace_id, timestamp
//! These are stripped before forwarding to the downstream tool.

use crate::{
    errors::GatewayError,
    models::{
        MCPResponse, MCPError,
    },
    modules::{identity, authority, audit_ledger, eat_minting},
    AppState,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tracing::{info, error, warn, debug};
use std::time::Instant;

// ---------------------------------------------------------------------------
// Wire types
// ---------------------------------------------------------------------------

/// The _covenant metadata injected by MCPBridge into every tools/call
#[derive(Debug, Deserialize)]
pub struct CovenantMeta {
    pub connection_id: String,
    pub agent_id:      String,
    pub trace_id:      Option<String>,
    pub timestamp:     String,
}

/// Inbound tools/call params (JSON-RPC 2.0)
#[derive(Debug, Deserialize)]
pub struct ToolsCallParams {
    pub name:      String,
    pub arguments: Value,
}

/// A single MCP content item in the result
#[derive(Debug, Serialize, Deserialize)]
pub struct ContentItem {
    #[serde(rename = "type")]
    pub content_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text:         Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data:         Option<Value>,
}

/// Registered MCP server entry (stored in AppState.mcp_registry)
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct McpServerEntry {
    /// Prefix that matches the tool name, e.g. "github" matches "github.create_issue"
    pub prefix:   String,
    /// Full base URL of the downstream MCP server
    pub base_url: String,
    /// Optional fixed bearer token for the downstream server
    pub bearer:   Option<String>,
    /// Category label for audit
    pub category: String,
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

pub struct MCPToolRouter;

impl MCPToolRouter {
    /// Entry point — called from mcp_handler when method == "tools/call"
    pub async fn handle(
        params_value: Value,
        call_id:      Option<Value>,
        covenant_id:  &str,
        agent_id_hdr: &str,
        trace_id_hdr: &str,
        state:        &AppState,
    ) -> Result<MCPResponse, GatewayError> {
        let t0 = Instant::now();

        // 1. Parse params
        let params: ToolsCallParams = serde_json::from_value(params_value)
            .map_err(|e| GatewayError::InvalidRequest(format!("tools/call params invalid: {}", e)))?;

        // 2. Extract and strip _covenant from arguments
        let (covenant_meta, clean_args) = Self::extract_covenant_meta(&params.arguments);

        // Prefer header values; fall back to _covenant block in body
        let agent_id = if !agent_id_hdr.is_empty() {
            agent_id_hdr.to_string()
        } else {
            covenant_meta.as_ref().map(|m| m.agent_id.clone()).unwrap_or_default()
        };
        let connection_id = if !covenant_id.is_empty() {
            covenant_id.to_string()
        } else {
            covenant_meta.as_ref().map(|m| m.connection_id.clone()).unwrap_or_default()
        };
        let trace_id = if !trace_id_hdr.is_empty() {
            trace_id_hdr.to_string()
        } else {
            covenant_meta.as_ref().and_then(|m| m.trace_id.clone()).unwrap_or_default()
        };

        if agent_id.is_empty() || connection_id.is_empty() {
            return Ok(Self::err(-32600, "Missing agent_id or connection_id", call_id));
        }

        info!(
            "tools/call  tool={} agent={} conn={} trace={}",
            params.name, agent_id, connection_id, trace_id
        );

        // 3. Generate authority run id
        let authority_run_id = identity::IdentityModule::generate_authority_run_id();

        // 4. Verify agent identity
        //    Covenant already verified Ed25519 before calling here;
        //    connection_id is used as the cert surrogate.
        let identity_context = match identity::IdentityModule::verify_session(
            &agent_id,
            &connection_id,
            "",
            state,
        ).await {
            Ok(ctx) => ctx,
            Err(e) => {
                warn!("Identity check failed agent={}: {}", agent_id, e);
                let _ = audit_ledger::AuditLedgerModule::record_session_rejected(
                    &agent_id, &authority_run_id, &connection_id, &e.to_string(), state,
                ).await;
                return Ok(Self::err(-32001, &format!("Identity rejected: {}", e), call_id));
            }
        };

        // 5. Policy gate
        let authority_bundle_id = authority::AuthorityModule::get_authority_bundle_id(&identity_context);
        let action_ctx = Some(json!({
            "tool": params.name,
            "connection_id": connection_id,
            "trace_id": trace_id,
        }));

        let policy_response = authority::AuthorityModule::check_action(
            &identity_context,
            &authority_bundle_id,
            &params.name,
            "",
            action_ctx.clone(),
            state,
        ).await?;

        match policy_response.decision {
            crate::models::PolicyDecision::Deny => {
                let _ = audit_ledger::AuditLedgerModule::record_tool_call_denied(
                    &agent_id, &authority_run_id, &params.name,
                    policy_response.reason.as_deref().unwrap_or("denied"),
                    state,
                ).await;
                return Ok(Self::err(
                    -32002,
                    &format!("Policy denied: {}", policy_response.reason.unwrap_or_default()),
                    call_id,
                ));
            }
            crate::models::PolicyDecision::NeedsApproval => {
                let _ = audit_ledger::AuditLedgerModule::record_tool_call_needs_approval(
                    &agent_id, &authority_run_id, &params.name,
                    policy_response.approver_role.as_deref(),
                    policy_response.reason.as_deref(),
                    state,
                ).await;
                return Ok(Self::err(
                    -32003,
                    &format!("Needs approval: {}", policy_response.reason.unwrap_or_default()),
                    call_id,
                ));
            }
            crate::models::PolicyDecision::Allow => {}
        }

        // 6. Mint EAT
        let eat = match eat_minting::EATMintingModule::mint_eat(
            &identity_context,
            &authority_run_id,
            &params.name,
            "",
            &policy_response,
            &action_ctx.unwrap_or(Value::Null),
            state,
        ).await {
            Ok(t) => t,
            Err(e) => {
                error!("EAT mint failed: {}", e);
                return Ok(Self::err(-32004, &format!("EAT mint failed: {}", e), call_id));
            }
        };

        // 7. Resolve tool to downstream MCP server
        let server = Self::resolve_tool(&params.name, state);

        // 8. Forward to downstream or return EAT for direct execution
        let (result_content, is_error) = match server {
            Some(entry) => {
                Self::forward_to_mcp_server(&entry, &params.name, &clean_args, &eat.signature, &trace_id).await
            }
            None => {
                debug!("No downstream server for tool={}, returning EAT", params.name);
                (
                    vec![ContentItem {
                        content_type: "text".into(),
                        text: Some(serde_json::to_string(&json!({
                            "ok": true,
                            "eat_issued": true,
                            "tool": params.name,
                            "eat_id": eat.eat_id,
                            "authority_run_id": authority_run_id,
                            "note": "No downstream MCP server registered. EAT issued for direct execution."
                        })).unwrap_or_default()),
                        data: None,
                    }],
                    false,
                )
            }
        };

        // 9. Audit outcome
        let _ = audit_ledger::AuditLedgerModule::record_tool_call_allowed(
            &agent_id, &authority_run_id, &params.name,
            Some(&format!("tools/call ok in {}ms", t0.elapsed().as_millis())),
            state,
        ).await;

        Ok(MCPResponse {
            result: Some(json!({
                "content": result_content,
                "isError": is_error,
                "_meta": {
                    "authority_run_id": authority_run_id,
                    "connection_id": connection_id,
                    "trace_id": trace_id,
                    "execution_ms": t0.elapsed().as_millis(),
                }
            })),
            error: None,
            id: call_id,
        })
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    fn extract_covenant_meta(args: &Value) -> (Option<CovenantMeta>, Value) {
        let mut clean = args.clone();
        let meta = clean
            .as_object_mut()
            .and_then(|m| m.remove("_covenant"))
            .and_then(|v| serde_json::from_value::<CovenantMeta>(v).ok());
        (meta, clean)
    }

    fn resolve_tool(tool_name: &str, state: &AppState) -> Option<McpServerEntry> {
        state.mcp_registry.iter().find(|entry| {
            tool_name == entry.prefix
                || tool_name.starts_with(&format!("{}.", entry.prefix))
        }).cloned()
    }

    async fn forward_to_mcp_server(
        server:    &McpServerEntry,
        tool_name: &str,
        arguments: &Value,
        eat_sig:   &str,
        trace_id:  &str,
    ) -> (Vec<ContentItem>, bool) {
        use std::time::Duration;

        let payload = json!({
            "jsonrpc": "2.0",
            "id": uuid::Uuid::new_v4().to_string(),
            "method": "tools/call",
            "params": { "name": tool_name, "arguments": arguments }
        });

        let client = match reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .build() {
            Ok(c) => c,
            Err(e) => return (vec![ContentItem {
                content_type: "text".into(),
                text: Some(format!("HTTP client build error: {}", e)),
                data: None,
            }], true),
        };

        let mut req = client
            .post(&server.base_url)
            .header("Content-Type", "application/json")
            .header("X-EAT", eat_sig)
            .header("X-Trace-Id", trace_id)
            .json(&payload);

        if let Some(bearer) = &server.bearer {
            req = req.header("Authorization", format!("Bearer {}", bearer));
        }

        match req.send().await {
            Ok(resp) => {
                let is_error = !resp.status().is_success();
                match resp.json::<Value>().await {
                    Ok(body) => {
                        if let Some(content) = body.pointer("/result/content") {
                            if let Ok(items) = serde_json::from_value::<Vec<ContentItem>>(content.clone()) {
                                return (items, is_error);
                            }
                        }
                        (vec![ContentItem {
                            content_type: "text".into(),
                            text: Some(body.to_string()),
                            data: None,
                        }], is_error)
                    }
                    Err(e) => (vec![ContentItem {
                        content_type: "text".into(),
                        text: Some(format!("Downstream parse error: {}", e)),
                        data: None,
                    }], true),
                }
            }
            Err(e) => (vec![ContentItem {
                content_type: "text".into(),
                text: Some(format!("Downstream unreachable: {}", e)),
                data: None,
            }], true),
        }
    }

    fn err(code: i32, message: &str, id: Option<Value>) -> MCPResponse {
        MCPResponse {
            result: None,
            error: Some(MCPError { code, message: message.to_string(), data: None }),
            id,
        }
    }
}
