import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.services.provider_routing_service import execute_governed_inference
from backend.db.models.agent_stack import AgentSwarm
from backend.core.memory.conversation import ConversationMemory

logger = logging.getLogger(__name__)

class SwarmOrchestrator:
    """
    Orchestrates groups of agents to act as an autonomous swarm (Council).
    Agents run in parallel, hold each other accountable, and debate towards a consensus.
    All inference is routed through provider_router for Ollama/BYOK fallback handling.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _execute_agent(
        self, agent: Dict[str, Any], prompt: str, workspace_id: str, byok_keys: Optional[Dict] = None, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Execute a single agent's LLM call."""
        messages = [
            {"role": "system", "content": f"You are part of a Swarm. Your role is: {agent.get('role', 'worker')}."}
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": agent.get("model_name", "llama3"),
            "provider": agent.get("model_provider", "ollama"),
            "messages": messages,
            "max_tokens": 1000,
        }
        
        try:
            # We use the tenant-aware router to guarantee BYOK -> Ollama fallback logic
            result, source, reason, latency_ms = await execute_governed_inference(
                self.db, workspace_id, "swarm", body
            )
            
            # Extract content from standardized CompletionResult
            response_text = result.payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "agent_id": agent.get("id"),
                "role": agent.get("role"),
                "status": "success",
                "source": source,
                "content": response_text
            }
        except Exception as e:
            logger.error(f"Agent {agent.get('id')} failed: {e}")
            return {
                "agent_id": agent.get("id"),
                "role": agent.get("role"),
                "status": "error",
                "content": str(e)
            }

    async def _debate_consensus(
        self, worker_responses: List[Dict[str, Any]], critic: Dict[str, Any], prompt: str, workspace_id: str, byok_keys: Optional[Dict] = None, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """A critic agent reviews the workers' outputs to reach a consensus."""
        
        context_block = "\n".join([f"Agent ({r['role']}): {r['content']}" for r in worker_responses])
        
        debate_prompt = f"""
Original Task: {prompt}
Worker Outputs:
{context_block}

As the Critic, review the worker outputs. Resolve any contradictions and provide the final unified answer.
"""
        return await self._execute_agent(critic, debate_prompt, workspace_id, byok_keys, history)


    async def dispatch_swarm(
        self, swarm_config: Dict[str, Any], prompt: str, workspace_id: str, byok_keys: Optional[Dict] = None, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches a swarm of agents.
        Groups them by roles. Executes workers in parallel, then uses the critic/supervisor
        to form a consensus if debate_protocol is enabled.
        """
        agents = swarm_config.get("agents", [])
        if not agents:
            return {"status": "failed", "reason": "No agents in swarm"}

        # Fetch history
        history = []
        if conversation_id:
            history = await ConversationMemory.get_history(workspace_id, conversation_id)

        # Separate roles
        workers = [a for a in agents if a.get("role", "worker") != "critic"]
        critics = [a for a in agents if a.get("role") == "critic"]
        
        # If no explicit critic, just pick the first agent as the fallback supervisor
        if not critics and len(workers) > 1:
            critics = [workers.pop()]

        # 1. Parallel execution for all workers
        worker_tasks = [self._execute_agent(worker, prompt, workspace_id, byok_keys, history) for worker in workers]
        worker_results = await asyncio.gather(*worker_tasks)
        
        # 2. Consensus / Debate phase
        debate_protocol = swarm_config.get("debate_protocol", "consensus")
        
        if critics and debate_protocol == "consensus":
            # Pass all worker results to the critic
            critic = critics[0]
            final_result = await self._debate_consensus(worker_results, critic, prompt, workspace_id, byok_keys, history)
        else:
            # Flat flat execution, just return the first worker
            final_result = worker_results[0] if worker_results else {}

        # 3. Commit to memory
        if conversation_id and final_result.get("status") == "success":
            new_msgs = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": final_result.get("content")}
            ]
            await ConversationMemory.add_messages(workspace_id, conversation_id, new_msgs)

        return {
            "swarm_id": swarm_config.get("id", "unknown"),
            "status": "success",
            "workers": worker_results,
            "final_consensus": final_result
        }
