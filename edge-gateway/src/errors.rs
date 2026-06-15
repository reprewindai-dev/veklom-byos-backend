use thiserror::Error;

#[derive(Error, Debug)]
pub enum EdgeGatewayError {
    #[error("Invalid EAT: {0}")]
    InvalidEAT(String),
    
    #[error("EAT verification failed: {0}")]
    EATVerificationFailed(String),
    
    #[error("EAT expired")]
    EATExpired,
    
    #[error("EAT already used (replay protection)")]
    EATReused,
    
    #[error("Scope violation: {0}")]
    ScopeViolation(String),
    
    #[error("x402 payment required")]
    X402PaymentRequired,
    
    #[error("x402 payment verification failed: {0}")]
    X402VerificationFailed(String),
    
    #[error("Execution timeout")]
    ExecutionTimeout,
    
    #[error("Execution failed: {0}")]
    ExecutionFailed(String),
    
    #[error("Rate limit exceeded")]
    RateLimitExceeded,
    
    #[error("Invalid request: {0}")]
    InvalidRequest(String),
    
    #[error("Backend service error: {0}")]
    BackendError(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("HTTP client error: {0}")]
    HttpClientError(#[from] reqwest::Error),
    
    #[error("Configuration error: {0}")]
    ConfigError(String),
    
    #[error("Unauthorized access")]
    Unauthorized,
}

impl EdgeGatewayError {
    pub fn error_code(&self) -> u16 {
        match self {
            EdgeGatewayError::InvalidEAT(_) => 401,
            EdgeGatewayError::EATVerificationFailed(_) => 401,
            EdgeGatewayError::EATExpired => 401,
            EdgeGatewayError::EATReused => 401,
            EdgeGatewayError::ScopeViolation(_) => 403,
            EdgeGatewayError::X402PaymentRequired => 402,
            EdgeGatewayError::X402VerificationFailed(_) => 402,
            EdgeGatewayError::ExecutionTimeout => 408,
            EdgeGatewayError::ExecutionFailed(_) => 500,
            EdgeGatewayError::RateLimitExceeded => 429,
            EdgeGatewayError::InvalidRequest(_) => 400,
            EdgeGatewayError::BackendError(_) => 502,
            EdgeGatewayError::SerializationError(_) => 500,
            EdgeGatewayError::HttpClientError(_) => 502,
            EdgeGatewayError::ConfigError(_) => 500,
            EdgeGatewayError::Unauthorized => 401,
        }
    }
}
