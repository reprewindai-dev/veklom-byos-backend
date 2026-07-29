import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from veklom_amphoteric import AmphotericRouter, create_mcp_endpoints, WebMCPSchemaInjector
from apps.gpc.routes import router as gpc_router, initialize_gpc
from backend.gpc.orchestrator import BuilderOrchestrator
import asyncio
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

# Register GPC routes
app.include_router(gpc_router)

@app.on_event("startup")
async def start_gpc_services():
    # Initialize GPC compiler and watchers
    await initialize_gpc()
    
    # Start the orchestrator background task
    print("[GPC] Starting Builder Orchestrator...")
    orchestrator = BuilderOrchestrator()
    app.orchestrator_task = asyncio.create_task(orchestrator.start())

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
