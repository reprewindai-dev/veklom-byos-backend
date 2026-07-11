from fastapi import FastAPI
import uvicorn

from backend.core.config.settings import settings

app = FastAPI(
    title="Veklom Ledger Node",
    description="Internal Ledger & PGL Settlement Node (x402)",
    version="1.0.0",
)

# TODO: Add routes for x402 budget checks, PGL identity checks, receipt creation.

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "ledger_node"}

if __name__ == "__main__":
    uvicorn.run("backend.apps.ledger.main:app", host="0.0.0.0", port=8003, reload=True)
