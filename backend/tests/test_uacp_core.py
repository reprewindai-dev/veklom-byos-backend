import pytest
from backend.services.uacp.core import UACPDecisionKernel

def test_check_tool_allowlist_empty_dicts():
    kernel = UACPDecisionKernel()
    passed, details = kernel._check_tool_allowlist({}, {}, "ws_1")
    assert passed is True
    assert details == {"blocked_tools": []}

def test_check_tool_allowlist_empty_tools_and_allowlist():
    kernel = UACPDecisionKernel()
    passed, details = kernel._check_tool_allowlist({"tools": []}, {"tool_allowlist": []}, "ws_1")
    assert passed is True
    assert details == {"blocked_tools": []}

def test_check_tool_allowlist_empty_tools_with_allowlist():
    kernel = UACPDecisionKernel()
    passed, details = kernel._check_tool_allowlist({"tools": []}, {"tool_allowlist": ["tool1", "tool2"]}, "ws_1")
    assert passed is True
    assert details == {"blocked_tools": []}

def test_check_tool_allowlist_tools_with_empty_allowlist():
    kernel = UACPDecisionKernel()
    passed, details = kernel._check_tool_allowlist({"tools": ["tool1"]}, {"tool_allowlist": []}, "ws_1")
    assert passed is False
    assert details == {"blocked_tools": ["tool1"]}

def test_check_tool_allowlist_all_tools_allowed():
    kernel = UACPDecisionKernel()
    passed, details = kernel._check_tool_allowlist(
        {"tools": ["tool1", "tool2"]},
        {"tool_allowlist": ["tool1", "tool2", "tool3"]},
        "ws_1"
    )
    assert passed is True
    assert details == {"blocked_tools": []}

def test_check_tool_allowlist_partially_allowed():
    kernel = UACPDecisionKernel()
    passed, details = kernel._check_tool_allowlist(
        {"tools": ["tool1", "tool_unallowed"]},
        {"tool_allowlist": ["tool1", "tool2"]},
        "ws_1"
    )
    assert passed is False
    assert details == {"blocked_tools": ["tool_unallowed"]}

def test_check_tool_allowlist_all_tools_blocked():
    kernel = UACPDecisionKernel()
    passed, details = kernel._check_tool_allowlist(
        {"tools": ["bad_tool1", "bad_tool2"]},
        {"tool_allowlist": ["tool1", "tool2"]},
        "ws_1"
    )
    assert passed is False
    assert details == {"blocked_tools": ["bad_tool1", "bad_tool2"]}
