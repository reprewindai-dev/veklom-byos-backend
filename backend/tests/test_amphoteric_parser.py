import pytest
from backend.core.schemas.trust.connection import TransportMode
from backend.core.amphoteric.parser import extract_amphoteric_context

def test_extract_amphoteric_context_generates_w3c_trace_if_missing():
    headers = {}
    trace, transport = extract_amphoteric_context(headers)
    
    assert trace.traceparent is not None
    assert trace.traceparent.startswith("00-")
    assert trace.traceparent.endswith("-01")
    assert trace.tracestate == ""

def test_extract_amphoteric_context_preserves_w3c_trace_if_present():
    headers = {
        "traceparent": "00-12345678901234567890123456789012-1234567890123456-01",
        "tracestate": "rojo=00f067aa0ba902b7"
    }
    trace, transport = extract_amphoteric_context(headers)
    
    assert trace.traceparent == headers["traceparent"]
    assert trace.tracestate == headers["tracestate"]

def test_extract_amphoteric_context_validates_spiffe_identity():
    import os
    os.environ["DEBUG_MOCK_SPIFFE"] = "true"
    headers = {
        "X-Spiffe-Id": "spiffe://veklom.io/ns/test/svc/backend",
        "X-Transport": "mcp"
    }
    trace, transport = extract_amphoteric_context(headers)
    
    assert transport.spiffe_verified is True
    assert transport.spiffe_id == headers["X-Spiffe-Id"]
    assert transport.transport_mode == TransportMode.MCP.value

def test_extract_amphoteric_context_invalid_spiffe_degrades_to_unknown():
    headers = {
        "X-Spiffe-Id": "spiffe://other.io/ns/test/svc/backend",
        "X-Transport": "mcp"
    }
    trace, transport = extract_amphoteric_context(headers)
    
    assert transport.spiffe_verified is False
    assert transport.spiffe_id is None
    assert transport.transport_mode == TransportMode.UNKNOWN.value

def test_extract_amphoteric_context_no_spiffe_degrades_to_unknown():
    headers = {
        "X-Transport": "mcp"
    }
    trace, transport = extract_amphoteric_context(headers)
    
    assert transport.spiffe_verified is False
    assert transport.spiffe_id is None
    assert transport.transport_mode == TransportMode.UNKNOWN.value
