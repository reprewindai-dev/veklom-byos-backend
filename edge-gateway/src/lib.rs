pub mod config;
pub mod handlers;
pub mod modules;
pub mod models;
pub mod errors;

use config::Config;
use std::sync::Arc;

#[derive(Clone)]
pub struct AppState {
    pub config: Config,
    pub http_client: reqwest::Client,
    pub used_nonces: Arc<tokio::sync::RwLock<std::collections::HashSet<String>>>,
    pub used_eat_ids: Arc<tokio::sync::RwLock<std::collections::HashSet<String>>>,
}

impl AppState {
    pub async fn new(config: Config) -> anyhow::Result<Self> {
        let http_client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()?;

        Ok(Self {
            config,
            http_client,
            used_nonces: Arc::new(tokio::sync::RwLock::new(std::collections::HashSet::new())),
            used_eat_ids: Arc::new(tokio::sync::RwLock::new(std::collections::HashSet::new())),
        })
    }
}
