"""Agent Evaluation and Observability Layer - Layer 5 of AI Agents Stack 2026"""

import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, case
import numpy as np
import pandas as pd
from dataclasses import dataclass
import logging

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.agent_stack import (
    Agent, AgentExecution, AgentEvaluation, AgentTrace, 
    SafetyIncident, AgentMemory, ConversationContext
)

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Evaluation"])
logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetric:
    """Definition of an evaluation metric"""
    name: str
    description: str
    metric_type: str  # accuracy, latency, cost, safety, custom
    target_value: Optional[float] = None
    weight: float = 1.0


# Standard evaluation metrics for agents
STANDARD_METRICS = [
    EvaluationMetric(
        name="success_rate",
        description="Percentage of successful agent executions",
        metric_type="accuracy",
        target_value=0.95,
        weight=0.3
    ),
    EvaluationMetric(
        name="avg_latency_ms",
        description="Average execution time in milliseconds",
        metric_type="latency",
        target_value=5000.0,
        weight=0.2
    ),
    EvaluationMetric(
        name="cost_per_execution",
        description="Average cost per execution in USD",
        metric_type="cost",
        target_value=0.10,
        weight=0.2
    ),
    EvaluationMetric(
        name="safety_score",
        description="Safety and compliance score",
        metric_type="safety",
        target_value=0.98,
        weight=0.3
    )
]


@router.post("/{agent_id}/evaluate")
async def evaluate_agent(
    agent_id: str,
    evaluation_config: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start an agent evaluation"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Create evaluation record
        evaluation_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{agent_id[:8]}"
        
        evaluation = AgentEvaluation(
            id=evaluation_id,
            agent_id=agent_id,
            workspace_id=user.workspace_id,
            evaluation_type=evaluation_config.get("type", "offline"),
            evaluation_metrics=evaluation_config.get("metrics", [m.name for m in STANDARD_METRICS]),
            baseline_score=agent.success_rate,
            overall_score=0.0,  # Will be updated after evaluation
            evaluation_version="1.0"
        )
        
        db.add(evaluation)
        await db.commit()
        
        # Start evaluation in background
        if evaluation_config.get("async", True):
            background_tasks.add_task(
                run_agent_evaluation,
                evaluation_id,
                agent_id,
                evaluation_config,
                user.workspace_id
            )
            
            return {
                "evaluation_id": evaluation_id,
                "status": "started",
                "message": "Evaluation started in background"
            }
        else:
            # Run synchronously
            results = await run_agent_evaluation(
                evaluation_id, agent_id, evaluation_config, user.workspace_id
            )
            
            return {
                "evaluation_id": evaluation_id,
                "status": "completed",
                "results": results
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start agent evaluation: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start evaluation: {str(e)}")


@router.get("/{agent_id}/evaluations")
async def list_agent_evaluations(
    agent_id: str,
    evaluation_type: str = None,
    limit: int = 50,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List evaluations for an agent"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Build query
        query = select(AgentEvaluation).where(
            and_(
                AgentEvaluation.agent_id == agent_id,
                AgentEvaluation.workspace_id == user.workspace_id
            )
        )
        
        if evaluation_type:
            query = query.where(AgentEvaluation.evaluation_type == evaluation_type)
        
        query = query.order_by(desc(AgentEvaluation.evaluated_at)).limit(limit)
        
        result = await db.execute(query)
        evaluations = result.scalars().all()
        
        return {
            "evaluations": [
                {
                    "id": eval.id,
                    "evaluation_type": eval.evaluation_type,
                    "overall_score": eval.overall_score,
                    "metric_scores": eval.metric_scores,
                    "baseline_score": eval.baseline_score,
                    "evaluated_at": eval.evaluated_at.isoformat(),
                    "evaluation_version": eval.evaluation_version
                }
                for eval in evaluations
            ],
            "total_count": len(evaluations)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list agent evaluations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list evaluations: {str(e)}")


@router.get("/{agent_id}/evaluations/{evaluation_id}")
async def get_evaluation_details(
    agent_id: str,
    evaluation_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed evaluation results"""
    try:
        evaluation_result = await db.execute(
            select(AgentEvaluation).where(
                and_(
                    AgentEvaluation.id == evaluation_id,
                    AgentEvaluation.agent_id == agent_id,
                    AgentEvaluation.workspace_id == user.workspace_id
                )
            )
        )
        evaluation = evaluation_result.scalar_one_or_none()
        
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        return {
            "id": evaluation.id,
            "evaluation_type": evaluation.evaluation_type,
            "test_dataset": evaluation.test_dataset,
            "evaluation_metrics": evaluation.evaluation_metrics,
            "baseline_score": evaluation.baseline_score,
            "overall_score": evaluation.overall_score,
            "metric_scores": evaluation.metric_scores,
            "detailed_results": evaluation.detailed_results,
            "failure_cases": evaluation.failure_cases,
            "improvement_suggestions": evaluation.improvement_suggestions,
            "evaluated_at": evaluation.evaluated_at.isoformat(),
            "evaluation_version": evaluation.evaluation_version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evaluation details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get evaluation: {str(e)}")


@router.get("/{agent_id}/observability/dashboard")
async def get_observability_dashboard(
    agent_id: str,
    time_range: str = "24h",  # 1h, 24h, 7d, 30d
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get observability dashboard data for an agent"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Calculate time range
        time_delta = parse_time_range(time_range)
        start_time = datetime.now(timezone.utc) - time_delta
        
        # Get execution metrics
        execution_stats = await get_execution_statistics(agent_id, user.workspace_id, start_time, db)
        
        # Get safety incidents
        safety_stats = await get_safety_statistics(agent_id, user.workspace_id, start_time, db)
        
        # Get performance trends
        performance_trends = await get_performance_trends(agent_id, user.workspace_id, start_time, db)
        
        # Get tool usage statistics
        tool_usage = await get_tool_usage_statistics(agent_id, user.workspace_id, start_time, db)
        
        # Get memory usage
        memory_stats = await get_memory_usage_statistics(agent_id, user.workspace_id, db)
        
        return {
            "agent_id": agent_id,
            "time_range": time_range,
            "execution_stats": execution_stats,
            "safety_stats": safety_stats,
            "performance_trends": performance_trends,
            "tool_usage": tool_usage,
            "memory_stats": memory_stats,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get observability dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/{agent_id}/traces")
async def get_agent_traces(
    agent_id: str,
    trace_type: str = None,
    execution_id: str = None,
    limit: int = 100,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution traces for an agent"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Build query
        query = select(AgentTrace).where(
            and_(
                AgentTrace.agent_id == agent_id,
                AgentTrace.workspace_id == user.workspace_id
            )
        )
        
        if trace_type:
            query = query.where(AgentTrace.trace_type == trace_type)
        
        if execution_id:
            query = query.where(AgentTrace.execution_id == execution_id)
        
        query = query.order_by(desc(AgentTrace.timestamp)).limit(limit)
        
        result = await db.execute(query)
        traces = result.scalars().all()
        
        return {
            "traces": [
                {
                    "id": trace.id,
                    "execution_id": trace.execution_id,
                    "trace_type": trace.trace_type,
                    "timestamp": trace.timestamp.isoformat(),
                    "duration_ms": trace.duration_ms,
                    "success": trace.success,
                    "input_data": trace.input_data,
                    "output_data": trace.output_data,
                    "metadata": trace.metadata,
                    "error_message": trace.error_message
                }
                for trace in traces
            ],
            "total_count": len(traces)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent traces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get traces: {str(e)}")


@router.post("/{agent_id}/traces/{trace_id}/analyze")
async def analyze_trace(
    agent_id: str,
    trace_id: str,
    analysis_config: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze a specific trace for performance and safety issues"""
    try:
        # Get trace
        trace_result = await db.execute(
            select(AgentTrace).where(
                and_(
                    AgentTrace.id == trace_id,
                    AgentTrace.agent_id == agent_id,
                    AgentTrace.workspace_id == user.workspace_id
                )
            )
        )
        trace = trace_result.scalar_one_or_none()
        
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        # Perform trace analysis
        analysis = await analyze_trace_performance(trace, analysis_config)
        
        return {
            "trace_id": trace_id,
            "analysis": analysis,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze trace: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze trace: {str(e)}")


# Background evaluation task
async def run_agent_evaluation(
    evaluation_id: str,
    agent_id: str,
    config: Dict[str, Any],
    workspace_id: str
):
    """Run agent evaluation in background"""
    from backend.core.database.database import get_db_context
    
    async with get_db_context() as db:
        try:
            # Get evaluation metrics
            metrics = config.get("metrics", [m.name for m in STANDARD_METRICS])
            
            # Calculate each metric
            metric_scores = {}
            detailed_results = {}
            
            for metric_name in metrics:
                if metric_name == "success_rate":
                    score, details = await evaluate_success_rate(agent_id, workspace_id, db)
                elif metric_name == "avg_latency_ms":
                    score, details = await evaluate_latency(agent_id, workspace_id, db)
                elif metric_name == "cost_per_execution":
                    score, details = await evaluate_cost(agent_id, workspace_id, db)
                elif metric_name == "safety_score":
                    score, details = await evaluate_safety(agent_id, workspace_id, db)
                else:
                    score, details = await evaluate_custom_metric(agent_id, workspace_id, metric_name, db)
                
                metric_scores[metric_name] = score
                detailed_results[metric_name] = details
            
            # Calculate overall score (weighted average)
            overall_score = calculate_overall_score(metric_scores, metrics)
            
            # Generate improvement suggestions
            improvement_suggestions = generate_improvement_suggestions(metric_scores, detailed_results)
            
            # Update evaluation record
            eval_result = await db.execute(
                select(AgentEvaluation).where(AgentEvaluation.id == evaluation_id)
            )
            evaluation = eval_result.scalar_one()
            
            evaluation.overall_score = overall_score
            evaluation.metric_scores = metric_scores
            evaluation.detailed_results = detailed_results
            evaluation.improvement_suggestions = improvement_suggestions
            evaluation.evaluated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Completed evaluation {evaluation_id} for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Background evaluation failed: {str(e)}")
            await db.rollback()


# Real evaluation metric functions using the evaluation service
async def evaluate_success_rate(agent_id: str, workspace_id: str, db: AsyncSession) -> tuple[float, Dict[str, Any]]:
    """Evaluate agent success rate using real service"""
    from backend.core.services.evaluation_service import get_evaluation_service
    
    service = get_evaluation_service()
    return await service.evaluate_success_rate(agent_id, workspace_id, db)


async def evaluate_latency(agent_id: str, workspace_id: str, db: AsyncSession) -> tuple[float, Dict[str, Any]]:
    """Evaluate agent latency performance using real service"""
    from backend.core.services.evaluation_service import get_evaluation_service
    
    service = get_evaluation_service()
    return await service.evaluate_latency(agent_id, workspace_id, db)


async def evaluate_cost(agent_id: str, workspace_id: str, db: AsyncSession) -> tuple[float, Dict[str, Any]]:
    """Evaluate agent cost efficiency using real service"""
    from backend.core.services.evaluation_service import get_evaluation_service
    
    service = get_evaluation_service()
    return await service.evaluate_cost(agent_id, workspace_id, db)


async def evaluate_safety(agent_id: str, workspace_id: str, db: AsyncSession) -> tuple[float, Dict[str, Any]]:
    """Evaluate agent safety and compliance using real service"""
    from backend.core.services.evaluation_service import get_evaluation_service
    
    service = get_evaluation_service()
    return await service.evaluate_safety(agent_id, workspace_id, db)


async def evaluate_custom_metric(agent_id: str, workspace_id: str, metric_name: str, db: AsyncSession) -> tuple[float, Dict[str, Any]]:
    """Evaluate a custom metric using real service"""
    from backend.core.services.evaluation_service import get_evaluation_service
    
    service = get_evaluation_service()
    return await service.evaluate_custom_metric(agent_id, workspace_id, metric_name, db)


def calculate_overall_score(metric_scores: Dict[str, float], metrics: List[str]) -> float:
    """Calculate overall evaluation score using real service"""
    from backend.core.services.evaluation_service import get_evaluation_service
    
    service = get_evaluation_service()
    return service.calculate_overall_score(metric_scores, metrics)


def generate_improvement_suggestions(metric_scores: Dict[str, float], detailed_results: Dict[str, Any]) -> List[str]:
    """Generate improvement suggestions using real service"""
    from backend.core.services.evaluation_service import get_evaluation_service
    
    service = get_evaluation_service()
    return service.generate_improvement_suggestions(metric_scores, detailed_results)


# Observability helper functions
async def get_execution_statistics(agent_id: str, workspace_id: str, start_time: datetime, db: AsyncSession) -> Dict[str, Any]:
    """Get execution statistics for observability"""
    result = await db.execute(
        select(
            func.count(AgentExecution.id).label("total_executions"),
            func.sum(case((AgentExecution.status == "completed", 1), else_=0)).label("successful_executions"),
            func.avg(AgentExecution.duration_ms).label("avg_duration"),
            func.sum(AgentExecution.cost_estimate).label("total_cost"),
            func.sum(AgentExecution.tokens_used).label("total_tokens")
        ).where(
            and_(
                AgentExecution.agent_id == agent_id,
                AgentExecution.workspace_id == workspace_id,
                AgentExecution.created_at >= start_time
            )
        )
    )
    stats = result.first()
    
    total = stats.total_executions or 0
    successful = stats.successful_executions or 0
    
    return {
        "total_executions": total,
        "successful_executions": successful,
        "success_rate": successful / total if total > 0 else 0,
        "avg_duration_ms": stats.avg_duration or 0,
        "total_cost": stats.total_cost or 0,
        "total_tokens": stats.total_tokens or 0
    }


async def get_safety_statistics(agent_id: str, workspace_id: str, start_time: datetime, db: AsyncSession) -> Dict[str, Any]:
    """Get safety statistics for observability"""
    result = await db.execute(
        select(
            func.count(SafetyIncident.id).label("total_incidents"),
            SafetyIncident.severity,
            func.count(SafetyIncident.id).label("count")
        ).where(
            and_(
                SafetyIncident.agent_id == agent_id,
                SafetyIncident.workspace_id == workspace_id,
                SafetyIncident.created_at >= start_time
            )
        ).group_by(SafetyIncident.severity)
    )
    
    incidents_by_severity = {row.severity: row.count for row in result}
    total_incidents = sum(incidents_by_severity.values())
    
    return {
        "total_incidents": total_incidents,
        "incidents_by_severity": incidents_by_severity,
        "resolved_incidents": 0  # Would need to track resolution status
    }


async def get_performance_trends(agent_id: str, workspace_id: str, start_time: datetime, db: AsyncSession) -> Dict[str, Any]:
    """Get performance trends over time"""
    # Group by hour for trend analysis
    result = await db.execute(
        select(
            func.date_trunc('hour', AgentExecution.created_at).label("hour"),
            func.count(AgentExecution.id).label("executions"),
            func.avg(AgentExecution.duration_ms).label("avg_duration"),
            func.sum(case((AgentExecution.status == "completed", 1), else_=0)).label("successful")
        ).where(
            and_(
                AgentExecution.agent_id == agent_id,
                AgentExecution.workspace_id == workspace_id,
                AgentExecution.created_at >= start_time
            )
        ).group_by(func.date_trunc('hour', AgentExecution.created_at))
        .order_by(func.date_trunc('hour', AgentExecution.created_at))
    )
    
    trends = []
    for row in result:
        trends.append({
            "timestamp": row.hour.isoformat(),
            "executions": row.executions,
            "avg_duration_ms": float(row.avg_duration) if row.avg_duration else 0,
            "success_rate": row.successful / row.executions if row.executions > 0 else 0
        })
    
    return {"trends": trends}


async def get_tool_usage_statistics(agent_id: str, workspace_id: str, start_time: datetime, db: AsyncSession) -> Dict[str, Any]:
    """Get tool usage statistics"""
    # This would require analyzing trace data for tool calls
    # Placeholder implementation
    return {
        "total_tool_calls": 0,
        "tools_used": [],
        "most_used_tool": None
    }


async def get_memory_usage_statistics(agent_id: str, workspace_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Get memory usage statistics"""
    result = await db.execute(
        select(
            func.count(AgentMemory.id).label("total_memories"),
            func.count(func.distinct(AgentMemory.memory_type)).label("memory_types"),
            func.avg(AgentMemory.access_count).label("avg_access_count")
        ).where(
            and_(
                AgentMemory.agent_id == agent_id,
                AgentMemory.workspace_id == workspace_id
            )
        )
    )
    stats = result.first()
    
    return {
        "total_memories": stats.total_memories or 0,
        "memory_types": stats.memory_types or 0,
        "avg_access_count": float(stats.avg_access_count) if stats.avg_access_count else 0
    }


async def analyze_trace_performance(trace: AgentTrace, config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a specific trace for performance issues"""
    analysis = {
        "performance_issues": [],
        "safety_concerns": [],
        "optimization_suggestions": []
    }
    
    # Check for performance issues
    if trace.duration_ms and trace.duration_ms > 10000:  # 10 seconds
        analysis["performance_issues"].append({
            "type": "high_latency",
            "description": f"Execution took {trace.duration_ms}ms, which exceeds typical thresholds",
            "severity": "medium"
        })
    
    # Check for safety concerns
    if not trace.success and trace.error_message:
        analysis["safety_concerns"].append({
            "type": "execution_failure",
            "description": f"Execution failed: {trace.error_message}",
            "severity": "high"
        })
    
    # Generate optimization suggestions
    if trace.trace_type == "tool_call" and trace.duration_ms and trace.duration_ms > 5000:
        analysis["optimization_suggestions"].append(
            "Consider optimizing tool call performance or adding caching"
        )
    
    return analysis


def parse_time_range(time_range: str) -> timedelta:
    """Parse time range string into timedelta"""
    if time_range == "1h":
        return timedelta(hours=1)
    elif time_range == "24h":
        return timedelta(days=1)
    elif time_range == "7d":
        return timedelta(days=7)
    elif time_range == "30d":
        return timedelta(days=30)
    else:
        return timedelta(days=1)  # Default to 24 hours
