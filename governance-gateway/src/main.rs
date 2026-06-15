use anyhow::Result;
use axum::{
    routing::{get, post},
    extract::{Request, State},
    http::StatusCode,
    response::{Json, Response},
    Router,
};
use governance_gateway::{
    config::Config,
    handlers::{mcp_handler, health_handler},
    modules::{identity, authority, audit_ledger, mcp_interface},
};
use std::net::SocketAddr;
use tower::ServiceBuilder;
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::{info, error};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "governance_gateway=debug,tower_http=debug".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load configuration
    dotenv::dotenv().ok();
    let config = Config::from_env()?;
    info!("Starting governance gateway with config: {:?}", config);

    // Create shared state
    let app_state = governance_gateway::AppState::new(config).await?;

    // Build router
    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/mcp", post(mcp_handler))
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(CorsLayer::permissive()),
        )
        .with_state(app_state);

    // Start server
    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    info!("Governance gateway listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
