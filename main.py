import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from veklom_amphoteric import AmphotericRouter, create_mcp_endpoints, WebMCPSchemaInjector

app = FastAPI(title="Veklom BYOS Backend 2 - Amphoteric Node")
amphoteric = AmphotericRouter()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LANDING_PATH = os.path.join(_BASE_DIR, "frontend", "landing", "index.html")

# Define a sample data-lake query tool using the Amphoteric primitive
@amphoteric.tool(
    name="query_data_lake",
    description="Query the primary sovereign data lake. Used for RAG processing."
)
def query_data_lake(query: str, limit: int = 10):
    # Simulated data lake response
    return {
        "results": [
            {"id": "doc1", "content": f"Match for {query} from veklom-byos-backend-2"}
        ],
        "metadata": {"limit": limit, "node": "Backend 1 (Fiber)"}
    }

app.include_router(amphoteric.router)
create_mcp_endpoints(app, amphoteric, prefix="/mcp")

@app.get("/veklom-discovery.json")
async def get_veklom_discovery():
    return {
        "schema_version": "2",
        "name": "Veklom",
        "description": "Governed AI execution platform",
        "endpoints": {
            "mcp": "https://cappo.veklom.com/mcp",
            "api": "https://api.veklom.com",
            "governance": "https://cappo.veklom.com"
        },
        "discovery": {
            "agent_card": "https://veklom.com/.well-known/agent-card.json",
            "mcp_discovery": "https://cappo.veklom.com/mcp (POST, Mcp-Method: server/discover)",
            "mcp_convenience": "https://veklom.com/.well-known/mcp.json"
        },
        "pricing": {
            "model": "pay-per-call",
            "currency": "USDC",
            "discovery": "free",
            "tiers": [
                {"tier": "micro", "price_usd": "0.001", "description": "Status/discovery reads"},
                {"tier": "read", "price_usd": "0.005", "description": "Governed data reads"},
                {"tier": "action", "price_usd": "0.05", "description": "State mutations"},
                {"tier": "compute", "price_usd": "0.50", "description": "Agent execution + PGL evidence"}
            ],
            "payment_schemes": ["x402", "mpp"],
            "pricing_detail_url": "https://cappo.veklom.com/api/v1/x402/config"
        },
        "authentication": {
            "type": "oauth2",
            "authorization_server": "https://veklom.com/.well-known/oauth-authorization-server"
        },
        "extensions": {
            "pgl": {
                "specification": "https://pgl.veklom.com/spec/v0.1",
                "a2a_extension": "https://pgl.veklom.com/a2a/v1",
                "evidence_verification": "https://pgl.veklom.com/verify"
            }
        },
        "agentic_market": {
            "listed": True,
            "listing_url": "https://agentic.market/veklom"
        }
    }

@app.get("/", response_class=HTMLResponse)
async def serve_landing(request: Request):
    try:
        with open(_LANDING_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "<html><head></head><body><h1>Veklom BYOS Backend</h1><p>Landing page not found.</p></body></html>"
    
    # Inject WebMCP declarative tags
    webmcp_tags = WebMCPSchemaInjector.get_webmcp_meta_tags(amphoteric)
    if "</head>" in content:
        content = content.replace("</head>", f"{webmcp_tags}\n</head>")
        
    return HTMLResponse(content=content)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Serving Amphoteric node on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
