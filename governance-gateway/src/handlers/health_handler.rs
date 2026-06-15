use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
};
use serde_json::{json, Value};
use crate::AppState;

pub async fn health_handler(
    State(state): State<AppState>,
) -> Result<Json<Value>, StatusCode> {
    let health_status = json!({
        "status": "healthy",
        "service": "governance-gateway",
        "version": "0.1.0",
        "phase": "0A",
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "components": {
            "identity": "operational",
            "authority": "operational", 
            "audit_ledger": "operational",
            "mcp_interface": "operational"
        },
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health"
        }
    });

    Ok(Json(health_status))
}
