"""Agent Guardrails and Safety Layer - Layer 6 of AI Agents Stack 2026"""

import json
import asyncio
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Callable
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
import logging

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.agent_stack import (
    Agent, AgentGuardrail, SafetyIncident, AgentExecution, 
    AgentTrace, MCPTool
)

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Guardrails"])
logger = logging.getLogger(__name__)


class GuardrailEngine:
    """Core guardrail engine for enforcing safety policies"""
    
    def __init__(self):
        self.input_filters = []
        self.output_filters = []
        self.tool_guards = []
        self.rate_limiters = {}
    
    async def evaluate_input(
        self, 
        agent_id: str, 
        input_data: Dict[str, Any], 
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Evaluate input against all applicable guardrails using real service"""
        from backend.core.services.guardrail_service import get_guardrail_service
        
        result = {
            "allowed": True,
            "violations": [],
            "modified_data": input_data.copy(),
            "risk_score": 0.0
        }
        
        try:
            # Get active guardrails for this agent
            guardrails_result = await db.execute(
                select(AgentGuardrail).where(
                    and_(
                        AgentGuardrail.agent_id == agent_id,
                        AgentGuardrail.guardrail_type.in_(["input_filter", "rate_limit"]),
                        AgentGuardrail.is_active == True
                    )
                )
            )
            guardrails = guardrails_result.scalars().all()
            
            # Get real guardrail service
            guardrail_service = get_guardrail_service()
            
            # Evaluate with real service
            safety_check = await guardrail_service.evaluate_input_safety(
                input_data, user_id, agent_id, [g.rules for g in guardrails]
            )
            
            if not safety_check.passed:
                result["allowed"] = False
                result["risk_score"] = safety_check.risk_score
                
                # Convert to violation format
                for guardrail in guardrails:
                    result["violations"].append({
                        "guardrail_id": guardrail.id,
                        "guardrail_name": guardrail.name,
                        "severity": guardrail.severity,
                        "reason": safety_check.reason,
                        "action": "block"
                    })
                
                # Apply modifications if any
                if safety_check.modified_data:
                    result["modified_data"] = safety_check.modified_data
            
            # Cap risk score at 1.0
            result["risk_score"] = min(result["risk_score"], 1.0)
            
        except Exception as e:
            logger.error(f"Error evaluating input guardrails: {str(e)}")
            result["allowed"] = False
            result["violations"].append({
                "guardrail_id": "system_error",
                "guardrail_name": "System Error",
                "severity": "error",
                "reason": f"Guardrail evaluation failed: {str(e)}",
                "action": "block"
            })
        
        return result
    
    async def evaluate_output(
        self, 
        agent_id: str, 
        output_data: Dict[str, Any], 
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Evaluate output against all applicable guardrails using real service"""
        from backend.core.services.guardrail_service import get_guardrail_service
        
        result = {
            "allowed": True,
            "violations": [],
            "modified_data": output_data.copy(),
            "risk_score": 0.0
        }
        
        try:
            # Get active output guardrails for this agent
            guardrails_result = await db.execute(
                select(AgentGuardrail).where(
                    and_(
                        AgentGuardrail.agent_id == agent_id,
                        AgentGuardrail.guardrail_type == "output_filter",
                        AgentGuardrail.is_active == True
                    )
                )
            )
            guardrails = guardrails_result.scalars().all()
            
            # Get real guardrail service
            guardrail_service = get_guardrail_service()
            
            # Evaluate with real service
            safety_check = await guardrail_service.evaluate_output_safety(
                output_data, user_id, agent_id, [g.rules for g in guardrails]
            )
            
            if not safety_check.passed:
                result["allowed"] = False
                result["risk_score"] = safety_check.risk_score
                
                # Convert to violation format
                for guardrail in guardrails:
                    result["violations"].append({
                        "guardrail_id": guardrail.id,
                        "guardrail_name": guardrail.name,
                        "severity": guardrail.severity,
                        "reason": safety_check.reason,
                        "action": "block"
                    })
                
                # Apply modifications if any
                if safety_check.modified_data:
                    result["modified_data"] = safety_check.modified_data
            
            # Cap risk score at 1.0
            result["risk_score"] = min(result["risk_score"], 1.0)
            
        except Exception as e:
            logger.error(f"Error evaluating output guardrails: {str(e)}")
            result["allowed"] = False
            result["violations"].append({
                "guardrail_id": "system_error",
                "guardrail_name": "System Error",
                "severity": "error",
                "reason": f"Guardrail evaluation failed: {str(e)}",
                "action": "block"
            })
        
        return result
    
    async def evaluate_tool_call(
        self, 
        agent_id: str, 
        tool_id: str, 
        tool_data: Dict[str, Any], 
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Evaluate tool call against tool guardrails using real service"""
        from backend.core.services.guardrail_service import get_guardrail_service
        
        result = {
            "allowed": True,
            "violations": [],
            "modified_data": tool_data.copy(),
            "risk_score": 0.0
        }
        
        try:
            # Get tool guardrails
            guardrails_result = await db.execute(
                select(AgentGuardrail).where(
                    and_(
                        AgentGuardrail.agent_id == agent_id,
                        AgentGuardrail.guardrail_type == "tool_guard",
                        AgentGuardrail.is_active == True
                    )
                )
            )
            guardrails = guardrails_result.scalars().all()
            
            # Get tool safety level
            tool_result = await db.execute(
                select(MCPTool).where(MCPTool.id == tool_id)
            )
            tool = tool_result.scalar_one_or_none()
            tool_safety_level = tool.safety_level if tool else "safe"
            
            # Get real guardrail service
            guardrail_service = get_guardrail_service()
            
            # Evaluate with real service
            safety_check = await guardrail_service.evaluate_tool_safety(
                tool_id, tool_data, user_id, agent_id, tool_safety_level, [g.rules for g in guardrails], db=db
            )
            
            if not safety_check.passed:
                result["allowed"] = False
                result["risk_score"] = safety_check.risk_score
                
                # Convert to violation format
                for guardrail in guardrails:
                    result["violations"].append({
                        "guardrail_id": guardrail.id,
                        "guardrail_name": guardrail.name,
                        "severity": guardrail.severity,
                        "reason": safety_check.reason,
                        "action": "block",
                        "tool_id": tool_id
                    })
            
            # Cap risk score at 1.0
            result["risk_score"] = min(result["risk_score"], 1.0)
            
        except Exception as e:
            logger.error(f"Error evaluating tool guardrails: {str(e)}")
            result["allowed"] = False
            result["violations"].append({
                "guardrail_id": "system_error",
                "guardrail_name": "System Error",
                "severity": "error",
                "reason": f"Tool guardrail evaluation failed: {str(e)}",
                "action": "block",
                "tool_id": tool_id
            })
        
        return result
    
    async def _evaluate_guardrail(
        self, 
        guardrail: AgentGuardrail, 
        data: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """Evaluate a single guardrail"""
        rules = guardrail.rules
        actions = guardrail.actions
        
        for rule in rules:
            rule_type = rule.get("type")
            
            if rule_type == "content_filter":
                if not self._check_content_filter(data, rule):
                    return {
                        "passed": False,
                        "reason": f"Content filter violation: {rule.get('description', 'Inappropriate content detected')}",
                        "action": actions.get("on_violation", "block")
                    }
            
            elif rule_type == "pattern_match":
                if self._check_pattern_match(data, rule):
                    return {
                        "passed": False,
                        "reason": f"Pattern match violation: {rule.get('description', 'Blocked pattern detected')}",
                        "action": actions.get("on_violation", "block")
                    }
            
            elif rule_type == "data_validation":
                validation_result = self._check_data_validation(data, rule)
                if not validation_result["valid"]:
                    return {
                        "passed": False,
                        "reason": f"Data validation violation: {validation_result['reason']}",
                        "action": actions.get("on_violation", "block"),
                        "modified_data": validation_result.get("modified_data")
                    }
            
            elif rule_type == "rate_limit":
                if not await self._check_rate_limit(user_id, rule):
                    return {
                        "passed": False,
                        "reason": f"Rate limit exceeded: {rule.get('description', 'Too many requests')}",
                        "action": actions.get("on_violation", "block")
                    }
        
        return {"passed": True}
    
    async def _evaluate_tool_guardrail(
        self, 
        guardrail: AgentGuardrail, 
        tool_id: str, 
        tool_data: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """Evaluate a tool-specific guardrail"""
        rules = guardrail.rules
        actions = guardrail.actions
        
        # Check if this tool is specifically blocked
        if rules.get("blocked_tools") and tool_id in rules["blocked_tools"]:
            return {
                "passed": False,
                "reason": f"Tool {tool_id} is explicitly blocked",
                "action": actions.get("on_violation", "block")
            }
        
        # Check tool permissions
        if rules.get("required_permissions"):
            # This would check user permissions against required tool permissions
            # Simplified implementation
            pass
        
        # Check tool parameter validation
        if rules.get("parameter_validation"):
            validation_rules = rules["parameter_validation"]
            for param, rule in validation_rules.items():
                if param in tool_data:
                    if not self._validate_parameter(tool_data[param], rule):
                        return {
                            "passed": False,
                            "reason": f"Parameter {param} validation failed",
                            "action": actions.get("on_violation", "block")
                        }
        
        return {"passed": True}
    
    async def _evaluate_tool_safety(
        self, 
        tool: MCPTool, 
        tool_data: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """Evaluate tool-specific safety"""
        if tool.safety_level == "dangerous":
            # Dangerous tools require admin approval
            # This would check user role and approval status
            return {
                "allowed": False,
                "violation": {
                    "guardrail_id": "tool_safety",
                    "guardrail_name": "Dangerous Tool Protection",
                    "severity": "critical",
                    "reason": f"Tool {tool.name} is classified as dangerous and requires special approval",
                    "action": "block"
                }
            }
        
        elif tool.safety_level == "restricted":
            # Restricted tools need additional validation
            # Check for suspicious patterns in tool data
            suspicious_patterns = [
                r"password",
                r"secret",
                r"token",
                r"key",
                r"\.\./",  # Path traversal
                r"rm\s+-rf",  # Dangerous commands
            ]
            
            data_str = json.dumps(tool_data).lower()
            for pattern in suspicious_patterns:
                if re.search(pattern, data_str):
                    return {
                        "allowed": False,
                        "violation": {
                            "guardrail_id": "tool_safety",
                            "guardrail_name": "Restricted Tool Protection",
                            "severity": "error",
                            "reason": f"Suspicious pattern detected in tool data: {pattern}",
                            "action": "block"
                        }
                    }
        
        return {"allowed": True}
    
    def _check_content_filter(self, data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check content filter rules"""
        blocked_words = rule.get("blocked_words", [])
        content = json.dumps(data).lower()
        
        for word in blocked_words:
            if word.lower() in content:
                return False
        
        return True
    
    def _check_pattern_match(self, data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check pattern matching rules"""
        patterns = rule.get("patterns", [])
        content = json.dumps(data)
        
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _check_data_validation(self, data: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check data validation rules"""
        field = rule.get("field")
        validation_type = rule.get("validation_type")
        
        if field not in data:
            return {"valid": True}
        
        value = data[field]
        
        if validation_type == "string_length":
            min_len = rule.get("min_length", 0)
            max_len = rule.get("max_length", 1000)
            
            if not isinstance(value, str) or len(value) < min_len or len(value) > max_len:
                return {
                    "valid": False,
                    "reason": f"Field {field} must be between {min_len} and {max_len} characters"
                }
        
        elif validation_type == "numeric_range":
            min_val = rule.get("min_value")
            max_val = rule.get("max_value")
            
            try:
                num_val = float(value)
                if min_val is not None and num_val < min_val:
                    return {
                        "valid": False,
                        "reason": f"Field {field} must be at least {min_val}"
                    }
                if max_val is not None and num_val > max_val:
                    return {
                        "valid": False,
                        "reason": f"Field {field} must be at most {max_val}"
                    }
            except (ValueError, TypeError):
                return {
                    "valid": False,
                    "reason": f"Field {field} must be a number"
                }
        
        elif validation_type == "allowed_values":
            allowed = rule.get("allowed_values", [])
            if value not in allowed:
                return {
                    "valid": False,
                    "reason": f"Field {field} must be one of: {', '.join(allowed)}"
                }
        
        return {"valid": True}
    
    async def _check_rate_limit(self, user_id: str, rule: Dict[str, Any]) -> bool:
        """Check rate limiting rules"""
        # This would implement actual rate limiting with Redis or similar
        # Simplified implementation for now
        max_requests = rule.get("max_requests", 100)
        time_window = rule.get("time_window", 3600)  # 1 hour default
        
        # In production, check actual request count from cache
        # For now, always allow
        return True
    
    def _validate_parameter(self, value: Any, rule: Dict[str, Any]) -> bool:
        """Validate individual parameter"""
        param_type = rule.get("type")
        
        if param_type == "string":
            if not isinstance(value, str):
                return False
            min_len = rule.get("min_length", 0)
            max_len = rule.get("max_length", 1000)
            return min_len <= len(value) <= max_len
        
        elif param_type == "number":
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        
        elif param_type == "boolean":
            return isinstance(value, bool)
        
        elif param_type == "array":
            return isinstance(value, list)
        
        return True


# Global guardrail engine instance
guardrail_engine = GuardrailEngine()


@router.post("/{agent_id}/guardrails")
async def create_guardrail(
    agent_id: str,
    guardrail_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new guardrail for an agent"""
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
        
        # Create guardrail
        guardrail_id = f"guard_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{agent_id[:8]}"
        
        guardrail = AgentGuardrail(
            id=guardrail_id,
            agent_id=agent_id,
            workspace_id=user.workspace_id,
            name=guardrail_data.get("name", "Unnamed Guardrail"),
            description=guardrail_data.get("description", ""),
            guardrail_type=guardrail_data.get("guardrail_type", "input_filter"),
            severity=guardrail_data.get("severity", "warning"),
            rules=guardrail_data.get("rules", {}),
            actions=guardrail_data.get("actions", {"on_violation": "block"})
        )
        
        db.add(guardrail)
        await db.commit()
        
        return {
            "guardrail_id": guardrail_id,
            "created": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create guardrail: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create guardrail: {str(e)}")


@router.get("/{agent_id}/guardrails")
async def list_guardrails(
    agent_id: str,
    guardrail_type: str = None,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List guardrails for an agent"""
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
        query = select(AgentGuardrail).where(
            and_(
                AgentGuardrail.agent_id == agent_id,
                AgentGuardrail.workspace_id == user.workspace_id
            )
        )
        
        if guardrail_type:
            query = query.where(AgentGuardrail.guardrail_type == guardrail_type)
        
        result = await db.execute(query)
        guardrails = result.scalars().all()
        
        return {
            "guardrails": [
                {
                    "id": guardrail.id,
                    "name": guardrail.name,
                    "description": guardrail.description,
                    "guardrail_type": guardrail.guardrail_type,
                    "severity": guardrail.severity,
                    "is_active": guardrail.is_active,
                    "trigger_count": guardrail.trigger_count,
                    "last_triggered": guardrail.last_triggered.isoformat() if guardrail.last_triggered else None,
                    "created_at": guardrail.created_at.isoformat()
                }
                for guardrail in guardrails
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list guardrails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list guardrails: {str(e)}")


@router.post("/{agent_id}/guardrails/{guardrail_id}/test")
async def test_guardrail(
    agent_id: str,
    guardrail_id: str,
    test_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test a guardrail with sample data"""
    try:
        # Get guardrail
        guardrail_result = await db.execute(
            select(AgentGuardrail).where(
                and_(
                    AgentGuardrail.id == guardrail_id,
                    AgentGuardrail.agent_id == agent_id,
                    AgentGuardrail.workspace_id == user.workspace_id
                )
            )
        )
        guardrail = guardrail_result.scalar_one_or_none()
        
        if not guardrail:
            raise HTTPException(status_code=404, detail="Guardrail not found")
        
        # Test the guardrail
        evaluation = await guardrail_engine._evaluate_guardrail(
            guardrail, 
            test_data.get("data", {}), 
            user.id
        )
        
        return {
            "guardrail_id": guardrail_id,
            "test_result": evaluation,
            "tested_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test guardrail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test guardrail: {str(e)}")


@router.post("/{agent_id}/evaluate-input")
async def evaluate_agent_input(
    agent_id: str,
    input_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate agent input against guardrails"""
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
        
        # Evaluate input
        result = await guardrail_engine.evaluate_input(agent_id, input_data, user.id, db)
        
        # Log safety incident if blocked
        if not result["allowed"]:
            await log_safety_incident(
                db=db,
                agent_id=agent_id,
                workspace_id=user.workspace_id,
                execution_id=None,
                incident_type="guardrail_violation",
                severity="medium",
                description=f"Input blocked by guardrails: {[v['reason'] for v in result['violations']]}",
                context_data={
                    "input_data": input_data,
                    "violations": result["violations"],
                    "risk_score": result["risk_score"],
                    "user_id": user.id
                }
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to evaluate agent input: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate input: {str(e)}")


@router.post("/{agent_id}/evaluate-output")
async def evaluate_agent_output(
    agent_id: str,
    output_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate agent output against guardrails"""
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
        
        # Evaluate output
        result = await guardrail_engine.evaluate_output(agent_id, output_data, user.id, db)
        
        # Log safety incident if blocked
        if not result["allowed"]:
            await log_safety_incident(
                db=db,
                agent_id=agent_id,
                workspace_id=user.workspace_id,
                execution_id=None,
                incident_type="guardrail_violation",
                severity="medium",
                description=f"Output blocked by guardrails: {[v['reason'] for v in result['violations']]}",
                context_data={
                    "output_data": output_data,
                    "violations": result["violations"],
                    "risk_score": result["risk_score"],
                    "user_id": user.id
                }
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to evaluate agent output: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate output: {str(e)}")


@router.post("/{agent_id}/evaluate-tool-call")
async def evaluate_tool_call(
    agent_id: str,
    tool_call_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate tool call against guardrails"""
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
        
        tool_id = tool_call_data.get("tool_id")
        tool_data = tool_call_data.get("tool_data", {})
        
        if not tool_id:
            raise HTTPException(status_code=400, detail="tool_id is required")
        
        # Evaluate tool call
        result = await guardrail_engine.evaluate_tool_call(agent_id, tool_id, tool_data, user.id, db)
        
        # Log safety incident if blocked
        if not result["allowed"]:
            await log_safety_incident(
                db=db,
                agent_id=agent_id,
                workspace_id=user.workspace_id,
                execution_id=None,
                incident_type="tool_guardrail_violation",
                severity="high",
                description=f"Tool call blocked by guardrails: {[v['reason'] for v in result['violations']]}",
                context_data={
                    "tool_id": tool_id,
                    "tool_data": tool_data,
                    "violations": result["violations"],
                    "risk_score": result["risk_score"],
                    "user_id": user.id
                }
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to evaluate tool call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate tool call: {str(e)}")


@router.get("/{agent_id}/safety-incidents")
async def list_safety_incidents(
    agent_id: str,
    incident_type: str = None,
    severity: str = None,
    limit: int = 50,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List safety incidents for an agent"""
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
        query = select(SafetyIncident).where(
            and_(
                SafetyIncident.agent_id == agent_id,
                SafetyIncident.workspace_id == user.workspace_id
            )
        )
        
        if incident_type:
            query = query.where(SafetyIncident.incident_type == incident_type)
        
        if severity:
            query = query.where(SafetyIncident.severity == severity)
        
        query = query.order_by(desc(SafetyIncident.created_at)).limit(limit)
        
        result = await db.execute(query)
        incidents = result.scalars().all()
        
        return {
            "incidents": [
                {
                    "id": incident.id,
                    "incident_type": incident.incident_type,
                    "severity": incident.severity,
                    "description": incident.description,
                    "detected_by": incident.detected_by,
                    "response_action": incident.response_action,
                    "resolved": incident.resolved,
                    "impact_score": incident.impact_score,
                    "created_at": incident.created_at.isoformat(),
                    "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None
                }
                for incident in incidents
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list safety incidents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list incidents: {str(e)}")


@router.post("/{agent_id}/safety-incidents/{incident_id}/resolve")
async def resolve_safety_incident(
    agent_id: str,
    incident_id: str,
    resolution_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resolve a safety incident"""
    try:
        # Get incident
        incident_result = await db.execute(
            select(SafetyIncident).where(
                and_(
                    SafetyIncident.id == incident_id,
                    SafetyIncident.agent_id == agent_id,
                    SafetyIncident.workspace_id == user.workspace_id
                )
            )
        )
        incident = incident_result.scalar_one_or_none()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Update incident
        incident.resolved = True
        incident.resolved_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return {
            "incident_id": incident_id,
            "resolved": True,
            "resolved_at": incident.resolved_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve safety incident: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resolve incident: {str(e)}")


async def log_safety_incident(
    db: AsyncSession,
    agent_id: str,
    workspace_id: str,
    execution_id: Optional[str],
    incident_type: str,
    severity: str,
    description: str,
    context_data: Dict[str, Any]
):
    """Log a safety incident"""
    try:
        incident = SafetyIncident(
            id=f"incident_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{agent_id[:8]}",
            agent_id=agent_id,
            workspace_id=workspace_id,
            execution_id=execution_id,
            incident_type=incident_type,
            severity=severity,
            description=description,
            context_data=context_data,
            detected_by="guardrail_engine"
        )
        
        db.add(incident)
        await db.commit()
        
        logger.warning(f"Safety incident logged: {incident_type} - {description}")
        
    except Exception as e:
        logger.error(f"Failed to log safety incident: {str(e)}")
        await db.rollback()
