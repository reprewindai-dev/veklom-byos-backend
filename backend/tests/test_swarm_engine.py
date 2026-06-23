import pytest
from unittest.mock import patch, MagicMock
from backend.core.services.swarm_engine import SwarmOrchestrator
from backend.core.ai.provider_router import CompletionResult

@pytest.mark.asyncio
async def test_swarm_orchestrator_parallel_execution():
    """Test that the swarm orchestrator correctly parallelizes workers and runs the critic."""
    
    mock_db = MagicMock()
    orchestrator = SwarmOrchestrator(mock_db)
    
    swarm_config = {
        "id": "test_swarm_001",
        "debate_protocol": "consensus",
        "agents": [
            {"id": "agent_1", "role": "worker", "model_name": "llama3", "model_provider": "ollama"},
            {"id": "agent_2", "role": "worker", "model_name": "llama3", "model_provider": "ollama"},
            {"id": "agent_3", "role": "critic", "model_name": "llama3", "model_provider": "ollama"}
        ]
    }
    
    # Mock the LLM completion
    async def mock_run_completion(*args, **kwargs):
        body = args[0]
        # Return a deterministic completion
        role = "worker" if "critic" not in str(body.get("messages")) else "critic"
        raw_res = {"choices": [{"message": {"content": f"I am a {role}"}}]}
        return CompletionResult("ollama", raw_res), "default", ""
        
    with patch("backend.core.services.swarm_engine.run_completion_for_tenant", side_effect=mock_run_completion):
        result = await orchestrator.dispatch_swarm(
            swarm_config, "Fix the billing engine", "workspace_test", byok_keys={}
        )
        
    assert result["status"] == "success"
    assert result["swarm_id"] == "test_swarm_001"
    
    # 2 workers should have been executed in parallel
    assert len(result["workers"]) == 2
    for w in result["workers"]:
        assert w["status"] == "success"
        assert w["content"] == "I am a worker"
        
    # The final consensus should come from the critic
    assert result["final_consensus"]["role"] == "critic"
    assert result["final_consensus"]["content"] == "I am a critic"
