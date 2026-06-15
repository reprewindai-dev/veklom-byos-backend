use anyhow::Result;
use axum::{
    routing::{get, post},
    extract::{Request, State},
    http::StatusCode,
    response::{Json, Response},
    Router,
};
use edge_gateway::{
    config::Config,
    handlers::{execution_handler, health_handler, x402_handler},
    modules::{eat_verification, x402_merchant, execution_engine},
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
            std::env::var("RUST_LOG").unwrap_or_else(|_| "edge_gateway=debug,tower_http=debug".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load configuration
    dotenv::dotenv().ok();
    let config = Config::from_env()?;
    info!("Starting edge gateway with config: {:?}", config);

    // Create shared state
    let app_state = edge_gateway::AppState::new(config).await?;

    // Build router
    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/execute", post(execution_handler))
        .route("/x402/challenge", post(x402_handler::challenge))
        .route("/x402/verify", post(x402_handler::verify))
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(CorsLayer::permissive()),
        )
        .with_state(app_state);

    // Start server
    let addr = SocketAddr::from(([0, 0, 0, 0], 8081));
    info!("Edge gateway listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
