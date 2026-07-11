from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.core.config.settings import settings
from backend.apps.api.routers import capi

app = FastAPI(
    title="Veklom CAPI Node",
    description="Compute API Orchestration Node",
    version="1.0.0",
)

# CORS middleware for CAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the CAPI router
app.include_router(capi.router)

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "capi_node"}

if __name__ == "__main__":
    uvicorn.run("backend.apps.capi.main:app", host="0.0.0.0", port=8002, reload=True)
