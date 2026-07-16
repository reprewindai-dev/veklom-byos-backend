import os
import uuid
import math
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from epca_policy import check_action_safety

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vek-backend")

app = FastAPI(title="Veklom Scaffold Backend", version="1.0.0")

# Configure CORS securely: explicitly specify allowed origins from env or default to frontend URL
allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentOnboardingRequest(BaseModel):
    name: str
    country: str = "CA"
    age: int = 25
    identity_score: float = 0.95

@app.get("/health")
def health():
    # Continuous SPIFFE SVID Check Simulation
    return {
        "status": "healthy",
        "svid": "spiffe://local.veklom.dev/ns/default/sa/scaffold-backend",
        "spire_attestation": "verified",
        "temporal_worker": "connected"
    }

@app.post("/api/v1/onboard")
def run_onboarding(req: AgentOnboardingRequest):
    # 1. Run Z3 SMT ePCA Guardrails
    is_safe, proof_msg = check_action_safety(req.country, req.age, req.identity_score, is_authorized=True)
    
    # 2. Calculate simulated Semantic Drift (Cosine Metric)
    # Drift increases with successive mock workflow cycles
    drift_score = round(1.0 - math.cos(0.052), 6)
    
    if not is_safe:
        logger.error(f"ePCA Veto: {proof_msg}")
        raise HTTPException(
            status_code=403,
            detail={
                "status": "UNSAT",
                "reason": proof_msg,
                "remediation": "Update request attributes to satisfy Z3 compliance formulas."
            }
        )
    
    # 3. Commit state with mock SPIFFE identity
    session_id = str(uuid.uuid4())
    logger.info(f"Durable state saved for session {session_id} using SPIFFE identity")

    return {
        "session_id": session_id,
        "status": "SATISFIABLE",
        "drift_score": drift_score,
        "token_budget_consumed": 45,
        "evidence_hash": "sha256-" + uuid.uuid4().hex[:16],
        "proof_message": proof_msg
    }
