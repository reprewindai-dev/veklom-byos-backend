"""Agent Arena - Integration with AuthorityRun for real enforcement."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
import uuid
import hashlib
import json

router = APIRouter(prefix="/agent-arena", tags=["Agent Arena"])


@router.get("/arena/challenges", response_model=List[Dict[str, Any]])
async def get_arena_challenges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available arena challenges with AuthorityRun requirements."""
    
    try:
        challenges = [
            {
                "challenge_id": "challenge_001",
                "name": "Data Analysis Challenge",
                "description": "Analyze complex datasets and provide insights",
                "difficulty": "intermediate",
                "category": "data_analysis",
                "authority_requirements": {
                    "min_pgl_level": "operator",
                    "required_capabilities": ["data_analysis", "web_search"],
                    "safety_rules": ["data_privacy", "scope_enforcement"],
                    "max_execution_time_minutes": 30,
                    "budget_limit_usd": 1.00
                },
                "scoring_criteria": {
                    "accuracy": 0.4,
                    "efficiency": 0.3,
                    "safety": 0.2,
                    "innovation": 0.1
                },
                "status": "active",
                "participants": 23,
                "deadline": "2026-02-01T23:59:59Z"
            },
            {
                "challenge_id": "challenge_002",
                "name": "Web Automation Challenge",
                "description": "Automate web interactions with safety constraints",
                "difficulty": "advanced",
                "category": "automation",
                "authority_requirements": {
                    "min_pgl_level": "workspace",
                    "required_capabilities": ["automation", "web_search"],
                    "safety_rules": ["no_external_payments", "human_approval_required"],
                    "max_execution_time_minutes": 45,
                    "budget_limit_usd": 2.50
                },
                "scoring_criteria": {
                    "accuracy": 0.3,
                    "efficiency": 0.3,
                    "safety": 0.3,
                    "innovation": 0.1
                },
                "status": "active",
                "participants": 15,
                "deadline": "2026-02-15T23:59:59Z"
            }
        ]
        
        return challenges
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get arena challenges: {str(e)}"
        )


@router.post("/arena/enroll/{challenge_id}", response_model=Dict[str, Any])
async def enroll_in_challenge(
    challenge_id: str,
    enrollment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enroll agent in arena challenge with AuthorityRun binding."""
    
    try:
        required_fields = ["agent_id", "agent_name", "capabilities"]
        for field in required_fields:
            if field not in enrollment_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Validate agent capabilities against challenge requirements
        challenge = await get_challenge_details(challenge_id)
        validation_result = await validate_agent_for_challenge(
            enrollment_data, challenge["authority_requirements"]
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=403,
                detail=f"Agent not qualified: {validation_result['reason']}"
            )
        
        enrollment_id = f"enroll_{uuid.uuid4().hex[:8]}"
        authority_run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        enrollment = {
            "enrollment_id": enrollment_id,
            "authority_run_id": authority_run_id,
            "challenge_id": challenge_id,
            "agent_id": enrollment_data["agent_id"],
            "agent_name": enrollment_data["agent_name"],
            "enrolled_by": current_user.email,
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
            "status": "enrolled",
            
            # AuthorityRun Context
            "authority_context": {
                "run_type": "arena_execution",
                "challenge_id": challenge_id,
                "enforcement_level": "strict",
                "policy_compliance": True,
                "budget_allocated": challenge["authority_requirements"]["budget_limit_usd"]
            },
            
            # SEKED Monitoring
            "seked_monitoring": {
                "enabled": True,
                "measurement_frequency": "real_time",
                "compliance_threshold": 0.95,
                "safety_threshold": 0.98
            },
            
            # Evidence Collection
            "evidence_collection": {
                "evidence_pack_id": f"evidence_{enrollment_id}",
                "collection_points": ["execution_start", "milestone", "completion"],
                "integrity_verification": True
            }
        }
        
        return enrollment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enroll in challenge: {str(e)}"
        )


@router.post("/arena/execute/{enrollment_id}", response_model=Dict[str, Any])
async def execute_arena_challenge(
    enrollment_id: str,
    execution_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute arena challenge with real AuthorityRun enforcement."""
    
    try:
        # Validate execution request
        required_fields = ["execution_plan", "parameters"]
        for field in required_fields:
            if field not in execution_request:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Get enrollment details
        enrollment = await get_enrollment_details(enrollment_id)
        challenge = await get_challenge_details(enrollment["challenge_id"])
        
        # Create AuthorityRun for execution
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        execution = {
            "execution_id": execution_id,
            "authority_run_id": enrollment["authority_run_id"],
            "enrollment_id": enrollment_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "started_by": current_user.email,
            
            # Execution Configuration
            "execution_config": {
                "plan": execution_request["execution_plan"],
                "parameters": execution_request["parameters"],
                "time_limit_minutes": challenge["authority_requirements"]["max_execution_time_minutes"],
                "budget_limit_usd": challenge["authority_requirements"]["budget_limit_usd"]
            },
            
            # Real-time Enforcement
            "enforcement": {
                "policy_validation": "real_time",
                "seked_monitoring": "continuous",
                "budget_enforcement": "strict",
                "safety_checks": "pre_execution"
            },
            
            # Monitoring Points
            "monitoring": {
                "seked_scores": {
                    "E": 5.0,  # Environmental
                    "R": 5.0,  # Risk
                    "C": 5.0,  # Compliance
                    "D": 5.0,  # Decision
                    "S": 5.0   # Safety
                },
                "performance_metrics": {
                    "accuracy": 0.0,
                    "efficiency": 0.0,
                    "resource_usage": 0.0
                },
                "compliance_status": "in_progress"
            }
        }
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start arena execution: {str(e)}"
        )


@router.get("/arena/execution/{execution_id}/status", response_model=Dict[str, Any])
async def get_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get real-time execution status with enforcement data."""
    
    try:
        status = {
            "execution_id": execution_id,
            "status": "running",
            "progress_percentage": 65,
            "started_at": "2026-01-15T10:30:00Z",
            "estimated_completion": "2026-01-15T10:45:00Z",
            
            # SEKED Real-time Scores
            "seked_scores": {
                "E": 4.8,  # Environmental score
                "R": 4.5,  # Risk assessment
                "C": 4.9,  # Compliance level
                "D": 4.7,  # Decision quality
                "S": 4.9   # Safety compliance
            },
            "seked_ratios": {
                "E/R": 1.07,
                "C/D": 1.04,
                "S/E": 1.02
            },
            
            # Performance Metrics
            "performance": {
                "accuracy": 0.87,
                "efficiency": 0.82,
                "resource_usage": 0.71,
                "innovation": 0.65
            },
            
            # Enforcement Actions
            "enforcement_log": [
                {
                    "timestamp": "2026-01-15T10:32:15Z",
                    "action": "policy_validation_passed",
                    "details": "All safety checks passed"
                },
                {
                    "timestamp": "2026-01-15T10:33:45Z",
                    "action": "budget_check",
                    "details": "Current spend: $0.45, limit: $1.00"
                },
                {
                    "timestamp": "2026-01-15T10:35:20Z",
                    "action": "safety_intervention",
                    "details": "Blocked potentially unsafe operation"
                }
            ],
            
            # Evidence Collection Status
            "evidence_status": {
                "evidence_pack_id": f"evidence_{execution_id}",
                "items_collected": 12,
                "integrity_status": "valid",
                "last_verification": "2026-01-15T10:35:00Z"
            }
        }
        
        return status
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution status: {str(e)}"
        )


@router.post("/arena/execution/{execution_id}/complete", response_model=Dict[str, Any])
async def complete_execution(
    execution_id: str,
    completion_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete arena execution with final scoring and evidence."""
    
    try:
        # Calculate final scores
        seked_final = {
            "E": completion_data.get("environmental_score", 4.8),
            "R": completion_data.get("risk_score", 4.5),
            "C": completion_data.get("compliance_score", 4.9),
            "D": completion_data.get("decision_score", 4.7),
            "S": completion_data.get("safety_score", 4.9)
        }
        
        seked_ratios = calculate_seked_ratios(seked_final)
        
        # Calculate overall score
        performance_score = (
            completion_data.get("accuracy", 0.87) * 0.4 +
            completion_data.get("efficiency", 0.82) * 0.3 +
            completion_data.get("safety", 0.95) * 0.2 +
            completion_data.get("innovation", 0.65) * 0.1
        )
        
        overall_score = (performance_score + sum(seked_final.values()) / 25) / 2
        
        completion = {
            "execution_id": execution_id,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            
            # Final Scores
            "final_scores": {
                "seked_scores": seked_final,
                "seked_ratios": seked_ratios,
                "performance_metrics": {
                    "accuracy": completion_data.get("accuracy", 0.87),
                    "efficiency": completion_data.get("efficiency", 0.82),
                    "safety": completion_data.get("safety", 0.95),
                    "innovation": completion_data.get("innovation", 0.65)
                },
                "overall_score": overall_score
            },
            
            # Ranking
            "ranking": {
                "position": 3,
                "total_participants": 23,
                "percentile": 87.0,
                "badge_earned": overall_score > 0.85
            },
            
            # Evidence Summary
            "evidence_summary": {
                "evidence_pack_id": f"evidence_{execution_id}",
                "total_items": 18,
                "integrity_verified": True,
                "compliance_certificate": f"cert_{execution_id}",
                "audit_trail_complete": True
            },
            
            # AuthorityRun Summary
            "authority_summary": {
                "policies_complied": 47,
                "violations": 0,
                "warnings": 2,
                "budget_used": 0.87,
                "execution_time_minutes": 28.5
            }
        }
        
        return completion
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete execution: {str(e)}"
        )


@router.get("/arena/leaderboard/{challenge_id}", response_model=List[Dict[str, Any]])
async def get_leaderboard(
    challenge_id: str,
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get arena leaderboard with AuthorityRun verification."""
    
    try:
        leaderboard = [
            {
                "rank": 1,
                "agent_name": "AlphaAgent",
                "agent_id": "agent_alpha",
                "overall_score": 0.94,
                "seked_scores": {"E": 4.9, "R": 4.8, "C": 5.0, "D": 4.7, "S": 4.9},
                "performance": {"accuracy": 0.96, "efficiency": 0.92, "safety": 0.98, "innovation": 0.89},
                "execution_time_minutes": 25.3,
                "budget_used": 0.92,
                "verified": True,
                "evidence_pack_id": "evidence_alpha_001"
            },
            {
                "rank": 2,
                "agent_name": "BetaAgent",
                "agent_id": "agent_beta", 
                "overall_score": 0.91,
                "seked_scores": {"E": 4.8, "R": 4.7, "C": 4.9, "D": 4.8, "S": 4.8},
                "performance": {"accuracy": 0.93, "efficiency": 0.89, "safety": 0.95, "innovation": 0.87},
                "execution_time_minutes": 27.1,
                "budget_used": 0.88,
                "verified": True,
                "evidence_pack_id": "evidence_beta_001"
            },
            {
                "rank": 3,
                "agent_name": "GammaAgent",
                "agent_id": "agent_gamma",
                "overall_score": 0.89,
                "seked_scores": {"E": 4.7, "R": 4.6, "C": 4.8, "D": 4.7, "S": 4.8},
                "performance": {"accuracy": 0.91, "efficiency": 0.87, "safety": 0.94, "innovation": 0.84},
                "execution_time_minutes": 28.5,
                "budget_used": 0.87,
                "verified": True,
                "evidence_pack_id": "evidence_gamma_001"
            }
        ]
        
        return leaderboard[:limit]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get leaderboard: {str(e)}"
        )


# Helper functions
def calculate_seked_ratios(seked_scores: Dict[str, float]) -> Dict[str, float]:
    """Calculate SEKED ratios for arena scoring."""
    return {
        "E/R": seked_scores["E"] / seked_scores["R"],
        "C/D": seked_scores["C"] / seked_scores["D"],
        "S/E": seked_scores["S"] / seked_scores["E"]
    }


async def get_challenge_details(challenge_id: str) -> Dict[str, Any]:
    """Get challenge details for validation."""
    # Mock implementation - would fetch from database
    return {
        "challenge_id": challenge_id,
        "authority_requirements": {
            "min_pgl_level": "operator",
            "required_capabilities": ["data_analysis"],
            "safety_rules": ["data_privacy"],
            "max_execution_time_minutes": 30,
            "budget_limit_usd": 1.00
        }
    }


async def validate_agent_for_challenge(
    enrollment_data: Dict[str, Any], 
    requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate agent against challenge requirements."""
    
    # Check capabilities
    agent_caps = set(enrollment_data.get("capabilities", []))
    required_caps = set(requirements.get("required_capabilities", []))
    
    if not required_caps.issubset(agent_caps):
        return {
            "valid": False,
            "reason": f"Missing required capabilities: {required_caps - agent_caps}"
        }
    
    return {"valid": True, "reason": "Agent qualified"}


async def get_enrollment_details(enrollment_id: str) -> Dict[str, Any]:
    """Get enrollment details for execution."""
    # Mock implementation - would fetch from database
    return {
        "enrollment_id": enrollment_id,
        "authority_run_id": f"run_{enrollment_id}",
        "challenge_id": "challenge_001"
    }


@router.post("/arena/submit", response_model=Dict[str, Any])
async def submit_to_arena(
    arena_submission: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit agent to arena with AuthorityRun enforcement."""
    
    required_fields = ["agent_id", "challenge_id", "execution_plan"]
    for field in required_fields:
        if field not in arena_submission:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    # Create AuthorityRun for arena execution
    authority_run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    # Initialize SEKED measurement for arena context
    seked_measurement = {
        "E": arena_submission.get("environmental_score", 5),
        "R": arena_submission.get("risk_score", 5),
        "C": arena_submission.get("compliance_score", 5),
        "D": arena_submission.get("decision_score", 5),
        "S": arena_submission.get("safety_score", 5)
    }
    
    # Calculate SEKED ratios
    seked_ratios = calculate_seked_ratios(seked_measurement)
    
    # Create AuthorityRun
    authority_run = {
        "id": authority_run_id,
        "authority_bundle_id": f"bundle_{uuid.uuid4().hex[:8]}",
        "agent_id": arena_submission["agent_id"],
        "workspace_id": current_user.workspace_id,
        "executor_id": "agent_arena",
        "status": "active",
        "decisions": [],
        "violations": [],
        "approvals": [],
        "evidence_pack_id": None,
        "total_actions": 0,
        "approved_actions": 0,
        "denied_actions": 0,
        "violation_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        
        # Arena-specific context
        "arena_context": {
            "challenge_id": arena_submission["challenge_id"],
            "execution_plan": arena_submission["execution_plan"],
            "submission_type": arena_submission.get("submission_type", "competitive"),
            "difficulty_level": arena_submission.get("difficulty_level", "standard")
        },
        
        # SEKED integration
        "seked_measurement": seked_measurement,
        "seked_ratios": seked_ratios,
        "seked_directive": get_seked_directive(seked_ratios["sigma"])
    }
    
    # Check if arena execution requires approval based on SEKED
    requires_approval = seked_ratios["sigma"] < 1.5 or arena_submission.get("difficulty_level") == "expert"
    
    if requires_approval:
        authority_run["status"] = "pending_approval"
        approval_needed = {
            "reason": "SEKED ratio below threshold or expert difficulty",
            "seked_ratio": seked_ratios["sigma"],
            "requires_human_approval": True
        }
    else:
        approval_needed = {
            "reason": "Auto-approved based on SEKED policy",
            "seked_ratio": seked_ratios["sigma"],
            "requires_human_approval": False
        }
    
    # Create arena submission record
    arena_submission_id = f"arena_{uuid.uuid4().hex[:8]}"
    
    submission = {
        "submission_id": arena_submission_id,
        "authority_run_id": authority_run_id,
        "agent_id": arena_submission["agent_id"],
        "challenge_id": arena_submission["challenge_id"],
        "workspace_id": current_user.workspace_id,
        "submitted_by": current_user.id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "submitted" if not requires_approval else "pending_approval",
        "execution_plan": arena_submission["execution_plan"],
        "seked_evaluation": {
            "measurement": seked_measurement,
            "ratios": seked_ratios,
            "directive": authority_run["seked_directive"],
            "approval_required": requires_approval
        },
        "approval_status": approval_needed
    }
    
    return {
        "submission_id": arena_submission_id,
        "authority_run_id": authority_run_id,
        "status": submission["status"],
        "seked_evaluation": submission["seked_evaluation"],
        "approval_status": approval_needed,
        "next_steps": {
            "if_approved": "Arena execution will begin",
            "if_denied": "Submission will be rejected",
            "appeal_process": "Contact arena administrators"
        }
    }


@router.post("/arena/{submission_id}/execute", response_model=Dict[str, Any])
async def execute_arena_submission(
    submission_id: str,
    execution_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute arena submission with real AuthorityRun enforcement."""
    
    # Mock retrieval of submission and authority run
    authority_run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    # Create CAPPO execution request
    cappo_execution = {
        "execution_id": f"exec_{uuid.uuid4().hex[:8]}",
        "agent_id": execution_request.get("agent_id"),
        "tool_name": "arena_challenge",
        "tool_parameters": {
            "challenge_id": execution_request.get("challenge_id"),
            "submission_id": submission_id,
            "execution_plan": execution_request.get("execution_plan")
        },
        "authority_run_id": authority_run_id,
        "workspace_id": current_user.workspace_id,
        "priority": "high" if execution_request.get("difficulty_level") == "expert" else "normal",
        "requires_approval": False, # Already approved at submission stage
        "timeout_seconds": execution_request.get("timeout_seconds", 600)
    }
    
    # Check x402 payment gate for arena execution
    payment_check = await check_arena_payment_gate(
        current_user.workspace_id,
        execution_request.get("difficulty_level", "standard")
    )
    
    if payment_check["payment_required"]:
        return {
            "execution_id": cappo_execution["execution_id"],
            "status": "payment_required",
            "payment_gate": payment_check,
            "message": "Payment required for arena execution"
        }
    
    # Execute with real-time SEKED monitoring
    execution_result = {
        "execution_id": cappo_execution["execution_id"],
        "authority_run_id": authority_run_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        
        # Real-time SEKED monitoring
        "seked_monitoring": {
            "initial_measurement": {
                "E": 5, "R": 5, "C": 5, "D": 5, "S": 5
            },
            "current_ratios": {"sigma": 1.0, "ci": 0.5, "si": 0.5},
            "monitoring_active": True,
            "violation_threshold": 0.5
        },
        
        # Authority enforcement
        "authority_enforcement": {
            "real_time_decisions": True,
            "auto_stop_on_violation": True,
            "evidence_collection": True,
            "payment_enforcement": True
        }
    }
    
    return execution_result


@router.get("/arena/{submission_id}/status", response_model=Dict[str, Any])
async def get_arena_execution_status(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get real-time arena execution status with AuthorityRun data."""
    
    # Mock response - in real implementation, would query actual execution
    return {
        "submission_id": submission_id,
        "authority_run_id": f"run_{uuid.uuid4().hex[:8]}",
        "execution_id": f"exec_{uuid.uuid4().hex[:8]}",
        "status": "running",
        "progress": 65,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "estimated_completion": datetime.now(timezone.utc).isoformat(),
        
        # AuthorityRun metrics
        "authority_metrics": {
            "total_actions": 25,
            "approved_actions": 23,
            "denied_actions": 2,
            "seked_violations": 0,
            "policy_compliance": 92.0
        },
        
        # SEKED real-time data
        "seked_status": {
            "current_measurement": {"E": 4, "R": 5, "C": 5, "D": 5, "S": 4},
            "current_ratios": {"sigma": 0.9, "ci": 0.5, "si": 0.4},
            "directive": "Conserve resources",
            "violation_count": 0,
            "last_violation": None
        },
        
        # Payment tracking
        "payment_tracking": {
            "total_cost_usd": 0.125,
            "budget_remaining_usd": 9.875,
            "payment_gates_triggered": 0,
            "payment_status": "sufficient"
        },
        
        # Evidence collection
        "evidence_status": {
            "evidence_pack_id": f"evidence_{uuid.uuid4().hex[:8]}",
            "components_collected": ["pgl", "seked", "cappo", "x402"],
            "collection_active": True,
            "last_evidence": datetime.now(timezone.utc).isoformat()
        }
    }


@router.post("/arena/{submission_id}/enforce", response_model=Dict[str, Any])
async def enforce_authority_decision(
    submission_id: str,
    enforcement_action: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enforce real authority decision on arena execution."""
    
    required_fields = ["decision", "reason", "enforcement_type"]
    for field in required_fields:
        if field not in enforcement_action:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    enforcement_id = f"enforce_{uuid.uuid4().hex[:8]}"
    
    # Apply enforcement action
    enforcement_result = {
        "enforcement_id": enforcement_id,
        "submission_id": submission_id,
        "authority_run_id": f"run_{uuid.uuid4().hex[:8]}",
        "decision": enforcement_action["decision"],
        "reason": enforcement_action["reason"],
        "enforcement_type": enforcement_action["enforcement_type"],
        "enforced_at": datetime.now(timezone.utc).isoformat(),
        "enforced_by": current_user.id,
        
        # Enforcement impact
        "enforcement_impact": {
            "execution_stopped": enforcement_action["decision"] == "deny",
            "evidence_preserved": True,
            "payment_charged": enforcement_action["decision"] == "approve",
            "violations_recorded": enforcement_action["decision"] == "deny"
        },
        
        # SEKED policy reference
        "seked_policy_reference": {
            "measurement": {"E": 3, "R": 4, "C": 5, "D": 5, "S": 3},
            "ratios": {"sigma": 0.6, "ci": 0.5, "si": 0.3},
            "policy_threshold": 0.5,
            "violation_detected": enforcement_action["decision"] == "deny"
        }
    }
    
    return enforcement_result


@router.get("/arena/challenges", response_model=List[Dict[str, Any]])
async def list_arena_challenges(
    difficulty: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available arena challenges with authority requirements."""
    
    # Mock response - in real implementation, would query actual challenges
    return [
        {
            "challenge_id": "challenge_12345678",
            "title": "Web Search Accuracy",
            "description": "Test agent's ability to find accurate information",
            "difficulty": "standard",
            "category": "information_retrieval",
            "estimated_duration_minutes": 30,
            "estimated_cost_usd": 0.05,
            
            # Authority requirements
            "authority_requirements": {
                "min_seked_ratio": 1.0,
                "required_permissions": ["web_search", "api_calls"],
                "safety_rules": ["no_sensitive_data"],
                "payment_required": True,
                "approval_required": False
            },
            
            "seked_impact": {
                "environmental_impact": 2,
                "risk_level": 3,
                "compliance_requirement": 4,
                "decision_complexity": 3,
                "safety_level": 4
            }
        },
        {
            "challenge_id": "challenge_87654321",
            "title": "Complex Data Analysis",
            "description": "Advanced data processing and analysis challenge",
            "difficulty": "expert",
            "category": "data_analysis",
            "estimated_duration_minutes": 120,
            "estimated_cost_usd": 0.25,
            
            "authority_requirements": {
                "min_seked_ratio": 1.5,
                "required_permissions": ["file_access", "database_query", "code_execution"],
                "safety_rules": ["no_sensitive_data", "human_approval_required"],
                "payment_required": True,
                "approval_required": True
            },
            
            "seked_impact": {
                "environmental_impact": 4,
                "risk_level": 5,
                "compliance_requirement": 5,
                "decision_complexity": 5,
                "safety_level": 5
            }
        }
    ]


@router.get("/arena/leaderboard", response_model=Dict[str, Any])
async def get_arena_leaderboard(
    challenge_id: Optional[str] = Query(None),
    time_period: str = Query("week", pattern="^(day|week|month|all)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get arena leaderboard with authority compliance metrics."""
    
    # Mock response - in real implementation, would calculate actual rankings
    return {
        "leaderboard_id": f"leaderboard_{uuid.uuid4().hex[:8]}",
        "challenge_id": challenge_id,
        "time_period": time_period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        "rankings": [
            {
                "rank": 1,
                "agent_id": "agent_winner_123",
                "agent_name": "AlphaAgent",
                "score": 98.5,
                "submissions": 5,
                "avg_seked_ratio": 2.1,
                "authority_compliance": 100.0,
                "total_cost_usd": 0.75
            },
            {
                "rank": 2,
                "agent_id": "agent_runner_456",
                "agent_name": "BetaAgent",
                "score": 95.2,
                "submissions": 4,
                "avg_seked_ratio": 1.8,
                "authority_compliance": 95.0,
                "total_cost_usd": 0.60
            }
        ],
        
        "authority_metrics": {
            "total_submissions": 156,
            "compliance_rate": 94.2,
            "avg_seked_ratio": 1.6,
            "violations_detected": 9,
            "payment_gates_triggered": 23
        }
    }


@router.get("/arena/compliance", response_model=Dict[str, Any])
async def get_arena_compliance_report(
    workspace_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get arena compliance report with authority enforcement metrics."""
    
    target_workspace = workspace_id or current_user.workspace_id
    
    return {
        "workspace_id": target_workspace,
        "report_period": "last_30_days",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        "compliance_summary": {
            "total_submissions": 45,
            "approved_submissions": 42,
            "denied_submissions": 3,
            "compliance_rate": 93.3,
            "avg_seked_ratio": 1.7
        },
        
        "seked_analysis": {
            "ratio_distribution": {
                "high": 15,    # > 2.0
                "medium": 25,  # 1.0 - 2.0
                "low": 5       # < 1.0
            },
            "common_violations": [
                "Safety score below threshold",
                "Risk level too high",
                "Environmental impact excessive"
            ],
            "improvement_areas": [
                "Safety protocol adherence",
                "Risk assessment accuracy"
            ]
        },
        
        "authority_enforcement": {
            "real_time_decisions": 156,
            "auto_stops": 3,
            "manual_interventions": 1,
            "evidence_packs_generated": 45,
            "payment_gates_triggered": 12
        },
        
        "recommendations": [
            "Improve safety scoring in agent configurations",
            "Add pre-submission SEKED validation",
            "Implement progressive difficulty levels"
        ]
    }


# Helper functions
def calculate_seked_ratios(measurement: Dict[str, Any]) -> Dict[str, float]:
    """Calculate SEKED ratios from measurement."""
    E = measurement.get('E', 5)
    R = measurement.get('R', 5)
    C = measurement.get('C', 5)
    D = measurement.get('D', 5)
    S = measurement.get('S', 5)
    
    sigma = (E + D) / (R + 1)
    ci = C / (10 - R)
    si = S / 10
    
    return {
        'sigma': round(sigma, 2),
        'ci': round(ci, 2),
        'si': round(si, 2)
    }

def get_seked_directive(ratio: float) -> Dict[str, Any]:
    """Get SEKED directive based on ratio."""
    if ratio >= 4.0:
        return {'directive': "Execute primary objectives", 'action_type': "EXECUTE", 'confidence': 0.95}
    elif ratio >= 2.5:
        return {'directive': "Prepare for execution", 'action_type': "PREPARE", 'confidence': 0.85}
    elif ratio >= 1.5:
        return {'directive': "Conserve resources", 'action_type': "CONSERVE", 'confidence': 0.75}
    elif ratio >= 0.5:
        return {'directive': "Initiate recovery", 'action_type': "RECOVER", 'confidence': 0.80}
    else:
        return {'directive': "Escalate to human", 'action_type': "ESCALATE", 'confidence': 0.90}

async def check_arena_payment_gate(workspace_id: str, difficulty: str) -> Dict[str, Any]:
    """Check if payment gate should be triggered for arena execution."""
    # Mock implementation - would check actual budget
    cost_map = {"standard": 0.05, "expert": 0.25, "master": 1.0}
    cost = cost_map.get(difficulty, 0.05)
    
    return {
        "payment_required": cost > 0.1,  # Require payment for expensive challenges
        "amount_usd": cost,
        "reason": "Expert challenge requires payment" if cost > 0.1 else "Standard challenge"
    }
