import base64
import json
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from backend.apps.gpc.canonical_plan import CanonicalPlanIR
from backend.apps.policy.pdp_engine import DecisionRecord
from backend.apps.orchestration.workflow_orchestrator import WorkflowState

class DSSESignature(BaseModel):
    keyid: str
    sig: str

class DSSEEnvelope(BaseModel):
    """
    Dead Simple Signing Envelope (DSSE).
    Used for wrapping attestations to ensure provenance and integrity.
    """
    payloadType: str = Field(default="application/vnd.in-toto+json")
    payload: str = Field(..., description="Base64 encoded JSON payload")
    signatures: List[DSSESignature] = Field(default_factory=list)

class DSSEAttestationBuilder:
    """
    Builds cryptographic evidence bundles (SLSA/in-toto style) for governed executions.
    """
    
    def __init__(self, signing_key_id: str = "veklom-runtime-v1"):
        self.signing_key_id = signing_key_id
        
    def _sign_payload(self, payload_b64: str) -> str:
        """
        Simulate signing a payload. In a real system, this would use KMS or Sigstore.
        """
        # Simulated signature
        import hashlib
        return hashlib.sha256(f"signed-{self.signing_key_id}-{payload_b64}".encode()).hexdigest()

    def build_workflow_attestation(
        self, 
        plan: CanonicalPlanIR, 
        decision: DecisionRecord, 
        execution_state: WorkflowState
    ) -> DSSEEnvelope:
        """
        Create a verifiable attestation that a specific plan was approved and executed.
        """
        
        # 1. Construct the in-toto Statement (Predicate)
        predicate = {
            "builder": {"id": "https://veklom.com/gpc-compiler/v1"},
            "buildType": "https://veklom.com/governed-execution/v1",
            "invocation": {
                "configSource": {
                    "uri": f"veklom://plan/{plan.plan_id}",
                    "digest": {"sha256": plan.compute_hash()}
                },
                "environment": {
                    "tenant_id": plan.tenant_id,
                    "workflow_id": execution_state.workflow_id
                }
            },
            "buildConfig": {
                "decision": decision.model_dump(mode='json'),
                "execution_result": execution_state.model_dump(mode='json')
            }
        }
        
        statement = {
            "_type": "https://in-toto.io/Statement/v0.1",
            "subject": [{"name": f"workflow-{execution_state.workflow_id}", "digest": {"sha256": plan.compute_hash()}}],
            "predicateType": "https://slsa.dev/provenance/v0.2",
            "predicate": predicate
        }
        
        # 2. Encode Payload
        payload_json = json.dumps(statement, separators=(',', ':'))
        payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')
        
        # 3. Sign
        sig = self._sign_payload(payload_b64)
        
        # 4. Wrap in DSSE
        return DSSEEnvelope(
            payloadType="application/vnd.in-toto+json",
            payload=payload_b64,
            signatures=[DSSESignature(keyid=self.signing_key_id, sig=sig)]
        )
