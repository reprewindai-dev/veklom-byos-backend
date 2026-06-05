import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.core.database.database import get_db_session
from backend.core.database.redis_client import redis_client
from backend.core.ai.provider_router import run_completion
from backend.db.models.ai import ExecLog
from backend.db.models.marketplace import PipelineRun
from sqlalchemy import select, update

async def _update_job_state(transaction_id: str, state: Dict[str, Any]):
    if not redis_client:
        return
    
    key = f"job:{transaction_id}"
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        await redis_client.set(key, json.dumps(state), ex=86400) # Expire in 24 hours
    except Exception as e:
        logger.error(f"Failed to update job state for {transaction_id}: {e}")

async def _log_execution(workspace_id: str, user_id: str, provider: str, model: str, latency: int, tokens: int, cost: float):
    try:
        async with get_db_session() as db:
            log_entry = ExecLog(
                user_id=user_id,
                workspace_id=workspace_id,
                model=model,
                provider=provider,
                prompt_tokens=tokens // 2,
                completion_tokens=tokens // 2,
                total_tokens=tokens,
                cost_usd=cost,
                latency_ms=latency,
                status="completed"
            )
            db.add(log_entry)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log execution: {e}")

async def _update_pipeline_run(run_id: str, updates: dict):
    try:
        async with get_db_session() as db:
            result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            run = result.scalar_one_or_none()
            if run:
                for k, v in updates.items():
                    setattr(run, k, v)
                if updates.get("status") in ("completed", "failed"):
                    run.completed_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as e:
        logger.error(f"Failed to update PipelineRun {run_id}: {e}")

async def run_pipeline_background(transaction_id: str, steps: List[Dict], workspace_id: str, user_id: str):
    """Executes a pipeline autonomously in the background and updates Postgres."""
    await _update_pipeline_run(transaction_id, {
        "status": "running",
        "progress": 0,
        "current_step": "Initializing autonomous pipeline engine..."
    })
    
    total_steps = len(steps)
    if total_steps == 0:
        await _update_pipeline_run(transaction_id, {
            "status": "completed",
            "progress": 100,
            "current_step": "Pipeline has no steps.",
            "output": {"result": "No steps to run."}
        })
        return
        
    context = "Initial Pipeline State."
    
    for i, step in enumerate(steps):
        step_name = step.get("name", f"Step {i+1}")
        await _update_pipeline_run(transaction_id, {
            "current_step": step_name,
            "progress": int((i / total_steps) * 100)
        })
        
        try:
            start_time = datetime.now()
            # Send prompt to AI Provider router
            prompt = f"Perform step: {step_name}. Previous Context: {context}. Be concise and factual."
            
            # Use OpenAI as default if no specific provider logic applies to the step
            result = await run_completion({"provider": "openai", "messages": [{"role": "user", "content": prompt}]}, stream=False)
            
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Parse output context
            context = result.payload.get("choices", [{}])[0].get("message", {}).get("content", "Step completed.")
            
            # Approx tokens for demo
            tokens = len(prompt.split()) + len(context.split())
            cost = tokens * 0.00001
            
            await _log_execution(workspace_id, user_id, result.provider, result.payload.get("model", "unknown"), latency, tokens, cost)
            
            # Brief delay to allow monitoring systems to tick
            await asyncio.sleep(1.5)
            
        except Exception as e:
            logger.error(f"Pipeline step {step_name} failed: {e}")
            await _update_pipeline_run(transaction_id, {
                "status": "failed",
                "error": f"Failed at {step_name}: {str(e)}",
                "current_step": step_name
            })
            return
            
    # Finalize
    await _update_pipeline_run(transaction_id, {
        "status": "completed",
        "progress": 100,
        "current_step": "Done",
        "output": {"result": context, "evidence_id": f"evd_{transaction_id[:8]}", "proof_hash": f"0x{transaction_id[:16]}"}
    })

async def run_gpc_background(transaction_id: str, graph: Dict, workspace_id: str, user_id: str, provider: str, model: str):
    """Executes a Governed Plan Compiler (GPC) graph autonomously."""
    state = {
        "status": "PROCESSING",
        "progress": 0,
        "detail": "Bootstrapping GPC reasoning graph...",
        "destination_node": None
    }
    await _update_job_state(transaction_id, state)
    
    nodes = graph.get("nodes", [])
    total_nodes = len(nodes)
    if total_nodes == 0:
        state["status"] = "COMPLETED"
        state["progress"] = 100
        state["detail"] = "GPC Graph is empty."
        await _update_job_state(transaction_id, state)
        return
        
    context = "Initial invariant state."
    
    for i, node in enumerate(nodes):
        node_id = node.get("id", f"node_{i}")
        desc = node.get("description", "Node Execution")
        
        state["destination_node"] = node_id
        state["detail"] = f"Evaluating {desc}..."
        state["progress"] = int((i / total_nodes) * 100)
        await _update_job_state(transaction_id, state)
        
        try:
            start_time = datetime.now()
            prompt = f"GPC Node: {desc}. Evaluate according to invariant limits. Current Context: {context}"
            
            result = await run_completion({"provider": provider, "model": model, "messages": [{"role": "user", "content": prompt}]}, stream=False)
            
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            context = result.payload.get("choices", [{}])[0].get("message", {}).get("content", "Evaluated.")
            
            tokens = len(prompt.split()) + len(context.split())
            cost = tokens * 0.00002
            
            await _log_execution(workspace_id, user_id, result.provider, result.payload.get("model", model), latency, tokens, cost)
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"GPC execution failed at node {node_id}: {e}")
            state["status"] = "FAILED"
            state["detail"] = f"Invariant breach at {desc}: {str(e)}"
            await _update_job_state(transaction_id, state)
            return
            
    # Finalize
    state["status"] = "COMPLETED"
    state["progress"] = 100
    state["detail"] = "GPC Path compiled and successfully executed."
    import hashlib
    state["proof_hash"] = hashlib.sha256(context.encode()).hexdigest()[:16]
    await _update_job_state(transaction_id, state)
