import time
import random
import string
import httpx
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from backend.core.config.settings import settings
from backend.core.logging.logger import logger

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
    agent = req.currentAgent
    t_start = time.time()
    
    if req.workflowType == "sequential":
        previous_output = ""
        if req.historyLog:
            context_parts = []
            for log in req.historyLog:
                context_parts.append(f"[Agent: {log.get('agentName')} ({log.get('role')})]\n{log.get('output')}")
            previous_output = "\n\n---\n\n".join(context_parts)
        else:
            previous_output = "None (This is the primary workflow starting point)."
            
        prompt = (
            f"You are part of a coordinated multi-agent sequential pipeline to solve this task:\n\n"
            f"### CORE MISSION BRIEF\n"
            f"\"{req.input}\"\n\n"
            f"### CURRENT PIPELINE PROGRESS (PREVIOUS STEPS OUTPUT)\n"
            f"{previous_output}\n\n"
            f"### YOUR CURRENT ASSIGNED STEP INSTRUCTION\n"
            f"Resource specification step: \"{req.stepInstruction or 'Analyze and contribute based on your role.'}\"\n\n"
            f"=======================================================\n"
            f"Your Profile:\n"
            f"- Name: {agent.name}\n"
            f"- Specialized Role: {agent.role}\n"
            f"- Guideline Instructions: {agent.systemInstruction}\n\n"
            f"GENERATE YOUR DETAILED CONTRIBUTION NOW. Enhance, refine, or build on top of any previous progress. "
            f"Be concrete, technical, and complete (avoid generic or vague summaries). Provide code blocks, specifications, "
            f"outlines, or copy where relevant. Speak as your character. Write in standard markdown. Do not repeat previous outputs "
            f"unless explicitly modifying them."
        )
    else:
        chat_context = ""
        if req.historyLog:
            context_parts = []
            for log in req.historyLog:
                context_parts.append(f"[{log.get('agentName')} | {log.get('role')}]: {log.get('output')}")
            chat_context = "\n\n".join(context_parts)
        else:
            chat_context = "The meeting has just begun. No comments have been shared yet."
            
        prompt = (
            f"You are a key committee member in an active collaborative multi-agent brainstorming session.\n\n"
            f"### BRAND MISSION / OBJECTIVE BRIEF\n"
            f"\"{req.input}\"\n\n"
            f"### ACTIVE MEETING ROOM CHAT HISTORY\n"
            f"{chat_context}\n\n"
            f"=======================================================\n"
            f"Your Profile:\n"
            f"- Name: {agent.name}\n"
            f"- Specialized Role: {agent.role}\n"
            f"- Personality & Directives: {agent.systemInstruction}\n\n"
            f"IT IS NOW YOUR TURN TO CONTRIBUTE TO THE FEEDBACK LOOP. "
            f"Add your character voice to the discussion. React dynamically, challenge potential bugs/flaws constructively, "
            f"suggest creative shifts, or propose concrete slogans/copy based on the conversation history. "
            f"Keep your response conversational, concise, and focused (usually 1-3 highly punchy paragraphs). "
            f"Write in markdown. Address other panel members naturally if appropriate."
        )
        
    output_text = await call_gemini(
        model=agent.model or "gemini-2.5-flash",
        system_instruction=agent.systemInstruction,
        prompt=prompt,
        temperature=agent.temperature if agent.temperature is not None else 0.7
    )
    
    duration_ms = int((time.time() - t_start) * 1000)
    tokens_used = estimate_tokens(prompt) + estimate_tokens(output_text)
    
    return {
        "success": True,
        "log": {
            "id": generate_log_id(),
            "agentId": agent.id,
            "agentName": agent.name,
            "avatar": agent.avatar,
            "color": agent.color,
            "role": agent.role,
            "inputUsed": prompt,
            "output": output_text,
            "durationMs": duration_ms,
            "tokensUsed": tokens_used,
            "modelUsed": agent.model or "gemini-2.5-flash",
            "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        }
    }

@router.post("/api/simulate")
async def simulate_full(req: FullSimulationRequest):
    if not req.agents:
        raise HTTPException(status_code=400, detail="No agents in workspace config.")
        
    t_start_total = time.time()
    logs = []
    
    if req.workflowType == "sequential":
        for step in req.steps:
            agent = next((a for a in req.agents if a.id == step.agentId), None)
            if not agent:
                continue
                
            previous_output = ""
            if logs:
                context_parts = []
                for log in logs:
                    context_parts.append(f"[Agent: {log.get('agentName')} ({log.get('role')})]\n{log.get('output')}")
                previous_output = "\n\n---\n\n".join(context_parts)
            else:
                previous_output = "None (This is the primary workflow starting point)."
                
            prompt = (
                f"You are part of a coordinated multi-agent sequential pipeline to solve this task:\n\n"
                f"### CORE MISSION BRIEF\n"
                f"\"{req.input}\"\n\n"
                f"### CURRENT PIPELINE PROGRESS (PREVIOUS STEPS OUTPUT)\n"
                f"{previous_output}\n\n"
                f"### YOUR CURRENT ASSIGNED STEP INSTRUCTION\n"
                f"Resource specification step: \"{step.instruction or 'Analyze and contribute based on your role.'}\"\n\n"
                f"=======================================================\n"
                f"Your Profile:\n"
                f"- Name: {agent.name}\n"
                f"- Specialized Role: {agent.role}\n"
                f"- Guideline Instructions: {agent.systemInstruction}\n\n"
                f"GENERATE YOUR DETAILED CONTRIBUTION NOW. Enhance, refine, or build on top of any previous progress. "
                f"Be concrete, technical, and complete (avoid generic or vague summaries). Provide code blocks, specifications, "
                f"outlines, or copy where relevant. Speak as your character. Write in standard markdown. Do not repeat previous outputs "
                f"unless explicitly modifying them."
            )
            
            t_step_start = time.time()
            output_text = await call_gemini(
                model=agent.model or "gemini-2.5-flash",
                system_instruction=agent.systemInstruction,
                prompt=prompt,
                temperature=agent.temperature if agent.temperature is not None else 0.7
            )
            duration_ms = int((time.time() - t_step_start) * 1000)
            tokens_used = estimate_tokens(prompt) + estimate_tokens(output_text)
            
            logs.append({
                "id": generate_log_id(),
                "agentId": agent.id,
                "agentName": agent.name,
                "avatar": agent.avatar,
                "color": agent.color,
                "role": agent.role,
                "inputUsed": prompt,
                "output": output_text,
                "durationMs": duration_ms,
                "tokensUsed": tokens_used,
                "modelUsed": agent.model or "gemini-2.5-flash",
                "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            })
    else:
        turns = req.discussionTurns or 3
        for i in range(turns):
            agent = req.agents[i % len(req.agents)]
            
            chat_context = ""
            if logs:
                context_parts = []
                for log in logs:
                    context_parts.append(f"[{log.get('agentName')} | {log.get('role')}]: {log.get('output')}")
                chat_context = "\n\n".join(context_parts)
            else:
                chat_context = "The meeting has just begun. No comments have been shared yet."
                
            prompt = (
                f"You are a key committee member in an active collaborative multi-agent brainstorming session.\n\n"
                f"### BRAND MISSION / OBJECTIVE BRIEF\n"
                f"\"{req.input}\"\n\n"
                f"### ACTIVE MEETING ROOM CHAT HISTORY\n"
                f"{chat_context}\n\n"
                f"=======================================================\n"
                f"Your Profile:\n"
                f"- Name: {agent.name}\n"
                f"- Specialized Role: {agent.role}\n"
                f"- Personality & Directives: {agent.systemInstruction}\n\n"
                f"IT IS NOW YOUR TURN TO CONTRIBUTE TO THE FEEDBACK LOOP. "
                f"Add your character voice to the discussion. React dynamically, challenge potential bugs/flaws constructively, "
                f"suggest creative shifts, or propose concrete slogans/copy based on the conversation history. "
                f"Keep your response conversational, concise, and focused (usually 1-3 highly punchy paragraphs). "
                f"Write in markdown. Address other panel members naturally if appropriate."
            )
            
            t_step_start = time.time()
            output_text = await call_gemini(
                model=agent.model or "gemini-2.5-flash",
                system_instruction=agent.systemInstruction,
                prompt=prompt,
                temperature=agent.temperature if agent.temperature is not None else 0.7
            )
            duration_ms = int((time.time() - t_step_start) * 1000)
            tokens_used = estimate_tokens(prompt) + estimate_tokens(output_text)
            
            logs.append({
                "id": generate_log_id(),
                "agentId": agent.id,
                "agentName": agent.name,
                "avatar": agent.avatar,
                "color": agent.color,
                "role": agent.role,
                "inputUsed": prompt,
                "output": output_text,
                "durationMs": duration_ms,
                "tokensUsed": tokens_used,
                "modelUsed": agent.model or "gemini-2.5-flash",
                "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            })
            
    final_output = logs[-1].get("output") if logs else "No output generated."
    total_duration_ms = int((time.time() - t_start_total) * 1000)
    
    return {
        "success": True,
        "logs": logs,
        "finalOutput": final_output,
        "totalDurationMs": total_duration_ms
    }
