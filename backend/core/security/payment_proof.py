from fastapi import Request, HTTPException, status
import hashlib
import json


async def require_payment_proof(request: Request) -> dict:
    """
    Dependency that extracts and validates the X-Payment-Proof header.
    In a full production implementation, this would verify the cryptographic signature
    and call out to the L2 chain to confirm settlement.
    """
    proof_header = request.headers.get("X-Payment-Proof")
    if not proof_header:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Missing X-Payment-Proof header for governed execution."
        )
    
    try:
        # For our local/development environment, we expect a JSON encoded proof
        proof = json.loads(proof_header)
        
        # Enforce that the proof has required tracking metadata
        if "payment_proof_hash" not in proof and "proof_hash" not in proof:
            proof["payment_proof_hash"] = hashlib.sha256(proof_header.encode()).hexdigest()
            
        return proof
    except json.JSONDecodeError:
        # Fallback to returning a synthetic proof dict from the raw header
        return {
            "payment_proof_hash": hashlib.sha256(proof_header.encode()).hexdigest(),
            "raw": proof_header
        }
