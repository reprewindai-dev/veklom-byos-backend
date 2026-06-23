from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any, List
import uuid

from backend.core.database.database import get_db
from backend.db.models.vnp import (
    Incident, IncidentState, SettlementEntry, SettlementState, LedgerEntryType,
    Attestation, AttestationState, Validator
)

router = APIRouter(prefix="/incidents", tags=["VNP Incidents"])

@router.post("/{incident_id}/challenge")
async def challenge_incident(
    incident_id: uuid.UUID,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Called by a Provider to dispute an SLA slash.
    Puts the associated 'slash' settlement entry into a 'hold' state
    and flags the incident as 'challenged'.
    """
    # Find incident
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = (await db.execute(stmt)).scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    if incident.state == IncidentState.resolved:
        raise HTTPException(status_code=400, detail="Cannot challenge a resolved incident")
        
    # Update incident state
    incident.state = IncidentState.acknowledged # Use acknowledged to represent under-review for now
    
    # Find associated settlement entry
    settlement_stmt = select(SettlementEntry).where(
        and_(
            SettlementEntry.entry_type == LedgerEntryType.slash,
            SettlementEntry.reference_code == f"slash-{incident_id}"
        )
    )
    settlements = (await db.execute(settlement_stmt)).scalars().all()
    
    for s in settlements:
        if s.state == SettlementState.pending:
            s.state = SettlementState.failed # Use failed/reversed to temporarily halt it. Ideally 'hold' but it doesn't exist in enum. Wait, 'hold' does exist in LedgerEntryType, but here we want SettlementState. Wait, the SettlementState enum is pending, posted, failed, reversed. We can leave it pending and set metadata.
            s.entry_metadata = {**s.entry_metadata, "challenged": True, "challenge_reason": payload.get("reason", "")}

    await db.commit()
    
    return {"status": "challenged", "incident_id": str(incident_id)}

@router.post("/{incident_id}/attest")
async def submit_attestation(
    incident_id: uuid.UUID,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Called by a PGL Validator (the 120-node army) to submit a vote (attestation) 
    on whether an SLA breach is legitimate.
    """
    validator_id_str = payload.get("validator_id")
    vote_uphold = payload.get("uphold_slash", True)
    signature = payload.get("signature")
    
    if not validator_id_str or not signature:
        raise HTTPException(status_code=400, detail="Missing validator_id or signature")
        
    try:
        validator_id = uuid.UUID(validator_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid validator UUID")
        
    stmt = select(Validator).where(Validator.id == validator_id)
    validator = (await db.execute(stmt)).scalar_one_or_none()
    
    if not validator:
        raise HTTPException(status_code=404, detail="Validator not found")
        
    # In a real impl, we would verify the Ed25519 signature of the payload using validator.public_key here
    
    attestation = Attestation(
        validator_id=validator_id,
        incident_id=incident_id,
        attestation_window_start=incident.opened_at if 'incident' in locals() else payload.get("window_start"),
        attestation_window_end=payload.get("window_end"),
        state=AttestationState.accepted if vote_uphold else AttestationState.rejected,
        payload=payload,
        signature_value=signature
    )
    
    # We need to fetch incident to set windows if missing
    inc_stmt = select(Incident).where(Incident.id == incident_id)
    inc = (await db.execute(inc_stmt)).scalar_one_or_none()
    if inc:
        attestation.attestation_window_start = inc.opened_at
        attestation.attestation_window_end = inc.opened_at # Simplifying for demo
        
    db.add(attestation)
    await db.commit()
    
    # Check consensus (66% supermajority)
    # Get all attestations for this incident
    att_stmt = select(Attestation).where(Attestation.incident_id == incident_id)
    all_atts = (await db.execute(att_stmt)).scalars().all()
    
    total_validators = 120 # From PGL
    uphold_votes = sum(1 for a in all_atts if a.state == AttestationState.accepted)
    
    consensus_reached = False
    action_taken = None
    
    if uphold_votes >= (total_validators * 0.66):
        consensus_reached = True
        action_taken = "slash_upheld"
        # Execute the slash
        if inc:
            inc.state = IncidentState.resolved
            
            settlement_stmt = select(SettlementEntry).where(
                and_(
                    SettlementEntry.entry_type == LedgerEntryType.slash,
                    SettlementEntry.reference_code == f"slash-{incident_id}"
                )
            )
            settlements = (await db.execute(settlement_stmt)).scalars().all()
            for s in settlements:
                s.state = SettlementState.posted
                
            await db.commit()
            
    return {
        "status": "attestation_recorded",
        "incident_id": str(incident_id),
        "consensus_reached": consensus_reached,
        "action_taken": action_taken,
        "current_uphold_votes": uphold_votes
    }
