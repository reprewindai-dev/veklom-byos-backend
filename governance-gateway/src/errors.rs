use thiserror::Error;

#[derive(Error, Debug)]
pub enum GatewayError {
    #[error("Identity verification failed: {0}")]
    IdentityVerificationFailed(String),
    
    #[error("Policy check failed: {0}")]
    PolicyCheckFailed(String),
    
    #[error("Audit logging failed: {0}")]
    AuditLoggingFailed(String),
    
    #[error("Backend service error: {0}")]
    BackendError(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("HTTP client error: {0}")]
    HttpClientError(#[from] reqwest::Error),
    
    #[error("Invalid request: {0}")]
    InvalidRequest(String),
    
    #[error("Configuration error: {0}")]
    ConfigError(String),
}
