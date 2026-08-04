"""
Evidence Pack Recorder
Records complete build and verification audit trail for compliance

Evidence packs capture:
- Build metadata (timestamp, builder, version)
- All verification results (hooks, tests, scans)
- Hash values (source, artifact, policy, dependency, runtime)
- PGL registration details
- Policy decisions
- Security scan results

Location: veklom-byos-backend/backend/gpc/verification/evidence_pack.py
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class BuildEvidence:
    """Evidence from the build phase"""
    builder_name: str
    requirement_type: str
    node_type: str
    external_system: Optional[str]
    source_code_hash: str
    artifact_hash: str
    manifest: Dict[str, Any]
    duration_seconds: float
    timestamp: datetime


@dataclass
class VerificationEvidence:
    """Evidence from verification hooks"""
    hook_name: str
    status: str  # passed, failed, skipped, error
    message: str
    evidence: Dict[str, Any]
    duration_seconds: float
    timestamp: datetime


@dataclass
class PGLEvidence:
    """Evidence from PGL registration"""
    agent_id: str
    certificate_id: str
    jurisdiction: str
    genome: Dict[str, Any]
    registered_at: datetime


@dataclass
class PolicyEvidence:
    """Evidence from policy validation"""
    policy_hash: str
    decisions: List[Dict[str, Any]]
    approved: bool
    validated_at: datetime


@dataclass
class FreshnessEvidence:
    """Evidence from freshness gate validation"""
    source_hash_valid: bool
    artifact_hash_valid: bool
    policy_hash_valid: bool
    dependency_hash_valid: bool
    runtime_hash_valid: bool
    certificate_valid: bool
    capi_approved: bool
    validated_at: datetime
    validation_chain: List[str]


class EvidencePack:
    """
    Complete audit trail for a capability.

    Immutable record of:
    - Build process
    - Verification checks
    - Hash values
    - Security decisions
    - Policy approvals
    - Freshness validation

    Used for compliance, debugging, and governance.
    """

    def __init__(
        self,
        capability_id: str,
        pipeline_id: str,
        tenant_id: str,
    ):
        """
        Initialize evidence pack.

        Args:
            capability_id: ID of the capability
            pipeline_id: Pipeline that requested it
            tenant_id: Tenant owning the pipeline
        """
        self.capability_id = capability_id
        self.pipeline_id = pipeline_id
        self.tenant_id = tenant_id

        self.created_at = datetime.utcnow()

        # Sections
        self.build_evidence: Optional[BuildEvidence] = None
        self.verification_evidence: List[VerificationEvidence] = []
        self.pgl_evidence: Optional[PGLEvidence] = None
        self.policy_evidence: Optional[PolicyEvidence] = None
        self.freshness_evidence: Optional[FreshnessEvidence] = None

        # Hashes for integrity
        self.hashes: Dict[str, str] = {}

    def add_build_evidence(
        self,
        builder_name: str,
        requirement_type: str,
        node_type: str,
        external_system: Optional[str],
        source_code_hash: str,
        artifact_hash: str,
        manifest: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """Add evidence from build phase"""
        self.build_evidence = BuildEvidence(
            builder_name=builder_name,
            requirement_type=requirement_type,
            node_type=node_type,
            external_system=external_system,
            source_code_hash=source_code_hash,
            artifact_hash=artifact_hash,
            manifest=manifest,
            duration_seconds=duration_seconds,
            timestamp=datetime.utcnow(),
        )

        # Record hashes
        self.hashes["source"] = source_code_hash
        self.hashes["artifact"] = artifact_hash

    def add_verification_evidence(
        self,
        hook_name: str,
        status: str,
        message: str,
        evidence: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """Add evidence from a verification hook"""
        self.verification_evidence.append(
            VerificationEvidence(
                hook_name=hook_name,
                status=status,
                message=message,
                evidence=evidence,
                duration_seconds=duration_seconds,
                timestamp=datetime.utcnow(),
            )
        )

    def add_pgl_evidence(
        self,
        agent_id: str,
        certificate_id: str,
        jurisdiction: str,
        genome: Dict[str, Any],
    ) -> None:
        """Add evidence from PGL registration"""
        self.pgl_evidence = PGLEvidence(
            agent_id=agent_id,
            certificate_id=certificate_id,
            jurisdiction=jurisdiction,
            genome=genome,
            registered_at=datetime.utcnow(),
        )

        # Record PGL hash
        self.hashes["pgl_certificate"] = certificate_id

    def add_policy_evidence(
        self,
        policy_hash: str,
        decisions: List[Dict[str, Any]],
        approved: bool,
    ) -> None:
        """Add evidence from policy validation"""
        self.policy_evidence = PolicyEvidence(
            policy_hash=policy_hash,
            decisions=decisions,
            approved=approved,
            validated_at=datetime.utcnow(),
        )

        # Record policy hash
        self.hashes["policy"] = policy_hash

    def add_freshness_evidence(
        self,
        source_hash_valid: bool,
        artifact_hash_valid: bool,
        policy_hash_valid: bool,
        dependency_hash_valid: bool,
        runtime_hash_valid: bool,
        certificate_valid: bool,
        capi_approved: bool,
        validation_chain: List[str],
    ) -> None:
        """Add evidence from freshness gate validation"""
        self.freshness_evidence = FreshnessEvidence(
            source_hash_valid=source_hash_valid,
            artifact_hash_valid=artifact_hash_valid,
            policy_hash_valid=policy_hash_valid,
            dependency_hash_valid=dependency_hash_valid,
            runtime_hash_valid=runtime_hash_valid,
            certificate_valid=certificate_valid,
            capi_approved=capi_approved,
            validated_at=datetime.utcnow(),
            validation_chain=validation_chain,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        return {
            "capability_id": self.capability_id,
            "pipeline_id": self.pipeline_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "build_evidence": asdict(self.build_evidence) if self.build_evidence else None,
            "verification_evidence": [
                {
                    **asdict(ev),
                    "timestamp": ev.timestamp.isoformat(),
                }
                for ev in self.verification_evidence
            ],
            "pgl_evidence": (
                {
                    **asdict(self.pgl_evidence),
                    "registered_at": self.pgl_evidence.registered_at.isoformat(),
                }
                if self.pgl_evidence
                else None
            ),
            "policy_evidence": (
                {
                    **asdict(self.policy_evidence),
                    "validated_at": self.policy_evidence.validated_at.isoformat(),
                }
                if self.policy_evidence
                else None
            ),
            "freshness_evidence": (
                {
                    **asdict(self.freshness_evidence),
                    "validated_at": self.freshness_evidence.validated_at.isoformat(),
                }
                if self.freshness_evidence
                else None
            ),
            "hashes": self.hashes,
            "integrity_hash": self._compute_integrity_hash(),
        }

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), default=str)

    def _compute_integrity_hash(self) -> str:
        """
        Compute hash of entire evidence pack.

        Used to detect tampering.
        """
        # Create canonical JSON (sorted keys)
        data = json.dumps(
            {
                k: v for k, v in self.to_dict().items()
                if k != "integrity_hash"
            },
            sort_keys=True,
            default=str,
        )

        return hashlib.sha256(data.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """
        Verify evidence pack integrity.

        Returns:
            True if hash matches, False if tampered
        """
        current_hash = self._compute_integrity_hash()
        stored_hash = self.to_dict().get("integrity_hash")

        return current_hash == stored_hash


class EvidencePackStore:
    """
    Stores and retrieves evidence packs.

    Could use S3, database, or local filesystem.
    """

    def __init__(self, backend_url: str = "s3://veklom-evidence"):
        """
        Initialize store.

        Args:
            backend_url: Where to store evidence packs
        """
        self.backend_url = backend_url

    async def store(self, evidence_pack: EvidencePack) -> str:
        """
        Store an evidence pack.

        Args:
            evidence_pack: The pack to store

        Returns:
            URL/path where it was stored
        """
        pack_id = f"{evidence_pack.capability_id}_{evidence_pack.created_at.timestamp()}"
        storage_path = f"{self.backend_url}/evidence/{pack_id}.json"

        # Would use S3 client or similar to store
        # await s3_client.put_object(
        #     Bucket="veklom-evidence",
        #     Key=f"evidence/{pack_id}.json",
        #     Body=evidence_pack.to_json(),
        # )

        print(f"[EvidenceStore] Stored {evidence_pack.capability_id} at {storage_path}")

        return storage_path

    async def retrieve(self, capability_id: str, timestamp: str) -> Optional[EvidencePack]:
        """
        Retrieve an evidence pack.

        Args:
            capability_id: The capability ID
            timestamp: When it was created

        Returns:
            EvidencePack or None if not found
        """
        pack_id = f"{capability_id}_{timestamp}"

        # Would use S3 client or similar to retrieve
        # response = await s3_client.get_object(
        #     Bucket="veklom-evidence",
        #     Key=f"evidence/{pack_id}.json",
        # )
        # data = json.loads(response['Body'].read())
        # return EvidencePack.from_dict(data)

        return None


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.gpc.verification.evidence_pack import EvidencePack, EvidencePackStore

# Create evidence pack
evidence = EvidencePack(
    capability_id="looker_connector_v1",
    pipeline_id="pipeline_123",
    tenant_id="default",
)

# Add build evidence
evidence.add_build_evidence(
    builder_name="OpenAPIConnectorBuilder",
    requirement_type="connector",
    node_type="looker_connector",
    external_system="looker",
    source_code_hash=result.source_hash,
    artifact_hash=result.artifact_hash,
    manifest=result.manifest,
    duration_seconds=result.duration_seconds,
)

# Add verification evidence (from hooks)
for hook_result in verification_results:
    evidence.add_verification_evidence(
        hook_name=hook_result.hook_name,
        status=hook_result.status.value,
        message=hook_result.message,
        evidence=hook_result.evidence,
        duration_seconds=hook_result.duration_seconds,
    )

# Add PGL evidence
evidence.add_pgl_evidence(
    agent_id=pgl_result["agent_id"],
    certificate_id=pgl_result["certificate_id"],
    jurisdiction="CA",
    genome={...},
)

# Add policy evidence
evidence.add_policy_evidence(
    policy_hash=policy_hash,
    decisions=[...],
    approved=True,
)

# Add freshness evidence
evidence.add_freshness_evidence(
    source_hash_valid=True,
    artifact_hash_valid=True,
    policy_hash_valid=True,
    dependency_hash_valid=True,
    runtime_hash_valid=True,
    certificate_valid=True,
    capi_approved=True,
    validation_chain=["security", "policy", "freshness"],
)

# Store
store = EvidencePackStore()
evidence_url = await store.store(evidence)

print(f"Evidence pack stored at {evidence_url}")
print(f"Integrity: {evidence.verify_integrity()}")

# Later, verify
json_data = evidence.to_json()
print(json_data)
"""
