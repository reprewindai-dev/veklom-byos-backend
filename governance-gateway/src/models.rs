use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityContext {
    pub agent_id: String,
    pub certificate_id: String,
    pub jurisdiction: String,
    pub risk_level: String,
    pub lineage_summary: String,
    pub latest_genome_hash: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyCheckRequest {
    pub identity_context: IdentityContext,
    pub authority_bundle_id: String,
    pub tool_name: String,
    pub workspace_id: String,
    pub action_context: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyCheckResponse {
    pub decision: PolicyDecision,
    pub reason: Option<String>,
    pub approver_role: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PolicyDecision {
    Allow,
    Deny,
    NeedsApproval,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEvent {
    pub event_type: String,
    pub agent_id: String,
    pub authority_run_id: String,
    pub tool_name: String,
    pub summary: String,
    pub details: serde_json::Value,
    pub created_at: DateTime<Utc>,
    pub event_hash: String,
    pub prev_event_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MCPRequest {
    pub method: String,
    pub params: serde_json::Value,
    pub id: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MCPResponse {
    pub result: Option<serde_json::Value>,
    pub error: Option<MCPError>,
    pub id: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MCPError {
    pub code: i32,
    pub message: String,
    pub data: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecuteActionParams {
    pub agent_id: String,
    pub certificate_id: String,
    pub latest_genome_hash: String,
    pub tool_name: String,
    pub workspace_id: String,
    pub action_context: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BirthCertificate {
    pub certificate_id: String,
    pub agent_id: String,
    pub status: String,
    pub latest_genome_hash: String,
    pub jurisdiction: String,
    pub created_at: DateTime<Utc>,
    pub lineage_root: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionAuthorizationToken {
    pub eat_id: String,
    pub agent_id: String,
    pub authority_run_id: String,
    pub tool_name: String,
    pub resource_scope: ResourceScope,
    pub workspace_id: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub nonce: String,
    pub constraints: TokenConstraints,
    pub signature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceScope {
    pub url: Option<String>,
    pub method: Option<String>,
    pub max_amount: f64,
    pub domain: Option<String>,
    pub route: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenConstraints {
    pub max_retries: u32,
    pub timeout_seconds: u64,
    pub requires_x402: bool,
    pub allowed_methods: Vec<String>,
    pub extra_rules: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionRequest {
    pub eat: ExecutionAuthorizationToken,
    pub payload: serde_json::Value,
    pub execution_context: ExecutionContext,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionContext {
    pub request_id: String,
    pub timestamp: DateTime<Utc>,
    pub client_info: ClientInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientInfo {
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
    pub source: String, // "internal_mcp" or "external_api"
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionReceipt {
    pub eat_id: String,
    pub authority_run_id: String,
    pub status: ExecutionStatus,
    pub response_summary: Option<String>,
    pub response_hash: Option<String>,
    pub execution_time_ms: u64,
    pub x402_payment_reference: Option<String>,
    pub error_details: Option<String>,
    pub completed_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionStatus {
    Success,
    Error,
    Timeout,
    Rejected,
}

// EAT canonical payload for signing (without signature)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EATPayload {
    pub eat_id: String,
    pub agent_id: String,
    pub authority_run_id: String,
    pub tool_name: String,
    pub resource_scope: ResourceScope,
    pub workspace_id: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub nonce: String,
    pub constraints: TokenConstraints,
}
