import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import uuid
from datetime import datetime
from agents.agent_ollama import run_agent, log
from backend.core.database.database import async_session
from backend.db.models.agent_stack import AgentExecution

GOALS = [
    "Check backend health and verify system is operational.",
    "List all marketplace vendors and tell me how many there are.",
    "Get the operating reserve balance for tenant 't-alpha'.",
    "List all models currently pulled in Ollama.",
    "Route a payload 'Activate shield' to IronGrid node at coordinates x=10, y=20."
]

async def log_to_db(goal, result, start_time, end_time, tools_used, error_msg=None):
    duration_ms = int((end_time - start_time) * 1000)
    status = "completed"
    if error_msg or result.get('answer', '').startswith("[Agent hit max"):
        status = "failed"
        
    async with async_session() as session:
        record = AgentExecution(
            id=f"exec_{uuid.uuid4().hex[:8]}",
            agent_id=1,
            workspace_id="1",
            session_id=result.get("session_id", "s-1"),
            input_data={"goal": goal},
            output_data={"answer": result.get("answer")},
            started_at=datetime.utcfromtimestamp(start_time),
            completed_at=datetime.utcfromtimestamp(end_time),
            duration_ms=duration_ms,
            status=status,
            tools_used=tools_used,
            tool_calls_count=len(tools_used),
            error_message=error_msg,
            cost_estimate=0.001 * result.get("iterations", 1)  # fake cost
        )
        session.add(record)
        await session.commit()
        print(f"Logged execution {record.id} with status {status}")

async def run_mission(goal):
    print(f"\n🚀 Starting mission: {goal}")
    start = time.time()
    try:
        result = await run_agent(goal)
        end = time.time()
        
        iters = result.get('iterations', 1)
        tools = ["llm_reasoning"] * iters
        
        await log_to_db(goal, result, start, end, tools)
        
    except Exception as e:
        end = time.time()
        await log_to_db(goal, {"goal": goal, "answer": str(e)}, start, end, [], str(e))

async def main():
    print("Initiating Agent Army Test Matrix...")
    for g in GOALS:
        await run_mission(g)
    print("\n✅ All missions complete!")

if __name__ == "__main__":
    asyncio.run(main())
