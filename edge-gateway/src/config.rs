use serde::{Deserialize, Serialize};
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub backend_url: String,
    pub gateway_port: u16,
    pub log_level: String,
    pub x402_config: X402Config,
    pub execution_config: ExecutionConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct X402Config {
    pub facilitator_url: String,
    pub base_network_url: String,
    pub payment_token_address: String,
    pub supported_tokens: Vec<String>,
    pub max_payment_amount: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionConfig {
    pub max_execution_time_seconds: u64,
    pub max_response_size_bytes: usize,
    pub allowed_domains: Vec<String>,
    pub rate_limit_per_minute: u32,
}

impl Config {
    pub fn from_env() -> anyhow::Result<Self> {
        Ok(Self {
            backend_url: env::var("BACKEND_URL")
                .unwrap_or_else(|_| "http://localhost:8080".to_string()),
            gateway_port: env::var("EDGE_GATEWAY_PORT")
                .unwrap_or_else(|_| "8081".to_string())
                .parse()?,
            log_level: env::var("RUST_LOG")
                .unwrap_or_else(|_| "debug".to_string()),
            x402_config: X402Config {
                facilitator_url: env::var("X402_FACILITATOR_URL")
                    .unwrap_or_else(|_| "https://api.x402.org".to_string()),
                base_network_url: env::var("BASE_NETWORK_URL")
                    .unwrap_or_else(|_| "https://base-goerli.public.blastapi.io".to_string()),
                payment_token_address: env::var("PAYMENT_TOKEN_ADDRESS")
                    .unwrap_or_else(|_| "0x07865c6E87B9F70255377e024ace6630C1Eaa37F".to_string()),
                supported_tokens: env::var("SUPPORTED_TOKENS")
                    .unwrap_or_else(|_| "USDC".to_string())
                    .split(',')
                    .map(|s| s.trim().to_string())
                    .collect(),
                max_payment_amount: env::var("MAX_PAYMENT_AMOUNT")
                    .unwrap_or_else(|_| "100.0".to_string())
                    .parse()?,
            },
            execution_config: ExecutionConfig {
                max_execution_time_seconds: env::var("MAX_EXECUTION_TIME_SECONDS")
                    .unwrap_or_else(|_| "120".to_string())
                    .parse()?,
                max_response_size_bytes: env::var("MAX_RESPONSE_SIZE_BYTES")
                    .unwrap_or_else(|_| "10485760".to_string()) // 10MB
                    .parse()?,
                allowed_domains: env::var("ALLOWED_DOMAINS")
                    .unwrap_or_else(|_| "api.example.com,api.veklom.com".to_string())
                    .split(',')
                    .map(|s| s.trim().to_string())
                    .collect(),
                rate_limit_per_minute: env::var("RATE_LIMIT_PER_MINUTE")
                    .unwrap_or_else(|_| "60".to_string())
                    .parse()?,
            },
        })
    }
}
