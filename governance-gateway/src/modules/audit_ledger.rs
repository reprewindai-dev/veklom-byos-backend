use crate::{
    errors::GatewayError,
    models::AuditEvent,
    AppState,
};
use chrono::Utc;
use reqwest::Client;
use serde_json::{json, Value};
use sha2::{Sha256, Digest};
use tracing::{info, error, debug};
use uuid::Uuid;

pub struct AuditLedgerModule;

impl AuditLedgerModule {
    /// 0A.4 Audit ledger append (hash-chained events)
    /// Record hash-linked execution events and authorization receipts
    pub async fn record_event(
        event_type: &str,
        agent_id: &str,
        authority_run_id: &str,
        tool_name: &str,
        summary: &str,
        details: Value,
        state: &AppState,
    ) -> Result<AuditEvent, GatewayError> {
        info!(
            "Recording audit event: {} for agent: {}, tool: {}",
            event_type, agent_id, tool_name
        );
        
        // Fetch previous event hash for this agent or run from backend
        let prev_event_hash = Self::fetch_previous_event_hash(agent_id, authority_run_id, &state.http_client, &state.config.audit_url).await?;
        
        // Build event object
        let created_at = Utc::now();
        let event_data = json!({
            "event_type": event_type,
            "agent_id": agent_id,
            "authority_run_id": authority_run_id,
            "tool_name": tool_name,
            "summary": summary,
            "details": details,
            "created_at": created_at.to_rfc3339(),
            "prev_event_hash": prev_event_hash
        });
        
        // Compute event_hash = sha256(prev_event_hash + canonical_event_json)
        let event_hash = Self::calculate_event_hash(&prev_event_hash, &event_data.to_string());
        
        let audit_event = AuditEvent {
            event_type: event_type.to_string(),
            agent_id: agent_id.to_string(),
            authority_run_id: authority_run_id.to_string(),
            tool_name: tool_name.to_string(),
            summary: summary.to_string(),
            details,
            created_at,
            event_hash: event_hash.clone(),
            prev_event_hash: prev_event_hash.clone(),
        };
        
        // Call backend to persist event in the ledger/audit table
        Self::persist_event(&audit_event, &state.http_client, &state.config.audit_url).await?;
        
        debug!("Audit event recorded with hash: {}", event_hash);
        Ok(audit_event)
    }
    
    async fn fetch_previous_event_hash(
        agent_id: &str,
        authority_run_id: &str,
        client: &Client,
        audit_url: &str,
    ) -> Result<Option<String>, GatewayError> {
        let url = format!("{}/events/previous-hash", audit_url);
        
        debug!("Fetching previous event hash from: {}", url);
        
        let request_body = json!({
            "agent_id": agent_id,
            "authority_run_id": authority_run_id
        });
        
        let response = client
            .post(&url)
            .json(&request_body)
            .send()
            .await
            .map_err(|e| GatewayError::AuditLoggingFailed(format!("Failed to fetch previous hash: {}", e)))?;
            
        if !response.status().is_success() {
            // If no previous events exist, return None
            if response.status() == 404 {
                return Ok(None);
            }
            return Err(GatewayError::AuditLoggingFailed(
                format!("Previous hash fetch failed with status: {}", response.status())
            ));
        }
        
        let response_data: Value = response
            .json()
            .await
            .map_err(|e| GatewayError::AuditLoggingFailed(format!("Failed to parse previous hash response: {}", e)))?;
            
        let prev_hash = response_data["prev_event_hash"].as_str().map(|s| s.to_string());
        
        Ok(prev_hash)
    }
    
    fn calculate_event_hash(prev_hash: &Option<String>, event_json: &str) -> String {
        let mut hasher = Sha256::new();
        
        // Hash previous event hash (or empty string for first event)
        match prev_hash {
            Some(hash) => hasher.update(hash.as_bytes()),
            None => hasher.update(b""),
        }
        
        // Hash canonical event JSON
        hasher.update(event_json.as_bytes());
        
        let result = hasher.finalize();
        hex::encode(result)
    }
    
    async fn persist_event(
        event: &AuditEvent,
        client: &Client,
        audit_url: &str,
    ) -> Result<(), GatewayError> {
        let url = format!("{}/events", audit_url);
        
        debug!("Persisting audit event to: {}", url);
        
        let event_data = json!({
            "event_type": event.event_type,
            "agent_id": event.agent_id,
            "authority_run_id": event.authority_run_id,
            "tool_name": event.tool_name,
            "summary": event.summary,
            "details": event.details,
            "created_at": event.created_at.to_rfc3339(),
            "event_hash": event.event_hash,
            "prev_event_hash": event.prev_event_hash
        });
        
        let response = client
            .post(&url)
            .json(&event_data)
            .send()
            .await
            .map_err(|e| GatewayError::AuditLoggingFailed(format!("Failed to persist event: {}", e)))?;
            
        if !response.status().is_success() {
            return Err(GatewayError::AuditLoggingFailed(
                format!("Event persistence failed with status: {}", response.status())
            ));
        }
        
        Ok(())
    }
    
    /// Event types for Phase 0A
    pub const TOOL_CALL_ATTEMPT: &str = "tool_call_attempt";
    pub const TOOL_CALL_ALLOWED: &str = "tool_call_allowed";
    pub const TOOL_CALL_DENIED: &str = "tool_call_denied";
    pub const TOOL_CALL_NEEDS_APPROVAL: &str = "tool_call_needs_approval";
    pub const SESSION_VERIFIED: &str = "session_verified";
    pub const SESSION_REJECTED: &str = "session_rejected";
    
    /// Helper method to record tool call attempt before policy check
    pub async fn record_tool_call_attempt(
        agent_id: &str,
        authority_run_id: &str,
        tool_name: &str,
        action_context: &Value,
        state: &AppState,
    ) -> Result<AuditEvent, GatewayError> {
        Self::record_event(
            Self::TOOL_CALL_ATTEMPT,
            agent_id,
            authority_run_id,
            tool_name,
            &format!("Agent attempted to call tool: {}", tool_name),
            json!({
                "action_context": action_context,
                "timestamp": Utc::now().to_rfc3339()
            }),
            state,
        ).await
    }
    
    /// Helper method to record tool call allowed after policy check
    pub async fn record_tool_call_allowed(
        agent_id: &str,
        authority_run_id: &str,
        tool_name: &str,
        reason: Option<&str>,
        state: &AppState,
    ) -> Result<AuditEvent, GatewayError> {
        Self::record_event(
            Self::TOOL_CALL_ALLOWED,
            agent_id,
            authority_run_id,
            tool_name,
            &format!("Tool call allowed: {}", tool_name),
            json!({
                "reason": reason,
                "timestamp": Utc::now().to_rfc3339()
            }),
            state,
        ).await
    }
    
    /// Helper method to record tool call denied after policy check
    pub async fn record_tool_call_denied(
        agent_id: &str,
        authority_run_id: &str,
        tool_name: &str,
        reason: &str,
        state: &AppState,
    ) -> Result<AuditEvent, GatewayError> {
        Self::record_event(
            Self::TOOL_CALL_DENIED,
            agent_id,
            authority_run_id,
            tool_name,
            &format!("Tool call denied: {}", tool_name),
            json!({
                "reason": reason,
                "timestamp": Utc::now().to_rfc3339()
            }),
            state,
        ).await
    }
    
    /// Helper method to record tool call needs approval after policy check
    pub async fn record_tool_call_needs_approval(
        agent_id: &str,
        authority_run_id: &str,
        tool_name: &str,
        approver_role: Option<&str>,
        reason: Option<&str>,
        state: &AppState,
    ) -> Result<AuditEvent, GatewayError> {
        Self::record_event(
            Self::TOOL_CALL_NEEDS_APPROVAL,
            agent_id,
            authority_run_id,
            tool_name,
            &format!("Tool call needs approval: {}", tool_name),
            json!({
                "approver_role": approver_role,
                "reason": reason,
                "timestamp": Utc::now().to_rfc3339()
            }),
            state,
        ).await
    }
    
    /// Helper method to record successful session verification
    pub async fn record_session_verified(
        agent_id: &str,
        authority_run_id: &str,
        certificate_id: &str,
        state: &AppState,
    ) -> Result<AuditEvent, GatewayError> {
        Self::record_event(
            Self::SESSION_VERIFIED,
            agent_id,
            authority_run_id,
            "identity_verification",
            "Session identity verified successfully",
            json!({
                "certificate_id": certificate_id,
                "timestamp": Utc::now().to_rfc3339()
            }),
            state,
        ).await
    }
    
    /// Helper method to record failed session verification
    pub async fn record_session_rejected(
        agent_id: &str,
        authority_run_id: &str,
        certificate_id: &str,
        reason: &str,
        state: &AppState,
    ) -> Result<AuditEvent, GatewayError> {
        Self::record_event(
            Self::SESSION_REJECTED,
            agent_id,
            authority_run_id,
            "identity_verification",
            "Session identity verification failed",
            json!({
                "certificate_id": certificate_id,
                "reason": reason,
                "timestamp": Utc::now().to_rfc3339()
            }),
            state,
        ).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    
    #[test]
    fn test_calculate_event_hash() {
        // Test hash calculation with no previous hash
        let hash1 = AuditLedgerModule::calculate_event_hash(&None, "test_event");
        assert!(!hash1.is_empty());
        assert_eq!(hash1.len(), 64); // SHA256 hex length
        
        // Test hash calculation with previous hash
        let hash2 = AuditLedgerModule::calculate_event_hash(&Some(hash1.clone()), "test_event");
        assert_ne!(hash1, hash2);
        
        // Same input should produce same hash
        let hash3 = AuditLedgerModule::calculate_event_hash(&Some(hash1.clone()), "test_event");
        assert_eq!(hash2, hash3);
    }
    
    #[test]
    fn test_event_constants() {
        assert_eq!(AuditLedgerModule::TOOL_CALL_ATTEMPT, "tool_call_attempt");
        assert_eq!(AuditLedgerModule::TOOL_CALL_ALLOWED, "tool_call_allowed");
        assert_eq!(AuditLedgerModule::TOOL_CALL_DENIED, "tool_call_denied");
        assert_eq!(AuditLedgerModule::TOOL_CALL_NEEDS_APPROVAL, "tool_call_needs_approval");
        assert_eq!(AuditLedgerModule::SESSION_VERIFIED, "session_verified");
        assert_eq!(AuditLedgerModule::SESSION_REJECTED, "session_rejected");
    }
}
