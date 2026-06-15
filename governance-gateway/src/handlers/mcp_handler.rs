use axum::{
    extract::{Request, State},
    http::StatusCode,
    response::Response,
    body::Bytes,
};
use crate::{
    AppState,
    modules::mcp_interface,
};
use tracing::{info, error, debug};

pub async fn mcp_handler(
    State(state): State<AppState>,
    request: Request,
) -> Result<Response, StatusCode> {
    info!("Received MCP request");
    
    // Read request body
    let body_bytes = match axum::body::to_bytes(request.into_body(), usize::MAX).await {
        Ok(bytes) => bytes,
        Err(e) => {
            error!("Failed to read request body: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    debug!("MCP request body: {:?}", String::from_utf8_lossy(&body_bytes));
    
    // Parse MCP request
    let mcp_request = match mcp_interface::MCPInterfaceModule::parse_mcp_request(&body_bytes) {
        Ok(request) => request,
        Err(e) => {
            error!("Failed to parse MCP request: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };
    
    // Validate request
    if let Err(e) = mcp_interface::MCPInterfaceModule::validate_request(&mcp_request) {
        error!("Invalid MCP request: {}", e);
        return Err(StatusCode::BAD_REQUEST);
    }
    
    // Handle request
    let mcp_response = match mcp_interface::MCPInterfaceModule::handle_mcp_request(mcp_request, &state).await {
        Ok(response) => response,
        Err(e) => {
            error!("Failed to handle MCP request: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };
    
    // Serialize response
    let response_bytes = match mcp_interface::MCPInterfaceModule::serialize_mcp_response(mcp_response) {
        Ok(bytes) => bytes,
        Err(e) => {
            error!("Failed to serialize MCP response: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };
    
    debug!("MCP response sent successfully");
    
    Ok(Response::builder()
        .status(StatusCode::OK)
        .header("content-type", "application/json")
        .body(Bytes::from(response_bytes))
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?)
}
