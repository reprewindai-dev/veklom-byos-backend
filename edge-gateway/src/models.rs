use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;

// Re-use models from governance-gateway
pub use governance_gateway::models::{
    ExecutionAuthorizationToken, ExecutionRequest, ExecutionReceipt, 
    ExecutionContext, ClientInfo, ExecutionStatus
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct X402Challenge {
    pub challenge_id: String,
    pub payment_address: String,
    pub amount_required: String,
    pub currency: String,
    pub network: String,
    pub expires_at: DateTime<Utc>,
    pub payment_reference: String,
    pub facilitator_data: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct X402PaymentProof {
    pub payment_reference: String,
    pub transaction_hash: String,
    pub amount: String,
    pub currency: String,
    pub payer_address: String,
    pub timestamp: DateTime<Utc>,
    pub signature: String,
    pub facilitator_verification: Option<FacilitatorVerification>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FacilitatorVerification {
    pub verified: bool,
    pub verification_timestamp: DateTime<Utc>,
    pub facilitator_response: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionRequestPayload {
    pub eat: ExecutionAuthorizationToken,
    pub target_url: String,
    pub method: String,
    pub headers: std::collections::HashMap<String, String>,
    pub body: Option<String>,
    pub timeout_seconds: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub eat_id: String,
    pub authority_run_id: String,
    pub status: ExecutionStatus,
    pub response_code: Option<u16>,
    pub response_body: Option<String>,
    pub response_headers: Option<std::collections::HashMap<String, String>>,
    pub execution_time_ms: u64,
    pub error_message: Option<String>,
    pub x402_payment_reference: Option<String>,
    pub completed_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeErrorResponse {
    pub error: String,
    pub code: u16,
    pub details: Option<serde_json::Value>,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    pub service: String,
    pub version: String,
    pub phase: String,
    pub timestamp: DateTime<Utc>,
    pub components: ComponentStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComponentStatus {
    pub eat_verification: String,
    pub x402_merchant: String,
    pub execution_engine: String,
    pub rate_limiter: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitInfo {
    pub requests_per_minute: u32,
    pub current_requests: u32,
    pub reset_at: DateTime<Utc>,
}

// Paid endpoint configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaidEndpoint {
    pub path: String,
    pub method: String,
    pub required_payment: f64,
    pub currency: String,
    pub description: String,
    pub workspace_required: bool,
}

impl Default for PaidEndpoint {
    fn default() -> Self {
        Self {
            path: "/api/v1/premium/analysis".to_string(),
            method: "POST".to_string(),
            required_payment: 5.0,
            currency: "USDC".to_string(),
            description: "Premium AI analysis endpoint".to_string(),
            workspace_required: true,
        }
    }
}
