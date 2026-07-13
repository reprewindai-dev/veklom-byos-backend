"""RepoGate Attestations - DSSE and SLSA alignment."""

import json
import base64
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import hashlib

class SourceAttestation(BaseModel):
    """Source Attestation mapping to SLSA concepts."""
    repository: str
    commit_sha: str
    branch: str
    slsa_level: int = Field(default=1, description="SLSA Level. 1=Provenance Documented. 2=Hosted Build Service.")
    build_authority: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DSSEEnvelope(BaseModel):
    """Dead Simple Signing Envelope (DSSE)."""
    payloadType: str = "application/vnd.in-toto+json"
    payload: str
    signatures: List[Dict[str, str]]

class RepoGateAttestor:
    """Handles the creation and verification of repository attestations."""
    
    def __init__(self, designated_build_authority: str = "coolify"):
        self.designated_build_authority = designated_build_authority
        
    def _b64_encode(self, data: str) -> str:
        return base64.b64encode(data.encode('utf-8')).decode('utf-8')

    def create_attestation(self, repository: str, commit_sha: str, branch: str, builder_id: str) -> DSSEEnvelope:
        """Create a DSSE wrapped source attestation."""
        
        # Determine SLSA level
        # If the builder is our designated authority (Coolify), it qualifies for SLSA Level 2
        slsa_level = 2 if builder_id.lower() == self.designated_build_authority else 1
        
        attestation = SourceAttestation(
            repository=repository,
            commit_sha=commit_sha,
            branch=branch,
            slsa_level=slsa_level,
            build_authority=builder_id
        )
        
        # In a real implementation, the signature would be a real cryptographic signature
        # over the PAE (Pre-Authentication Encoding) of the payload.
        # PAE = "DSSEv1" + len(payloadType) + payloadType + len(payload) + payload
        
        payload_json = json.dumps(attestation.model_dump(), sort_keys=True)
        encoded_payload = self._b64_encode(payload_json)
        
        # Mock signature for now (this would use Ed25519/ECDSA in production)
        pae = f"DSSEv1 28 application/vnd.in-toto+json {len(encoded_payload)} {encoded_payload}"
        mock_sig = hashlib.sha256(pae.encode('utf-8')).hexdigest()
        
        envelope = DSSEEnvelope(
            payload=encoded_payload,
            signatures=[{
                "keyid": f"urn:veklom:builder:{builder_id}",
                "sig": self._b64_encode(mock_sig)
            }]
        )
        
        return envelope
        
    def verify_attestation(self, envelope: DSSEEnvelope, required_slsa_level: int = 1) -> Dict[str, Any]:
        """Verify the DSSE envelope and SLSA requirements."""
        try:
            decoded_payload = base64.b64decode(envelope.payload).decode('utf-8')
            attestation_data = json.loads(decoded_payload)
            attestation = SourceAttestation(**attestation_data)
        except Exception as e:
            return {"valid": False, "reason": f"Malformed payload: {str(e)}"}
            
        # In a real implementation, we would cryptographically verify the signature here
        
        # Verify SLSA Level
        if attestation.slsa_level < required_slsa_level:
            return {
                "valid": False, 
                "reason": f"Insufficient SLSA level. Required {required_slsa_level}, got {attestation.slsa_level}"
            }
            
        # Gate Level 2 attestations on verification from designated build authority
        if required_slsa_level >= 2:
            if attestation.build_authority != self.designated_build_authority:
                # We could emit a warning instead of a hard block as per the open question, 
                # but failing closed is the safer default until instructed otherwise.
                return {
                    "valid": False,
                    "reason": f"SLSA Level 2 requires build authority '{self.designated_build_authority}', got '{attestation.build_authority}'"
                }
                
        return {
            "valid": True,
            "attestation": attestation.model_dump(),
            "reason": "Verified"
        }

repogate_attestor = RepoGateAttestor()
