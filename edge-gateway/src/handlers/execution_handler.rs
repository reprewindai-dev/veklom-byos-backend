use axum::{
    extract::{Request, State},
    http::StatusCode,
    response::Json,
    body::Bytes,
};
use crate::{
    AppState,
    models::{ExecutionRequestPayload, ExecutionResult, EdgeErrorResponse},
    modules::execution_engine,
};
use tracing::{info, error, debug};
use std::collections::HashMap;

pub async fn execution_handler(
    State(state): State<AppState>,
    request: Request,
) -> Result<Json<ExecutionResult>, StatusCode> {
    info!("Received execution request");
    
    // Read request body
    let body_bytes = match axum::body::to_bytes(request.into_body(), usize::MAX).await {
        Ok(bytes) => bytes,
        Err(e) => {
            error!("Failed to read request body: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Parse execution request
    let execution_request: ExecutionRequestPayload = match serde_json::from_slice(&body_bytes) {
        Ok(request) => request,
        Err(e) => {
            error!("Failed to parse execution request: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    debug!("Executing request for EAT: {}", execution_request.eat.eat_id);
    
    // Execute the request
    match execution_engine::ExecutionEngine::execute_with_eat(execution_request, &state).await {
        Ok(result) => {
            info!("Execution completed successfully: {}", result.eat_id);
            Ok(Json(result))
        },
        Err(e) => {
            error!("Execution failed: {}", e);
            
            // Return appropriate error response
            let error_response = EdgeErrorResponse {
                error: e.to_string(),
                code: e.error_code(),
                details: None,
                timestamp: chrono::Utc::now(),
            };
            
            Err((
                StatusCode::from_u16(e.error_code()).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR),
                Json(error_response)
            ).into())
        }
    }
}

pub async fn paid_execution_handler(
    State(state): State<AppState>,
    payment_reference: axum::extract::Path<String>,
    request: Request,
) -> Result<Json<ExecutionResult>, StatusCode> {
    info!("Received paid execution request with payment: {}", payment_reference);
    
    // Read request body
    let body_bytes = match axum::body::to_bytes(request.into_body(), usize::MAX).await {
        Ok(bytes) => bytes,
        Err(e) => {
            error!("Failed to read request body: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Parse execution request
    let execution_request: ExecutionRequestPayload = match serde_json::from_slice(&body_bytes) {
        Ok(request) => request,
        Err(e) => {
            error!("Failed to parse execution request: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Execute the paid request
    match execution_engine::ExecutionEngine::execute_paid_endpoint(
        execution_request, 
        payment_reference, 
        &state
    ).await {
        Ok(result) => {
            info!("Paid execution completed successfully: {}", result.eat_id);
            Ok(Json(result))
        },
        Err(e) => {
            error!("Paid execution failed: {}", e);
            
            let error_response = EdgeErrorResponse {
                error: e.to_string(),
                code: e.error_code(),
                details: None,
                timestamp: chrono::Utc::now(),
            };
            
            Err((
                StatusCode::from_u16(e.error_code()).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR),
                Json(error_response)
            ).into())
        }
    }
}
