use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
};
use crate::{AppState, models::HealthStatus};

pub async fn health_handler(
    State(state): State<AppState>,
) -> Result<Json<HealthStatus>, StatusCode> {
    let health_status = HealthStatus {
        status: "healthy".to_string(),
        service: "edge-gateway".to_string(),
        version: "0.1.0".to_string(),
        phase: "0B".to_string(),
        timestamp: chrono::Utc::now(),
        components: crate::models::ComponentStatus {
            eat_verification: "operational".to_string(),
            x402_merchant: "operational".to_string(),
            execution_engine: "operational".to_string(),
            rate_limiter: "operational".to_string(),
        },
    };

    Ok(Json(health_status))
}
