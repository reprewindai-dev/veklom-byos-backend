from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class TerminalCommand(BaseModel):
    command: str

@router.post("/shell")
async def execute_shell(cmd: TerminalCommand, request: Request):
    """
    Mock terminal shell for the UI demonstration.
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
        
    return logs
