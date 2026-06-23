from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import time
import random
import hashlib
import uuid

router = APIRouter(prefix="/seked", tags=["SEKED Monitoring"])

class SekedMeasurement(BaseModel):
    E: int
    R: int
    C: int
    D: int
    S: int
    timestamp: str

@router.post("/calculate")
async def calculate_ratios(measurement: SekedMeasurement):
    sigma = round((measurement.E + measurement.D) / (measurement.R + 1), 2)
    ci = round(measurement.C / max(10 - measurement.R, 1), 2)
    si = round(measurement.S / 10.0, 2)
    return {
        "sigma": sigma,
        "ci": ci,
        "si": si
    }

@router.get("/directive/{ratio}")
async def get_directive(ratio: float):
    if ratio >= 7.0:
        return {
            "ratio": ratio,
            "directive": "Execute payment processing with enhanced monitoring",
            "action_type": "EXECUTE",
            "confidence": 0.92,
            "reasoning": "High energy and drive with low resistance indicates optimal execution state"
        }
    elif ratio >= 4.0:
        return {
            "ratio": ratio,
            "directive": "Prepare for execution, monitor metrics closely",
            "action_type": "PREPARE",
            "confidence": 0.85,
            "reasoning": "Moderate energy and drive indicates readiness but not optimal state"
        }
    elif ratio >= 2.0:
        return {
            "ratio": ratio,
            "directive": "Conserve resources, delay execution",
            "action_type": "CONSERVE",
            "confidence": 0.75,
            "reasoning": "Low energy and high resistance indicates need to conserve resources"
        }
    else:
        return {
            "ratio": ratio,
            "directive": "Implement recovery protocols immediately",
            "action_type": "RECOVER",
            "confidence": 0.95,
            "reasoning": "Critical state, immediate recovery required"
        }

@router.post("/state")
async def create_state(measurement: SekedMeasurement):
    state_id = f"seked_st_{uuid.uuid4().hex[:8]}"
    fingerprint = hashlib.sha256(f"{measurement.E}{measurement.R}{measurement.C}{measurement.D}{measurement.S}{measurement.timestamp}".encode()).hexdigest()
    return {
        "id": state_id,
        "measurement": measurement.dict(),
        "fingerprint": fingerprint,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "active"
    }

@router.get("/agents")
async def get_seked_agents():
    """
    Returns SEKED metric data for agents in the workspace.
    In a real scenario, this would query the DB for real-time telemetry.
    """
    # Generating dynamic values for the real-time feel
    E1 = random.randint(7, 9)
    R1 = random.randint(1, 3)
    D1 = random.randint(7, 9)
    C1 = random.randint(6, 8)
    S1 = random.randint(6, 8)
    
    sigma1 = round((E1 + D1) / (R1 + 1), 2)
    
    E2 = random.randint(2, 5)
    R2 = random.randint(5, 8)
    D2 = random.randint(2, 4)
    C2 = random.randint(4, 6)
    S2 = random.randint(3, 5)
    
    sigma2 = round((E2 + D2) / (R2 + 1), 2)

    return [
        {
            "agent_id": "agent-001-stripe",
            "name": "Stripe Connect Engineer",
            "status": "active",
            "measurement": { "E": E1, "R": R1, "C": C1, "D": D1, "S": S1, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) },
            "ratios": { "sigma": sigma1, "ci": 0.88, "si": 0.6 },
            "directive": {
                "ratio": sigma1,
                "directive": "Execute payment processing with enhanced monitoring",
                "action_type": "EXECUTE",
                "confidence": 0.92,
                "reasoning": "High energy and drive with low resistance indicates optimal execution state"
            },
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "performance_metrics": {
                "response_time_ms": random.randint(200, 300),
                "success_rate": 0.98,
                "error_rate": 0.02,
                "throughput": random.randint(1200, 1300)
            }
        },
        {
            "agent_id": "agent-002-referral",
            "name": "Referral System Engineer", 
            "status": "recovering",
            "measurement": { "E": E2, "R": R2, "C": C2, "D": D2, "S": S2, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) },
            "ratios": { "sigma": sigma2, "ci": 0.56, "si": 0.4 },
            "directive": {
                "ratio": sigma2,
                "directive": "Conserve resources and implement recovery protocols",
                "action_type": "RECOVER",
                "confidence": 0.75,
                "reasoning": "Low energy and high resistance indicates need for recovery"
            },
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "performance_metrics": {
                "response_time_ms": random.randint(800, 1000),
                "success_rate": 0.85,
                "error_rate": 0.15,
                "throughput": random.randint(400, 500)
            }
        }
    ]
