use crate::{
    errors::EdgeGatewayError,
    models::{X402Challenge, X402PaymentProof, FacilitatorVerification, PaidEndpoint},
    AppState,
};
use chrono::{Duration, Utc};
use serde_json::json;
use tracing::{info, debug, warn, error};
use uuid::Uuid;

pub struct X402MerchantModule;

impl X402MerchantModule {
    /// Generate x402 payment challenge for a paid endpoint
    pub async fn create_challenge(
        endpoint: &PaidEndpoint,
        workspace_id: Option<&str>,
        state: &AppState,
    ) -> Result<X402Challenge, EdgeGatewayError> {
        info!("Creating x402 challenge for endpoint: {}", endpoint.path);
        
        let challenge_id = format!("challenge_{}", Uuid::new_v4().to_string().replace("-", "")[..16].to_string());
        let payment_reference = format!("pay_{}", Uuid::new_v4().to_string().replace("-", "")[..16].to_string());
        
        // Generate payment address (in real implementation, this would be a unique address per challenge)
        let payment_address = format!("0x{}", Self::generate_payment_address());
        
        let challenge = X402Challenge {
            challenge_id,
            payment_address,
            amount_required: endpoint.required_payment.to_string(),
            currency: endpoint.currency.clone(),
            network: "base".to_string(),
            expires_at: Utc::now() + Duration::minutes(15), // 15 minute expiry
            payment_reference,
            facilitator_data: json!({
                "facilitator_url": state.config.x402_config.facilitator_url,
                "endpoint": endpoint.path,
                "workspace_id": workspace_id,
                "max_amount": endpoint.required_payment
            }),
        };
        
        debug!("x402 challenge created: {}", challenge.challenge_id);
        Ok(challenge)
    }
    
    /// Verify x402 payment proof using facilitator
    pub async fn verify_payment(
        payment_proof: &X402PaymentProof,
        expected_amount: f64,
        expected_currency: &str,
        state: &AppState,
    ) -> Result<FacilitatorVerification, EdgeGatewayError> {
        info!("Verifying x402 payment: {}", payment_proof.payment_reference);
        
        // Step 1: Basic validation
        Self::validate_payment_proof(payment_proof, expected_amount, expected_currency)?;
        
        // Step 2: Verify with facilitator
        let facilitator_verification = Self::verify_with_facilitator(payment_proof, &state.config).await?;
        
        // Step 3: Check verification result
        if !facilitator_verification.verified {
            return Err(EdgeGatewayError::X402VerificationFailed(
                "Facilitator verification failed".to_string()
            ));
        }
        
        info!("x402 payment verified successfully: {}", payment_proof.payment_reference);
        Ok(facilitator_verification)
    }
    
    /// Validate basic payment proof requirements
    fn validate_payment_proof(
        payment_proof: &X402PaymentProof,
        expected_amount: f64,
        expected_currency: &str,
    ) -> Result<(), EdgeGatewayError> {
        // Check amount
        let paid_amount = payment_proof.amount.parse::<f64>()
            .map_err(|_| EdgeGatewayError::X402VerificationFailed(
                "Invalid amount format".to_string()
            ))?;
        
        if paid_amount < expected_amount {
            return Err(EdgeGatewayError::X402VerificationFailed(
                format!("Insufficient payment: paid {}, required {}", paid_amount, expected_amount)
            ));
        }
        
        // Check currency
        if payment_proof.currency != expected_currency {
            return Err(EdgeGatewayError::X402VerificationFailed(
                format!("Currency mismatch: expected {}, got {}", expected_currency, payment_proof.currency)
            ));
        }
        
        // Check timestamp (should be recent)
        let now = Utc::now();
        let payment_age = now.signed_duration_since(payment_proof.timestamp);
        
        if payment_age.num_minutes() > 30 {
            return Err(EdgeGatewayError::X402VerificationFailed(
                "Payment too old".to_string()
            ));
        }
        
        Ok(())
    }
    
    /// Verify payment with x402 facilitator
    async fn verify_with_facilitator(
        payment_proof: &X402PaymentProof,
        config: &crate::config::Config,
    ) -> Result<FacilitatorVerification, EdgeGatewayError> {
        let facilitator_url = format!("{}/verify", config.x402_config.facilitator_url);
        
        debug!("Calling facilitator at: {}", facilitator_url);
        
        let request_body = json!({
            "transaction_hash": payment_proof.transaction_hash,
            "payment_reference": payment_proof.payment_reference,
            "amount": payment_proof.amount,
            "currency": payment_proof.currency,
            "payer_address": payment_proof.payer_address,
            "signature": payment_proof.signature
        });
        
        let response = state.http_client
            .post(&facilitator_url)
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", Self::get_facilitator_api_key(config)))
            .json(&request_body)
            .send()
            .await
            .map_err(|e| EdgeGatewayError::X402VerificationFailed(
                format!("Failed to call facilitator: {}", e)
            ))?;
            
        if !response.status().is_success() {
            return Err(EdgeGatewayError::X402VerificationFailed(
                format!("Facilitator returned status: {}", response.status())
            ));
        }
        
        let facilitator_response: serde_json::Value = response
            .json()
            .await
            .map_err(|e| EdgeGatewayError::X402VerificationFailed(
                format!("Failed to parse facilitator response: {}", e)
            ))?;
        
        let verified = facilitator_response["verified"]
            .as_bool()
            .unwrap_or(false);
        
        Ok(FacilitatorVerification {
            verified,
            verification_timestamp: Utc::now(),
            facilitator_response: facilitator_response,
        })
    }
    
    /// Check if a request requires x402 payment
    pub async fn requires_payment(
        path: &str,
        method: &str,
        state: &AppState,
    ) -> Option<PaidEndpoint> {
        // Define the single paid endpoint for Phase 0B
        let paid_endpoint = PaidEndpoint::default();
        
        if path == paid_endpoint.path && method == paid_endpoint.method {
            Some(paid_endpoint)
        } else {
            None
        }
    }
    
    /// Generate a payment address (simplified implementation)
    fn generate_payment_address() -> String {
        // In a real implementation, this would generate a unique address
        // For now, return a deterministic address based on timestamp
        use sha2::{Sha256, Digest};
        
        let mut hasher = Sha256::new();
        hasher.update(Utc::now().timestamp().to_string().as_bytes());
        let result = hasher.finalize();
        
        format!("{:040x}", result)[0..40].to_string()
    }
    
    /// Get facilitator API key from configuration
    fn get_facilitator_api_key(config: &crate::config::Config) -> String {
        // In a real implementation, this would come from environment variables or secure storage
        std::env::var("X402_FACILITATOR_API_KEY").unwrap_or_else(|_| "test_api_key".to_string())
    }
    
    /// Check if a payment reference has been used (replay protection)
    pub async fn is_payment_reference_used(
        payment_reference: &str,
        state: &AppState,
    ) -> Result<bool, EdgeGatewayError> {
        // In a real implementation, this would check against a database or cache
        // For now, we'll use a simple in-memory check
        let used_references = state.used_nonces.read().await;
        Ok(used_references.contains(payment_reference))
    }
    
    /// Mark payment reference as used
    pub async fn mark_payment_reference_used(
        payment_reference: &str,
        state: &AppState,
    ) -> Result<(), EdgeGatewayError> {
        let mut used_references = state.used_nonces.write().await;
        used_references.insert(payment_reference.to_string());
        Ok(())
    }
    
    /// Get supported payment methods
    pub fn get_supported_payment_methods() -> Vec<String> {
        vec![
            "USDC".to_string(),
            "USDT".to_string(),
            "ETH".to_string(),
        ]
    }
    
    /// Validate payment amount against limits
    pub fn validate_payment_amount(
        amount: f64,
        max_amount: f64,
    ) -> Result<(), EdgeGatewayError> {
        if amount <= 0.0 {
            return Err(EdgeGatewayError::X402VerificationFailed(
                "Payment amount must be positive".to_string()
            ));
        }
        
        if amount > max_amount {
            return Err(EdgeGatewayError::X402VerificationFailed(
                format!("Payment amount exceeds maximum: {} > {}", amount, max_amount)
            ));
        }
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    
    #[test]
    fn test_validate_payment_amount_valid() {
        assert!(X402MerchantModule::validate_payment_amount(5.0, 10.0).is_ok());
        assert!(X402MerchantModule::validate_payment_amount(10.0, 10.0).is_ok());
    }
    
    #[test]
    fn test_validate_payment_amount_invalid() {
        assert!(X402MerchantModule::validate_payment_amount(0.0, 10.0).is_err());
        assert!(X402MerchantModule::validate_payment_amount(-5.0, 10.0).is_err());
        assert!(X402MerchantModule::validate_payment_amount(15.0, 10.0).is_err());
    }
    
    #[test]
    fn test_requires_payment() {
        let paid_endpoint = PaidEndpoint::default();
        
        // Test matching path and method
        assert!(X402MerchantModule::requires_payment(
            &paid_endpoint.path, 
            &paid_endpoint.method, 
            &crate::AppState::new(crate::config::Config::from_env().unwrap()).await.unwrap()
        ).await.is_some());
        
        // Test non-matching path
        assert!(X402MerchantModule::requires_payment(
            "/different/path", 
            &paid_endpoint.method, 
            &crate::AppState::new(crate::config::Config::from_env().unwrap()).await.unwrap()
        ).await.is_none());
        
        // Test non-matching method
        assert!(X402MerchantModule::requires_payment(
            &paid_endpoint.path, 
            "GET", 
            &crate::AppState::new(crate::config::Config::from_env().unwrap()).await.unwrap()
        ).await.is_none());
    }
    
    #[test]
    fn test_get_supported_payment_methods() {
        let methods = X402MerchantModule::get_supported_payment_methods();
        assert!(methods.contains(&"USDC".to_string()));
        assert!(methods.contains(&"USDT".to_string()));
        assert!(methods.contains(&"ETH".to_string()));
    }
    
    #[test]
    fn test_generate_payment_address() {
        let address1 = X402MerchantModule::generate_payment_address();
        let address2 = X402MerchantModule::generate_payment_address();
        
        assert_eq!(address1.len(), 40);
        assert_eq!(address2.len(), 40);
        assert!(address1.starts_with("0x"));
        assert!(address2.starts_with("0x"));
        // Should be different due to timestamp
        assert_ne!(address1, address2);
    }
}
