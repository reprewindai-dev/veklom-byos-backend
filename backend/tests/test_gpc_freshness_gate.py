from dataclasses import dataclass, field

import pytest

from backend.apps.gpc.freshness_gate import FreshnessGate


@dataclass
class BuildEvidence:
    source_code_hash: str = "source-hash"
    artifact_hash: str = "artifact-hash"
    requirement_type: str = "openapi"
    external_system: str = "test-api"
    manifest: dict = field(default_factory=lambda: {"operations": ["read"]})


@dataclass
class PolicyEvidence:
    approved: bool = True
    decisions: list = field(default_factory=lambda: [{"approved": True}])


@dataclass
class VerificationEvidence:
    hook_name: str = "unit_tests"
    status: str = "passed"


@dataclass
class PGLEvidence:
    certificate_id: str = "cert-123"


@dataclass
class EvidencePack:
    build_evidence: BuildEvidence = field(default_factory=BuildEvidence)
    policy_evidence: PolicyEvidence = field(default_factory=PolicyEvidence)
    verification_evidence: list = field(default_factory=lambda: [VerificationEvidence()])
    pgl_evidence: PGLEvidence = field(default_factory=PGLEvidence)


class PGLClient:
    async def verify_certificate(self, certificate_id: str):
        return {"valid": True, "expired": False, "certificate_id": certificate_id}


class CAPIClient:
    async def request_binding_approval(self, **kwargs):
        return {"approved": True, "approval_chain": ["policy", "security"], "request": kwargs}


@pytest.mark.asyncio
async def test_freshness_gate_fails_closed_without_external_governance_clients():
    result = await FreshnessGate().validate_before_bind("capability-1", EvidencePack())

    assert result["passed"] is False
    messages = [check["message"] for check in result["details"]]
    assert "PGL verifier unavailable" in messages
    assert "CAPI approval service unavailable" in messages


@pytest.mark.asyncio
async def test_freshness_gate_allows_binding_only_with_verified_pgl_and_capi_approval():
    gate = FreshnessGate(pgl_client=PGLClient(), capi_client=CAPIClient())

    result = await gate.validate_before_bind("capability-1", EvidencePack())

    assert result["passed"] is True
    assert result["recommendation"] == "safe_to_bind"
