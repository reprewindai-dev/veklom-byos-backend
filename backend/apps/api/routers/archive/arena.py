import time
import random
import string
import httpx
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from backend.core.config.settings import settings
import logging

logger = logging.getLogger("arena")

router = APIRouter(tags=["Arena"])

class AgentConfig(BaseModel):
    id: str
    name: str
    role: str
    systemInstruction: str
    temperature: Optional[float] = 0.7
    model: Optional[str] = "gemini-2.5-flash"
    avatar: Optional[str] = "🤖"
    color: Optional[str] = "blue"

class PipelineStep(BaseModel):
    id: str
    agentId: str
    instruction: Optional[str] = "Analyze and contribute based on your role."

class TurnSimulationRequest(BaseModel):
    input: str
    workflowType: str  # "sequential" or "collaborative"
    currentAgent: AgentConfig
    historyLog: Optional[List[Any]] = []
    stepInstruction: Optional[str] = None

class FullSimulationRequest(BaseModel):
    input: str
    workflowType: str
    agents: List[AgentConfig]
    steps: List[PipelineStep]
    discussionTurns: Optional[int] = 3

def estimate_tokens(text: str) -> int:
    return len(text) // 4 + 1

def generate_log_id() -> str:
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"log-{int(time.time() * 1000)}-{random_str}"

def map_model_name(model: str) -> str:
    # Google AI Studio models
    m = model.lower()
    if "gemini-3.5" in m or "gemini-3" in m:
        return "gemini-2.5-flash"
    if "gemini-2.5" in m:
        return "gemini-2.5-flash"
    if "gemini-1.5-pro" in m:
        return "gemini-1.5-pro"
    if "gemini-1.5" in m:
        return "gemini-1.5-flash"
    return "gemini-2.5-flash"

async def call_gemini(model: str, system_instruction: str, prompt: str, temperature: float) -> str:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY is not configured on this runtime.")
    
    mapped_model = map_model_name(model)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mapped_model}:generateContent?key={api_key}"
    
    # Construct the contents. We can put the system instruction in systemInstruction or merge into prompt.
    # The official API supports systemInstruction.
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {
                    "text": system_instruction
                }
            ]
        },
        "generationConfig": {
            "temperature": temperature
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            logger.info(f"Calling Gemini ({mapped_model}) for Arena simulation step...")
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error(f"Gemini API returned error {response.status_code}: {response.text}")
                # Fallback to prompt-embedded system instruction if systemInstruction field failed
                if "systemInstruction" in response.text:
                    logger.info("Retrying without systemInstruction field...")
                    payload_fallback = {
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": f"System Instruction:\n{system_instruction}\n\nUser Prompt:\n{prompt}"
                                    }
                                ]
                            }
                        ],
                        "generationConfig": {
                            "temperature": temperature
                        }
                    }
                    response = await client.post(url, json=payload_fallback)
            
            response.raise_for_status()
            res_data = response.json()
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "No text returned from Gemini.")
            return "No response candidates returned from Gemini."
        except Exception as e:
            logger.exception("Failed to call Gemini API")
            raise HTTPException(status_code=500, detail=f"Gemini API call failed: {str(e)}")

@router.post("/api/simulate/turn")
async def simulate_turn(req: TurnSimulationRequest):
    raise HTTPException(
        status_code=501,
        detail="Enterprise Arena Engine not yet attached. Simulated execution disabled."
    )

@router.post("/api/simulate")
async def simulate_full(req: FullSimulationRequest):
    raise HTTPException(
        status_code=501,
        detail="Enterprise Arena Engine not yet attached. Simulated execution disabled."
    )
