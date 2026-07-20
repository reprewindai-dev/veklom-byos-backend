"""
interlink-cAPI — Governed connection server for agents and API resources.
STANDALONE SERVICE — Aligned with Veklom Production Architecture.
"""

import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routes import intent, receipt, governance, webcapi, x402

app = FastAPI(
    title="interlink-cAPI",
    version="1.0.0",
    description="Veklom Governed Connection Layer (cAPI)"
)

cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")] if cors_origins_env else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(intent.router, prefix="/capi")
app.include_router(receipt.router, prefix="/capi")
app.include_router(governance.router, prefix="/capi")
app.include_router(webcapi.router, prefix="/capi")
app.include_router(x402.router, prefix="/capi")

@app.get("/")
async def root():
    return {"service": "interlink-cAPI", "status": "active", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
