use serde::{Deserialize, Serialize};
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub backend_url: String,
    pub authority_url: String,
    pub pgl_url: String,
    pub audit_url: String,
    pub gateway_port: u16,
    pub log_level: String,
}

impl Config {
    pub fn from_env() -> anyhow::Result<Self> {
        Ok(Self {
            backend_url: env::var("BACKEND_URL")
                .unwrap_or_else(|_| "http://localhost:8000".to_string()),
            authority_url: env::var("AUTHORITY_URL")
                .unwrap_or_else(|_| "http://localhost:8000/api/v1/authority".to_string()),
            pgl_url: env::var("PGL_URL")
                .unwrap_or_else(|_| "http://localhost:8000/api/v1/pgl".to_string()),
            audit_url: env::var("AUDIT_URL")
                .unwrap_or_else(|_| "http://localhost:8000/api/v1/evidence".to_string()),
            gateway_port: env::var("GATEWAY_PORT")
                .unwrap_or_else(|_| "8080".to_string())
                .parse()?,
            log_level: env::var("RUST_LOG")
                .unwrap_or_else(|_| "debug".to_string()),
        })
    }
}
