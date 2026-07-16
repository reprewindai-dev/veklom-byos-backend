import pytest
from backend.services.uacp.core import UACPDecisionKernel

@pytest.fixture
def uacp_kernel():
    return UACPDecisionKernel()

def test_check_data_exfiltration_missing_fields(uacp_kernel):
    policy_frame = {}
    context = {}
    workspace_id = "test-ws"

    passed, details = uacp_kernel._check_data_exfiltration(policy_frame, context, workspace_id)

    assert passed is True
    assert details["has_pii"] is False
    assert details["external_destinations"] == 0

def test_check_data_exfiltration_no_pii_no_dest(uacp_kernel):
    policy_frame = {"contains_pii": False, "external_destinations": []}
    context = {}
    workspace_id = "test-ws"

    passed, details = uacp_kernel._check_data_exfiltration(policy_frame, context, workspace_id)

    assert passed is True
    assert details["has_pii"] is False
    assert details["external_destinations"] == 0

def test_check_data_exfiltration_no_pii_with_dest(uacp_kernel):
    policy_frame = {"contains_pii": False, "external_destinations": ["example.com"]}
    context = {}
    workspace_id = "test-ws"

    passed, details = uacp_kernel._check_data_exfiltration(policy_frame, context, workspace_id)

    assert passed is True
    assert details["has_pii"] is False
    assert details["external_destinations"] == 1

def test_check_data_exfiltration_with_pii_no_dest(uacp_kernel):
    policy_frame = {"contains_pii": True, "external_destinations": []}
    context = {}
    workspace_id = "test-ws"

    passed, details = uacp_kernel._check_data_exfiltration(policy_frame, context, workspace_id)

    assert passed is True
    assert details["has_pii"] is True
    assert details["external_destinations"] == 0

def test_check_data_exfiltration_with_pii_with_dest(uacp_kernel):
    policy_frame = {"contains_pii": True, "external_destinations": ["example.com"]}
    context = {}
    workspace_id = "test-ws"

    passed, details = uacp_kernel._check_data_exfiltration(policy_frame, context, workspace_id)

    assert passed is False
    assert details["has_pii"] is True
    assert details["external_destinations"] == 1
