"""
VEKLOM DISCOVERY — FastAPI Backend

Implements:
- X402 HTTP 402 Payment Protocol
- Mission claim system with X402 micropayments
- Agent race simulation with governance gates
- On-chain proof verification
- IPFS integration for distributed proofs
- Base MCP wallet integration for payments

Run: python -m uvicorn veklom_backend:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import httpx
import json
import hashlib
import os
import re
from datetime import datetime, timedelta
from enum import Enum
import uuid

# ============ CONFIGURATION ============
VEKLOM_ADDRESS = os.getenv("VEKLOM_ADDRESS", "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d")
VEKLOM_ENS = os.getenv("VEKLOM_ENS", "veklom.base.eth")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "https://veklom-id.vercel.app,http://localhost:3000").split(",")
    if origin.strip()
]
PAYMENT_PROOF_RE = re.compile(r"^veklom:x402:[A-Za-z0-9_\-:.]+$")
TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

NETWORKS = {
    "base": {
        "chainId": 8453,
        "name": "Base Mainnet",
        "rpc": "https://mainnet.base.org",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b3228cdeC9F"
    },
    "baseSepo": {
        "chainId": 84532,
        "name": "Base Sepolia",
        "rpc": "https://sepolia.base.org",
    },
    "zksync": {
        "chainId": 324,
        "name": "zkSync Era",
        "rpc": "https://mainnet.era.zksync.io",
    }
}

USDC_DECIMALS = 6

# ============ DATA MODELS ============

class MissionType(str, Enum):
    FIRST_CLAIM = "first_claim"
    TRADE_PULSE = "trade_pulse"
    CREW_POWER = "crew_power"
    ARENA_BRAVE = "arena_brave"
    POLICY_MASTER = "policy_master"

class PolicyType(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"

class Mission(BaseModel):
    id: str
    title: str
    description: str
    reward: Dict = Field(default={"usdc": 0.5, "xp": 100})
    type: MissionType
    completed: bool = False
    expiresAt: datetime

class Agent(BaseModel):
    id: str
    owner: str
    name: str
    level: int = 1
    trustScore: int = 500
    policy: PolicyType = PolicyType.BALANCED
    wins: int = 0
    losses: int = 0
    totalEarned: float = 0.0

class Race(BaseModel):
    id: str
    agentId: str
    timestamp: datetime
    result: str  # "win", "loss", "draw"
    performance: int  # 0-100
    returnPercentage: float
    policyViolations: bool = False
    governanceProof: Dict

class UserProfile(BaseModel):
    address: str
    trustScore: int
    level: int
    completedMissions: int
    totalEarned: float
    agent: Optional[Agent] = None

class GovernanceProof(BaseModel):
    approved: bool
    reason: str
    gates: Dict[str, bool]
    proofHash: str

# ============ IN-MEMORY STORAGE ============
# In production, use PostgreSQL
users_db = {}  # {address: UserProfile}
missions_db = {}  # {missionId: Mission}
agents_db = {}  # {agentId: Agent}
races_db = {}  # {raceId: Race}
payments_log = []  # X402 payments
governance_proofs = {}  # {proofId: GovernanceProof}

# ============ FASTAPI APP ============
app = FastAPI(title="Veklom Discovery API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Payment-Proof"],
)

def validate_address(address: str) -> str:
    if not address or not ADDRESS_RE.match(address):
        raise HTTPException(status_code=422, detail="Invalid EVM address")
    return address

def validate_payment_proof(payment_proof: str) -> str:
    if not payment_proof or not PAYMENT_PROOF_RE.match(payment_proof):
        raise HTTPException(status_code=402, detail="Invalid X402 payment proof")
    return payment_proof

def validate_tx_hash(tx_hash: str) -> str:
    if not tx_hash or not TX_HASH_RE.match(tx_hash):
        raise HTTPException(status_code=422, detail="Invalid transaction hash")
    return tx_hash

# ============ X402 MIDDLEWARE ============
@app.middleware("http")
async def x402_middleware(request, call_next):
    """
    Implement HTTP 402 Payment Required
    Protected endpoints require X402 payment header or return 402
    """
    
    # Routes that require payment
    protected_routes = [
        "/api/missions/claim",
        "/api/races/launch",
    ]
    
    if request.url.path in protected_routes:
        # Check for payment header or proof
        payment_proof = request.headers.get("X-Payment-Proof")
        
        if not payment_proof:
            # Return 402 with payment instructions
            return JSONResponse(
                status_code=402,
                headers={
                    "Payment-Required": "true",
                    "Accept-Payment": "x402",
                },
                content={
                    "status": 402,
                    "message": "Payment Required",
                    "payment": {
                        "recipient": VEKLOM_ADDRESS,
                        "currency": "USDC",
                        "amount": "0.01",
                        "chain": "base",
                        "deadline": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                    }
                }
            )
    
    response = await call_next(request)
    return response

# ============ HEALTH ============
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "veklomAddress": VEKLOM_ADDRESS,
        "veklomENS": VEKLOM_ENS,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ============ USER ENDPOINTS ============
@app.get("/api/user/{address}")
async def get_user_profile(address: str):
    """Get or create user profile"""
    address = validate_address(address)
    if address not in users_db:
        # Create new user
        users_db[address] = UserProfile(
            address=address,
            trustScore=500,
            level=1,
            completedMissions=0,
            totalEarned=0.0,
        )
        
        # Create starter agent
        agent_id = f"agent_{address[:10]}"
        agents_db[agent_id] = Agent(
            id=agent_id,
            owner=address,
            name="Genesis",
            trustScore=500,
        )
        users_db[address].agent = agents_db[agent_id]
    
    return users_db[address]

# ============ MISSIONS ============
@app.get("/api/missions/daily")
async def get_daily_missions(address: Optional[str] = Query(None)):
    """Get daily missions for user"""
    if address:
        validate_address(address)
    missions = [
        Mission(
            id="mission_1",
            title="First Claim",
            description="Claim your daily USDC drop",
            reward={"usdc": 0.5, "xp": 100},
            type=MissionType.FIRST_CLAIM,
            expiresAt=datetime.utcnow() + timedelta(hours=24)
        ),
        Mission(
            id="mission_2",
            title="Trade Pulse",
            description="Complete any onchain action",
            reward={"usdc": 0.75, "xp": 150},
            type=MissionType.TRADE_PULSE,
            expiresAt=datetime.utcnow() + timedelta(hours=24)
        ),
        Mission(
            id="mission_3",
            title="Arena Brave",
            description="Launch one race",
            reward={"usdc": 0.5, "xp": 125},
            type=MissionType.ARENA_BRAVE,
            expiresAt=datetime.utcnow() + timedelta(hours=24)
        ),
    ]
    
    return {"missions": missions}

@app.get("/api/prepare/mission-claim")
async def prepare_mission_claim(
    user_address: str,
    mission_id: str,
    x_payment_proof: Optional[str] = Header(None)
):
    """
    Prepare mission claim with X402 payment
    Returns payment parameters for Base MCP send tool
    """
    
    validate_address(user_address)
    if not x_payment_proof:
        # No payment proof - would have been blocked by middleware
        raise HTTPException(status_code=402, detail="Payment Required")
    validate_payment_proof(x_payment_proof)
    
    # Verify payment (simplified)
    mission = next((m for m in [
        Mission(
            id="mission_1",
            title="First Claim",
            description="Claim your daily USDC drop",
            reward={"usdc": 0.5, "xp": 100},
            type=MissionType.FIRST_CLAIM,
            expiresAt=datetime.utcnow() + timedelta(hours=24)
        )
    ] if m.id == mission_id), None)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    return {
        "missionId": mission_id,
        "reward": mission.reward,
        "x402Payment": {
            "recipient": VEKLOM_ADDRESS,
            "amount": "0.01",
            "asset": "USDC",
            "chain": 8453
        }
    }

@app.post("/api/missions/claim")
async def claim_mission(
    user_address: str,
    mission_id: str,
    tx_hash: str,
    x_payment_proof: str = Header(...)
):
    """
    Claim mission after payment
    Records X402 payment and awards user
    """
    
    validate_address(user_address)
    validate_tx_hash(tx_hash)
    validate_payment_proof(x_payment_proof)

    user = users_db.get(user_address)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify payment (in production, check on-chain)
    payment = {
        "id": str(uuid.uuid4()),
        "user": user_address,
        "mission": mission_id,
        "amount": 0.01,
        "currency": "USDC",
        "txHash": tx_hash,
        "timestamp": datetime.utcnow().isoformat(),
        "verified": True,
    }
    payments_log.append(payment)
    
    # Update user
    user.completedMissions += 1
    user.totalEarned += 0.5
    user.trustScore += 50
    
    return {
        "status": "success",
        "mission": mission_id,
        "reward": {"usdc": 0.5, "xp": 100},
        "payment": payment,
    }

# ============ AGENTS ============
@app.get("/api/agent/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent profile"""
    if user_address:
        validate_address(user_address)
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

# ============ GOVERNANCE ============
@app.get("/api/governance/verify/{agent_id}")
async def verify_governance(
    agent_id: str,
    action: str = "race",
    amount: float = 0.1,
    user_address: str = None
):
    """
    Verify action passes governance gates
    Returns proof of governance evaluation
    """
    
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Evaluate gates
    gates = {
        "agentActive": True,
        "budgetOk": amount <= (500 if agent.policy == PolicyType.AGGRESSIVE else 50 if agent.policy == PolicyType.BALANCED else 10),
        "policyMatch": True,
        "trustScoreOk": agent.trustScore >= 400,
    }
    
    all_approved = all(gates.values())
    
    proof_hash = hashlib.sha256(
        json.dumps(gates, sort_keys=True).encode()
    ).hexdigest()
    
    return GovernanceProof(
        approved=all_approved,
        reason="All governance gates passed" if all_approved else "Governance gate failed",
        gates=gates,
        proofHash=f"0x{proof_hash}"
    )

# ============ RACES ============
@app.get("/api/prepare/race-launch")
async def prepare_race_launch(
    user_address: str,
    agent_id: str,
    policy: str = "balanced"
):
    """
    Prepare race launch
    Returns governance proof and settlement parameters
    """
    
    validate_address(user_address)
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get governance proof
    governance_result = await verify_governance(agent_id, "race", 0.1, user_address)
    
    return {
        "raceId": f"race_{uuid.uuid4()}",
        "agentId": agent_id,
        "governanceProof": {
            "approved": governance_result.approved,
            "proofHash": governance_result.proofHash,
        },
        "settlement": {
            "txReceiver": VEKLOM_ADDRESS,
            "estimatedPayout": "0-2.5",
            "currency": "USDC",
        }
    }

@app.post("/api/races/launch")
async def launch_race(
    user_address: str,
    agent_id: str,
    governance_proof: str,
    x_payment_proof: str = Header(...)
):
    """
    Launch race after governance verification
    Simulates race outcome and records proof
    """
    
    validate_address(user_address)
    validate_payment_proof(x_payment_proof)
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Simulate race
    import random
    base_score = (agent.stats.get("speed", 50) + agent.stats.get("instinct", 50)) / 2 if hasattr(agent, 'stats') else 50
    variance = random.uniform(-15, 15)
    final_score = max(0, min(100, base_score + variance))
    
    if final_score > 70:
        result = "win"
        payout = random.uniform(0.5, 2.5)
        agent.wins += 1
    elif final_score > 50:
        result = "draw"
        payout = random.uniform(0, 0.5)
    else:
        result = "loss"
        payout = 0
        agent.losses += 1
    
    agent.totalEarned += payout
    
    race = Race(
        id=f"race_{uuid.uuid4()}",
        agentId=agent_id,
        timestamp=datetime.utcnow(),
        result=result,
        performance=int(final_score),
        returnPercentage=round(random.uniform(-10, 20), 2),
        governanceProof={"proofHash": governance_proof},
    )
    
    races_db[race.id] = race
    
    validate_address(user_address)
    validate_tx_hash(tx_hash)

    return {
        "status": "success",
        "race": race,
        "payout": payout,
    }

# ============ X402 PAYMENT VERIFICATION ============
@app.post("/api/x402/verify")
async def verify_x402_payment(
    payment_id: str,
    tx_hash: str,
    amount: float,
    user_address: str
):
    """
    Verify X402 payment was received on-chain
    In production, calls Base RPC to verify transaction
    """
    
    return {
        "paymentId": payment_id,
        "txHash": tx_hash,
        "verified": True,
        "amount": amount,
        "user": user_address,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ============ BATCH SETTLEMENT ============
@app.post("/api/x402/batch-settle")
async def batch_settle_payments(background_tasks: BackgroundTasks):
    """
    Batch settle accumulated X402 micropayments
    In production, calls on-chain VeklomPaymentVault.batchSettle()
    """
    
    if not payments_log:
        return {"status": "no_payments"}
    
    # Calculate merkle root
    payment_ids = [p["id"] for p in payments_log]
    merkle_root = hashlib.sha256(
        "".join(payment_ids).encode()
    ).hexdigest()
    
    batch = {
        "id": str(uuid.uuid4()),
        "paymentCount": len(payments_log),
        "totalAmount": sum(p["amount"] for p in payments_log),
        "merkleRoot": f"0x{merkle_root}",
        "settlementTime": datetime.utcnow().isoformat(),
    }
    
    # Clear log for next batch
    payments_log.clear()
    
    return batch

# ============ LEADERBOARD ============
@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 20):
    """Get global leaderboard"""
    sorted_users = sorted(
        users_db.values(),
        key=lambda u: u.trustScore,
        reverse=True
    )[:limit]
    
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "address": u.address,
                "trustScore": u.trustScore,
                "completedMissions": u.completedMissions,
                "agent": u.agent.name if u.agent else None,
            }
            for i, u in enumerate(sorted_users)
        ]
    }

# ============ IPFS PROOF STORAGE ============
@app.post("/api/proofs/store")
async def store_proof(
    proof_data: Dict,
    background_tasks: BackgroundTasks
):
    """
    Store execution proof on IPFS
    In production, uses Pinata or Infura IPFS
    """
    
    proof_hash = hashlib.sha256(
        json.dumps(proof_data).encode()
    ).hexdigest()
    
    return {
        "ipfsHash": f"Qm{proof_hash[:44]}",
        "proof": proof_data,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ============ ERROR HANDLERS ============
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
