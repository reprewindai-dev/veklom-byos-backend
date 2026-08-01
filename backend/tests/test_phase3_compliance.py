from datetime import datetime, timedelta

import pytest

from backend.apps.gpc.routes import validate_gpc_request
from backend.apps.gpc.schemas import GPCNode, GPCPipelineGraph, PipelineCompilationRequest
from backend.compliance import DataClassification, JurisdictionDetector, LegalFramework, RuntimeSemanticStateRecord
from backend.compliance.ccpa_framework import CCPAFramework
from backend.compliance.gdpr_framework import GDPRFramework, LegalBasis
from backend.compliance.law25_compliance_framework import DataResidency, Law25ComplianceFramework, ProcessingPurpose
from backend.compliance.multi_jurisdiction_enforcement import AutoEnforcementMode, MultiJurisdictionEnforcer
from backend.compliance.sovereignty_enforcement import DataLocation, SovereigntyEnforcer


def _graph(metadata=None, region="ca-central-1"):
    return GPCPipelineGraph(
        pipeline_id="pipeline-compliance",
        tenant_id="workspace-1",
        nodes=[GPCNode(id="node-1", node_type="CsvFileInput")],
        edges=[],
        metadata=metadata or {},
        data_residency_region=region,
    )


def test_jurisdiction_detector_loads_law25_for_restricted_quebec_without_geoip_dependency():
    detector = JurisdictionDetector()

    result = detector.detect_jurisdiction(data_classification=DataClassification.RESTRICTED_QUEBEC)

    assert result.primary_framework == LegalFramework.LAW25
    assert LegalFramework.PIPEDA in result.applicable_frameworks
    assert result.requires_audit_trail is True
    assert result.cross_border_allowed is False


def test_law25_consent_audit_and_withdrawal_are_enforced():
    framework = Law25ComplianceFramework(tenant_id="workspace-1")
    framework.register_data_element(
        element_id="email",
        field_name="email",
        data_type="string",
        classification="restricted",
        residency=DataResidency.QUEBEC,
        contains_pii=True,
        is_sensitive=False,
        retention_days=30,
    )
    consent_id = framework.record_consent(
        user_id="user-1",
        purpose=ProcessingPurpose.ANALYTICS,
        expires_at=datetime.utcnow() + timedelta(days=1),
        proof_url="proof://consent/user-1",
    )

    assert framework.check_consent("user-1", ProcessingPurpose.ANALYTICS) is True
    assert framework.withdraw_consent(consent_id, reason="user requested") is True
    assert framework.check_consent("user-1", ProcessingPurpose.ANALYTICS) is False
    assert framework.get_audit_trail()


def test_sovereignty_enforcer_blocks_restricted_canadian_data_to_us_endpoint():
    enforcer = SovereigntyEnforcer()
    enforcer.register_endpoint("us-api", "api.example.com", 443, "https", DataLocation.USA, approved=True)

    allowed, reason = enforcer.validate_endpoint_for_data("us-api", "restricted_canadian")

    assert allowed is False
    assert "not in canada" in reason.lower()


def test_rssr_finalization_creates_verifiable_integrity_hash():
    rssr = RuntimeSemanticStateRecord(
        pipeline_id="pipeline-1",
        execution_id="run-1",
        tenant_id="workspace-1",
        user_id="user-1",
        jurisdiction="quebec",
    )
    idx = rssr.start_node_execution(
        node_id="node-1",
        node_name="Read Customer Data",
        node_type="input",
        operation="read",
        input_datasets=[],
        output_datasets=["customers"],
    )
    rssr.record_compliance_decision(
        transformation_idx=0,
        check_name="residency_check",
        passed=True,
        reason="Data stayed in Quebec",
        evidence={"location": "canada/quebec"},
        checked_by="test",
    )
    rssr.end_node_execution(0, row_count_in=0, row_count_out=1, residency_location="canada/quebec")

    final = rssr.finalize()

    assert final["compliance_summary"]["overall_compliant"] is True
    assert rssr.verify_integrity(final["integrity_hash"]) is True


def test_multi_jurisdiction_fails_closed_for_gdpr_without_explicit_consent():
    enforcer = MultiJurisdictionEnforcer(mode=AutoEnforcementMode.STRICT, organization_id="workspace-1")
    enforcer.auto_load_frameworks(data_classification=DataClassification.RESTRICTED_EU, user_location="eu")

    allowed, reason = enforcer.auto_enforce_consent("user-1", "analytics", ["pii"])

    assert allowed is False
    assert "Explicit consent required" in reason


def test_multi_jurisdiction_verifies_gdpr_consent_when_recorded():
    enforcer = MultiJurisdictionEnforcer(mode=AutoEnforcementMode.STRICT, organization_id="workspace-1")
    enforcer.auto_load_frameworks(data_classification=DataClassification.RESTRICTED_EU, user_location="eu")
    enforcer.gdpr_framework.record_consent("user-1", LegalBasis.CONSENT, "analytics", "proof://gdpr/user-1")

    allowed, reason = enforcer.auto_enforce_consent("user-1", "analytics", ["pii"])

    assert allowed is True
    assert "GDPR: Consent verified" in reason


def test_ccpa_opt_out_blocks_processing_after_recorded_opt_out():
    framework = CCPAFramework("workspace-1")
    framework.process_opt_out("user-1")

    assert framework.has_opted_out("user-1") is True


def test_gpc_compliance_gate_blocks_cross_border_restricted_quebec_graph():
    graph = _graph(
        metadata={
            "data_classification": "restricted_quebec",
            "source_location": "quebec",
            "target_location": "usa",
            "user_location": "quebec",
        }
    )
    request = PipelineCompilationRequest(pipeline_id=graph.pipeline_id, tenant_id=graph.tenant_id, graph=graph)

    with pytest.raises(ValueError, match="compliance gate blocked"):
        validate_gpc_request(request, authenticated_tenant_id="workspace-1")


def test_gpc_compliance_gate_allows_default_canadian_internal_graph():
    graph = _graph()
    request = PipelineCompilationRequest(pipeline_id=graph.pipeline_id, tenant_id=graph.tenant_id, graph=graph)

    validate_gpc_request(request, authenticated_tenant_id="workspace-1")
