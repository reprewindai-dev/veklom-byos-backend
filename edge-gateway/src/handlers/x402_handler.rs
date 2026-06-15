use axum::{
    extract::{Request, State},
    http::StatusCode,
    response::Json,
    body::Bytes,
};
use crate::{
    AppState,
    models::{X402Challenge, X402PaymentProof, PaidEndpoint, EdgeErrorResponse},
    modules::x402_merchant,
};
use tracing::{info, error, debug};
use serde_json::json;

pub async fn challenge(
    State(state): State<AppState>,
    request: Request,
) -> Result<Json<X402Challenge>, StatusCode> {
    info!("Received x402 challenge request");
    
    // Read request body
    let body_bytes = match axum::body::to_bytes(request.into_body(), usize::MAX).await {
        Ok(bytes) => bytes,
        Err(e) => {
            error!("Failed to read request body: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Parse challenge request
    let challenge_request: serde_json::Value = match serde_json::from_slice(&body_bytes) {
        Ok(request) => request,
        Err(e) => {
            error!("Failed to parse challenge request: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Extract endpoint and workspace info
    let endpoint_path = challenge_request.get("endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("/api/v1/premium/analysis");
    
    let workspace_id = challenge_request.get("workspace_id")
        .and_then(|v| v.as_str());
    
    // Check if this endpoint requires payment
    let paid_endpoint = match x402_merchant::X402MerchantModule::requires_payment(
        endpoint_path, 
        "POST", 
        &state
    ).await {
        Some(endpoint) => endpoint,
        None => {
            debug!("Endpoint does not require payment: {}", endpoint_path);
            return Err(StatusCode::NOT_FOUND);
        }
    };
    
    // Create challenge
    match x402_merchant::X402MerchantModule::create_challenge(
        &paid_endpoint,
        workspace_id,
        &state,
    ).await {
        Ok(challenge) => {
            info!("x402 challenge created: {}", challenge.challenge_id);
            Ok(Json(challenge))
        },
        Err(e) => {
            error!("Failed to create x402 challenge: {}", e);
            
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

pub async fn verify(
    State(state): State<AppState>,
    request: Request,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Received x402 verification request");
    
    // Read request body
    let body_bytes = match axum::body::to_bytes(request.into_body(), usize::MAX).await {
        Ok(bytes) => bytes,
        Err(e) => {
            error!("Failed to read request body: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Parse payment proof
    let payment_proof: X402PaymentProof = match serde_json::from_slice(&body_bytes) {
        Ok(proof) => proof,
        Err(e) => {
            error!("Failed to parse payment proof: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Check if payment reference has been used (replay protection)
    match x402_merchant::X402MerchantModule::is_payment_reference_used(
        &payment_proof.payment_reference,
        &state,
    ).await {
        Ok(true) => {
            error!("Payment reference already used: {}", payment_proof.payment_reference);
            return Err(StatusCode::CONFLICT);
        },
        Ok(false) => {
            // Continue with verification
        },
        Err(e) => {
            error!("Failed to check payment reference: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    }
    
    // Get expected amount from the payment proof or use default
    let expected_amount = payment_proof.amount.parse::<f64>()
        .unwrap_or(5.0); // Default paid endpoint amount
    
    let expected_currency = &payment_proof.currency;
    
    // Verify payment
    match x402_merchant::X402MerchantModule::verify_payment(
        &payment_proof,
        expected_amount,
        expected_currency,
        &state,
    ).await {
        Ok(verification) => {
            // Mark payment reference as used
            if let Err(e) = x402_merchant::X402MerchantModule::mark_payment_reference_used(
                &payment_proof.payment_reference,
                &state,
            ).await {
                error!("Failed to mark payment reference as used: {}", e);
                // Continue anyway since payment was verified
            }
            
            info!("x402 payment verified: {}", payment_proof.payment_reference);
            
            let response = json!({
                "verified": true,
                "payment_reference": payment_proof.payment_reference,
                "verification_timestamp": verification.verification_timestamp,
                "execution_token": format!("exec_{}", uuid::Uuid::new_v4().to_string().replace("-", "")[..16].to_string())
            });
            
            Ok(Json(response))
        },
        Err(e) => {
            error!("x402 payment verification failed: {}", e);
            
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

pub async fn status(
    State(state): State<AppState>,
    axum::extract::Path(payment_reference): axum::extract::Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Checking x402 payment status: {}", payment_reference);
    
    // Check if payment reference has been used
    match x402_merchant::X402MerchantModule::is_payment_reference_used(
        &payment_reference,
        &state,
    ).await {
        Ok(used) => {
            let response = json!({
                "payment_reference": payment_reference,
                "used": used,
                "timestamp": chrono::Utc::now()
            });
            
            Ok(Json(response))
        },
        Err(e) => {
            error!("Failed to check payment status: {}", e);
            
            let error_response = EdgeErrorResponse {
                error: e.to_string(),
                code: 500,
                details: None,
                timestamp: chrono::Utc::now(),
            };
            
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(error_response)
            ).into())
        }
    }
}
