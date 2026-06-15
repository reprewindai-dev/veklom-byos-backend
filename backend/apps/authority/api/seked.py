"""SEKED API endpoints integrated with Veklom Authority system."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional

from backend.core.security.auth import get_current_user
from backend.core.database.database import get_db
from backend.core.services.seked_service import seked_service
from backend.db.models.authority import AuthorityDecision, AuthorityRun
from backend.db.models.user import User

router = APIRouter(prefix="/seked", tags=["SEKED"])


@router.post("/calculate")
async def calculate_seked_ratios(
    measurement: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Calculate SEKED ratios from measurement.
    
    Args:
        measurement: Dict with E, R, C, D, S values (0-9)
        
    Returns:
        SEKED ratios dict
    """
    # Validate measurement
    required_keys = ['E', 'R', 'C', 'D', 'S']
    for key in required_keys:
        if key not in measurement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required measurement key: {key}"
            )
        if not isinstance(measurement[key], (int, float)) or measurement[key] < 0 or measurement[key] > 9:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Measurement {key} must be a number between 0 and 9"
            )
    
    ratios = seked_service.calculate_seked_ratios(measurement)
    return ratios


@router.get("/directive/{ratio}")
async def get_seked_directive(
    ratio: float,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get SEKED directive for a ratio.
    
    Args:
        ratio: Sigma ratio value
        
    Returns:
        SEKED directive dict
    """
    if ratio < 0 or ratio > 18:  # Max possible sigma is (9+9)/(0+1) = 18
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ratio must be between 0 and 18"
        )
    
    directive = seked_service.get_seked_directive(ratio)
    return directive


@router.post("/state")
async def create_seked_state(
    measurement: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create complete SEKED state from measurement.
    
    Args:
        measurement: SEKED measurement dict
        
    Returns:
        Complete SEKED state
    """
    # Validate measurement
    required_keys = ['E', 'R', 'C', 'D', 'S']
    for key in required_keys:
        if key not in measurement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required measurement key: {key}"
            )
        if not isinstance(measurement[key], (int, float)) or measurement[key] < 0 or measurement[key] > 9:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Measurement {key} must be a number between 0 and 9"
            )
    
    seked_state = seked_service.create_seked_state(measurement)
    return seked_state


@router.post("/verify")
async def verify_seked_state(
    state: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Verify SEKED state fingerprint.
    
    Args:
        state: SEKED state to verify
        
    Returns:
        Verification result
    """
    expected_fingerprint = seked_service.create_seked_fingerprint(state)
    provided_fingerprint = state.get('fingerprint', '')
    
    is_valid = expected_fingerprint == provided_fingerprint
    
    return {
        'valid': is_valid,
        'expected_fingerprint': expected_fingerprint,
        'provided_fingerprint': provided_fingerprint
    }


@router.post("/authority-decisions/{decision_id}/apply")
async def apply_seked_to_authority_decision(
    decision_id: str,
    measurement: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Apply SEKED decision to existing authority decision.
    
    Args:
        decision_id: Authority decision ID
        measurement: Optional SEKED measurement
        
    Returns:
        Updated authority decision
    """
    authority_decision = db.query(AuthorityDecision).filter(
        AuthorityDecision.id == decision_id
    ).first()
    
    if not authority_decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority decision not found"
        )
    
    # Check workspace access
    if authority_decision.authority_run.workspace_id != current_user.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Apply SEKED decision
    updated_decision = seked_service.apply_seked_decision(
        authority_decision, measurement
    )
    
    db.commit()
    db.refresh(updated_decision)
    
    return {
        'id': updated_decision.id,
        'decision': updated_decision.decision,
        'reason': updated_decision.reason,
        'confidence_score': updated_decision.confidence_score,
        'seked_measurement': updated_decision.seked_measurement,
        'seked_ratios': updated_decision.seked_ratios,
        'seked_directive': updated_decision.seked_directive
    }


@router.post("/authority-runs/{run_id}/initialize")
async def initialize_authority_run_with_seked(
    run_id: str,
    initial_measurement: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Initialize AuthorityRun with SEKED state.
    
    Args:
        run_id: Authority run ID
        initial_measurement: Optional initial SEKED measurement
        
    Returns:
        Updated authority run
    """
    authority_run = db.query(AuthorityRun).filter(
        AuthorityRun.id == run_id
    ).first()
    
    if not authority_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority run not found"
        )
    
    # Check workspace access
    if authority_run.workspace_id != current_user.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Initialize with SEKED
    updated_run = seked_service.initialize_authority_run_with_seked(
        authority_run, initial_measurement
    )
    
    db.commit()
    db.refresh(updated_run)
    
    return {
        'id': updated_run.id,
        'status': updated_run.status,
        'seked_initial_measurement': updated_run.seked_initial_measurement,
        'seked_final_directive': updated_run.seked_final_directive
    }


@router.get("/health")
async def get_seked_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get SEKED service health status.
    
    Returns:
        Health status dict
    """
    return seked_service.get_seked_health_status()


@router.get("/agent/{agent_id}/current-state")
async def get_agent_seked_state(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current SEKED state for an agent.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Current SEKED state
    """
    # Get the most recent authority decision for this agent
    latest_decision = db.query(AuthorityDecision).join(AuthorityRun).filter(
        AuthorityRun.agent_id == agent_id,
        AuthorityRun.workspace_id == current_user.workspace_id
    ).order_by(AuthorityDecision.decision_time.desc()).first()
    
    if not latest_decision or not latest_decision.seked_measurement:
        # Return default state
        default_measurement = {'E': 5, 'R': 5, 'C': 5, 'D': 5, 'S': 5}
        seked_state = seked_service.create_seked_state(default_measurement)
        return seked_state
    
    return {
        'measurement': latest_decision.seked_measurement,
        'ratios': latest_decision.seked_ratios,
        'directive': latest_decision.seked_directive,
        'timestamp': latest_decision.decision_time.isoformat()
    }


@router.post("/agent/{agent_id}/update-state")
async def update_agent_seked_state(
    agent_id: str,
    measurement: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update agent SEKED state and create authority decision.
    
    Args:
        agent_id: Agent ID
        measurement: New SEKED measurement
        
    Returns:
        Updated SEKED state and authority decision
    """
    # Validate measurement
    required_keys = ['E', 'R', 'C', 'D', 'S']
    for key in required_keys:
        if key not in measurement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required measurement key: {key}"
            )
        if not isinstance(measurement[key], (int, float)) or measurement[key] < 0 or measurement[key] > 9:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Measurement {key} must be a number between 0 and 9"
            )
    
    # Create a new authority decision with SEKED
    authority_decision = AuthorityDecision(
        authority_run_id=None,  # Will be set when associated with a run
        tool_name="agent_state_update",
        tool_parameters={'agent_id': agent_id},
        decision='approve',  # Will be updated by SEKED
        agent_context={'agent_id': agent_id},
        workspace_context={'workspace_id': current_user.workspace_id}
    )
    
    # Apply SEKED decision
    updated_decision = seked_service.apply_seked_decision(
        authority_decision, measurement
    )
    
    db.add(updated_decision)
    db.commit()
    db.refresh(updated_decision)
    
    return {
        'decision_id': updated_decision.id,
        'decision': updated_decision.decision,
        'seked_state': {
            'measurement': updated_decision.seked_measurement,
            'ratios': updated_decision.seked_ratios,
            'directive': updated_decision.seked_directive
        },
        'timestamp': updated_decision.decision_time.isoformat()
    }
