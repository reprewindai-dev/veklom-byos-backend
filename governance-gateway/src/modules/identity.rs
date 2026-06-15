use crate::{
    errors::GatewayError,
    models::{IdentityContext, BirthCertificate},
    AppState,
};
use reqwest::Client;
use serde_json::Value;
use tracing::{info, error, debug};
use uuid::Uuid;

pub struct IdentityModule;

impl IdentityModule {
    /// 0A.2 Identity intake & session attestation
    /// Verify certificate_id and genome_hash against active birth state
    pub async fn verify_session(
        agent_id: &str,
        certificate_id: &str,
        latest_genome_hash: &str,
        state: &AppState,
    ) -> Result<IdentityContext, GatewayError> {
        info!("Verifying identity for agent: {}, certificate: {}", agent_id, certificate_id);
        
        // Call existing backend/PGL to fetch canonical birth certificate + status
        let birth_cert = Self::fetch_birth_certificate(certificate_id, &state.http_client, &state.config.pgl_url).await?;
        
        // Validate status == "active"
        if birth_cert.status != "active" {
            return Err(GatewayError::IdentityVerificationFailed(
                format!("Certificate {} is not active: {}", certificate_id, birth_cert.status)
            ));
        }
        
        // Validate latest_genome_hash matches stored latest_genome_hash
        if birth_cert.latest_genome_hash != latest_genome_hash {
            return Err(GatewayError::IdentityVerificationFailed(
                format!(
                    "Genome hash mismatch for certificate {}. Expected: {}, Provided: {}",
                    certificate_id, birth_cert.latest_genome_hash, latest_genome_hash
                )
            ));
        }
        
        // Validate agent_id matches
        if birth_cert.agent_id != agent_id {
            return Err(GatewayError::IdentityVerificationFailed(
                format!(
                    "Agent ID mismatch for certificate {}. Expected: {}, Provided: {}",
                    certificate_id, birth_cert.agent_id, agent_id
                )
            ));
        }
        
        // Build IdentityContext
        let identity_context = IdentityContext {
            agent_id: agent_id.to_string(),
            certificate_id: certificate_id.to_string(),
            jurisdiction: birth_cert.jurisdiction,
            risk_level: Self::calculate_risk_level(&birth_cert),
            lineage_summary: birth_cert.lineage_root,
            latest_genome_hash: latest_genome_hash.to_string(),
            status: birth_cert.status,
        };
        
        debug!("Identity verification successful for agent: {}", agent_id);
        Ok(identity_context)
    }
    
    async fn fetch_birth_certificate(
        certificate_id: &str,
        client: &Client,
        pgl_url: &str,
    ) -> Result<BirthCertificate, GatewayError> {
        let url = format!("{}/adapter/agents/certificate/{}", pgl_url, certificate_id);
        
        debug!("Fetching birth certificate from: {}", url);
        
        let response = client
            .get(&url)
            .send()
            .await
            .map_err(|e| GatewayError::BackendError(format!("Failed to fetch birth certificate: {}", e)))?;
            
        if !response.status().is_success() {
            return Err(GatewayError::BackendError(
                format!("Birth certificate fetch failed with status: {}", response.status())
            ));
        }
        
        let cert_data: Value = response
            .json()
            .await
            .map_err(|e| GatewayError::BackendError(format!("Failed to parse birth certificate response: {}", e)))?;
            
        // Extract birth certificate data from response
        let birth_cert = BirthCertificate {
            certificate_id: cert_data["certificate_id"]
                .as_str()
                .unwrap_or(certificate_id)
                .to_string(),
            agent_id: cert_data["agent_id"]
                .as_str()
                .ok_or_else(|| GatewayError::BackendError("Missing agent_id in birth certificate".to_string()))?
                .to_string(),
            status: cert_data["status"]
                .as_str()
                .unwrap_or("unknown")
                .to_string(),
            latest_genome_hash: cert_data["latest_genome_hash"]
                .as_str()
                .ok_or_else(|| GatewayError::BackendError("Missing latest_genome_hash in birth certificate".to_string()))?
                .to_string(),
            jurisdiction: cert_data["jurisdiction"]
                .as_str()
                .unwrap_or("US")
                .to_string(),
            created_at: chrono::Utc::now(), // Will be parsed from response in real implementation
            lineage_root: cert_data["lineage_root"]
                .as_str()
                .unwrap_or("")
                .to_string(),
        };
        
        Ok(birth_cert)
    }
    
    fn calculate_risk_level(birth_cert: &BirthCertificate) -> String {
        // Simple risk calculation based on jurisdiction and other factors
        // In real implementation, this would be more sophisticated
        match birth_cert.jurisdiction.as_str() {
            "US" => "medium".to_string(),
            "EU" => "low".to_string(),
            _ => "high".to_string(),
        }
    }
    
    /// Generate a new authority run ID for tracking
    pub fn generate_authority_run_id() -> String {
        format!("run_{}", Uuid::new_v4().to_string().replace("-", "")[..8].to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_generate_authority_run_id() {
        let run_id = IdentityModule::generate_authority_run_id();
        assert!(run_id.starts_with("run_"));
        assert_eq!(run_id.len(), 12); // "run_" + 8 chars
    }
    
    #[test]
    fn test_calculate_risk_level() {
        let cert_us = BirthCertificate {
            certificate_id: "test".to_string(),
            agent_id: "agent".to_string(),
            status: "active".to_string(),
            latest_genome_hash: "hash".to_string(),
            jurisdiction: "US".to_string(),
            created_at: chrono::Utc::now(),
            lineage_root: "lineage".to_string(),
        };
        
        assert_eq!(IdentityModule::calculate_risk_level(&cert_us), "medium");
    }
}
