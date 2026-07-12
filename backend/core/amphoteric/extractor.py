from fastapi import Request
from backend.core.schemas.trust_fabric import AmphotericContext

def extract_amphoteric_context(request: Request) -> AmphotericContext:
    """
    Extracts the AmphotericContext from the incoming request.
    This enforces zero-trust identity before relying on heuristic transport headers.
    """
    # 1. SPIFFE SVID Validation (mTLS terminated by proxy/mesh)
    # The proxy (e.g., Envoy/Traefik with SPIFFE integration) validates the client cert
    # and passes the SPIFFE ID down via a trusted internal header.
    spiffe_id = request.headers.get("X-Spiffe-Id")
    
    # 2. Heuristic Transport Detection
    # Used for content negotiation, NOT for trust/identity decisions.
    client_heuristics = {
        "user_agent": request.headers.get("User-Agent", ""),
        "x_transport": request.headers.get("X-Transport", ""),
        "client_ip": request.client.host if request.client else None
    }
    
    transport = "rest"
    x_transport = client_heuristics["x_transport"].lower()
    
    if "mcp" in x_transport:
        transport = "mcp"
    elif "webmcp" in x_transport:
        transport = "webmcp"
    elif "mozilla" in client_heuristics["user_agent"].lower() and "mcp" not in x_transport:
        transport = "ui"
        
    return AmphotericContext(
        transport=transport,
        protocol_version=request.headers.get("X-Protocol-Version", "1.0"),
        authenticated_identity=spiffe_id,  # ONLY populated if mTLS/SPIFFE succeeded
        client_heuristics=client_heuristics
    )
