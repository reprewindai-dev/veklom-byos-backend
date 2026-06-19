use axum::{
    extract::{Request, State},
    http::StatusCode,
    response::Response,
    body::Bytes,
};
use crate::{
    AppState,
    modules::mcp_interface,
    modules::mcp_tool_router::MCPToolRouter,
};
use serde_json::Value;
use tracing::{info, error, debug};

/// MCP handler — routes both legacy execute_action calls and
/// Covenant-originated tools/call (JSON-RPC 2.0) from MCPBridge.
pub async fn mcp_handler(
    State(state): State<AppState>,
    request: Request,
) -> Result<Response, StatusCode> {
    // Extract Covenant headers before consuming the request
    let covenant_id  = header_str(request.headers(), "x-covenant-id");
    let agent_id_hdr = header_str(request.headers(), "x-agent-id");
    let trace_id_hdr = header_str(request.headers(), "x-trace-id");

    info!(
        "MCP request  covenant_id={} agent={} trace={}",
        covenant_id, agent_id_hdr, trace_id_hdr
    );

    // Read body
    let body_bytes = match axum::body::to_bytes(request.into_body(), usize::MAX).await {
        Ok(b) => b,
        Err(e) => {
            error!("Body read error: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };

    debug!("MCP body: {}", String::from_utf8_lossy(&body_bytes));

    // Peek at method to route correctly
    let envelope: Value = match serde_json::from_slice(&body_bytes) {
        Ok(v) => v,
        Err(e) => {
            error!("JSON parse error: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
    };

    let method  = envelope.get("method").and_then(|v| v.as_str()).unwrap_or("");
    let call_id = envelope.get("id").cloned();
    let params  = envelope.get("params").cloned().unwrap_or(Value::Object(Default::default()));

    // tools/call → Covenant bridge handler
    // everything else → legacy mcp_interface (unchanged)
    let mcp_response = if method == "tools/call" {
        match MCPToolRouter::handle(
            params,
            call_id,
            &covenant_id,
            &agent_id_hdr,
            &trace_id_hdr,
            &state,
        ).await {
            Ok(r)  => r,
            Err(e) => { error!("tools/call error: {}", e); return Err(StatusCode::INTERNAL_SERVER_ERROR); }
        }
    } else {
        let mcp_request = match mcp_interface::MCPInterfaceModule::parse_mcp_request(&body_bytes) {
            Ok(r)  => r,
            Err(e) => { error!("MCP parse error: {}", e); return Err(StatusCode::BAD_REQUEST); }
        };
        if let Err(e) = mcp_interface::MCPInterfaceModule::validate_request(&mcp_request) {
            error!("MCP validation error: {}", e);
            return Err(StatusCode::BAD_REQUEST);
        }
        match mcp_interface::MCPInterfaceModule::handle_mcp_request(mcp_request, &state).await {
            Ok(r)  => r,
            Err(e) => { error!("MCP handle error: {}", e); return Err(StatusCode::INTERNAL_SERVER_ERROR); }
        }
    };

    let response_bytes = match mcp_interface::MCPInterfaceModule::serialize_mcp_response(mcp_response) {
        Ok(b)  => b,
        Err(e) => { error!("Serialize error: {}", e); return Err(StatusCode::INTERNAL_SERVER_ERROR); }
    };

    Ok(Response::builder()
        .status(StatusCode::OK)
        .header("content-type", "application/json")
        .body(axum::body::Body::from(Bytes::from(response_bytes)))
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?)
}

fn header_str(headers: &axum::http::HeaderMap, name: &str) -> String {
    headers
        .get(name)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string()
}
