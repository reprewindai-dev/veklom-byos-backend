import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone

# Ensure we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.database.database import async_session
from backend.db.models.agent import Agent, Account
from backend.db.models.agent_stack import AgentEvaluation
from backend.apps.api.routers.agent_evaluation import run_agent_evaluation
from sqlalchemy import select

async def main():
    print("Starting Evaluation Trigger...")
    async with async_session() as session:
        # Find an agent to evaluate
        agent_result = await session.execute(select(Agent).limit(1))
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            print("No agents found. Creating a test account and agent...")
            account_result = await session.execute(select(Account).limit(1))
            account = account_result.scalar_one_or_none()
            if not account:
                account = Account(name="Test Account")
                session.add(account)
                await session.commit()
                await session.refresh(account)

            agent = Agent(
                account_id=account.id,
                agent_id="test-agent-" + str(uuid.uuid4())[:8],
                name="Test Agent",
                creator="System",
                jurisdiction="Global",
                declared_purpose="Evaluation Testing",
                status="registered"
            )
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            print(f"Created test agent with ID: {agent.id}")

        print(f"Triggering evaluation for agent: {agent.name} (ID: {agent.id})")
        
        # Create evaluation record
        evaluation_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(agent.id)[:8]}"
        
        config = {
            "type": "batch",
            "metrics": ["success_rate", "avg_latency_ms", "cost_per_execution", "safety_score"]
        }
        
        evaluation = AgentEvaluation(
            id=evaluation_id,
            agent_id=agent.id,
            workspace_id=str(agent.account_id),
            evaluation_type=config["type"],
            evaluation_metrics=config["metrics"],
            baseline_score=0.0,
            overall_score=0.0,
            evaluation_version="1.0"
        )
        
        session.add(evaluation)
        await session.commit()
        
        print(f"Created AgentEvaluation record: {evaluation_id}")
        
    # Run evaluation calculation (run_agent_evaluation will create its own session)
    print("Running background evaluation process...")
    await run_agent_evaluation(evaluation_id, str(agent.id), config, str(agent.account_id))
    
    # Check results
    async with async_session() as session:
        eval_result = await session.execute(
            select(AgentEvaluation).where(AgentEvaluation.id == evaluation_id)
        )
        completed_eval = eval_result.scalar_one()
        
        print(f"\n--- Evaluation Complete ---")
        print(f"Overall Score: {completed_eval.overall_score:.4f}")
        print(f"Metric Scores:")
        for k, v in completed_eval.metric_scores.items():
            print(f"  - {k}: {v:.4f}")
            
        if completed_eval.improvement_suggestions:
            print("\nSuggestions:")
            for s in completed_eval.improvement_suggestions:
                print(f"  - {s}")
        
if __name__ == "__main__":
    asyncio.run(main())
