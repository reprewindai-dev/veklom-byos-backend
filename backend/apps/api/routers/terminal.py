from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
from pydantic import BaseModel
from backend.apps.api.terminal_state import terminal_state_manager

router = APIRouter()

@router.get("/events")
async def get_terminal_events(request: Request):
    """
    SSE endpoint for streaming real-time swarm telemetry.
    """
    queue = asyncio.Queue()
    terminal_state_manager.subscribers.append(queue)
    
    async def event_generator():
        try:
            yield 'data: {"type": "connection", "message": "SSE connection established with Veklom Swarm Terminal"}\\n\\n'
            
            while True:
                if await request.is_disconnected():
                    break
                    
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {payload}\\n\\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\\n\\n"
        finally:
            if queue in terminal_state_manager.subscribers:
                terminal_state_manager.subscribers.remove(queue)
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

class TerminalCommand(BaseModel):
    command: str

@router.get("/state")
async def get_terminal_state():
    """
    Returns the real-time state of the swarm terminal, agents, delegates, and logs.
    """
    return {
        "agents": terminal_state_manager.agents,
        "delegates": terminal_state_manager.delegates,
        "logs": terminal_state_manager.logs,
        "liveMetrics": terminal_state_manager.live_metrics
    }

@router.post("/telemetry")
async def post_telemetry(payload: dict):
    source = payload.get("source", "SYS")
    message = payload.get("message", "")
    type_ = payload.get("type", "info")
    if message:
        terminal_state_manager.add_telemetry_log(source, message, type_)
    return {"status": "ok"}

@router.post("/shell")
async def execute_shell(cmd: TerminalCommand, request: Request):
    """
    Simulates a shell command execution and logs it to telemetry.
    """
    command = cmd.command.strip()
    if not command:
        return []

    logs = []
    
    if command == "ls":
        logs.append({"text": "bin   dev  home  lib64  mnt  proc  run   srv  tmp  var", "type": "out"})
        logs.append({"text": "boot  etc  lib   media  opt  root  sbin  sys  usr", "type": "out"})
    elif command == "pwd":
        logs.append({"text": "/root", "type": "out"})
    elif command == "whoami":
        logs.append({"text": "root", "type": "out"})
    elif command.startswith("echo "):
        logs.append({"text": command[5:], "type": "out"})
    else:
        logs.append({"text": f"bash: {command.split()[0]}: command not found", "type": "err"})
        
    # Log command execution to global telemetry
    terminal_state_manager.add_telemetry_log("USER-CLI", f"> {command}", "success")
    
    return logs
