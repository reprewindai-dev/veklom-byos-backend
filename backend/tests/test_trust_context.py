import pytest
from pydantic import ValidationError

from backend.core.schemas.trust.context import W3CTraceContext


def test_w3c_trace_context_valid():
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    context = W3CTraceContext(traceparent=traceparent, tracestate="congo=t61rcWkgMzE")
    assert context.traceparent == traceparent
    assert context.tracestate == "congo=t61rcWkgMzE"

def test_w3c_trace_context_invalid_parts_count():
    # Only 3 parts
    with pytest.raises(ValidationError, match="traceparent must follow W3C format"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7")

    # 5 parts
    with pytest.raises(ValidationError, match="traceparent must follow W3C format"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-extra")

def test_w3c_trace_context_invalid_prefix():
    # Starts with "01" instead of "00"
    with pytest.raises(ValidationError, match="traceparent must follow W3C format"):
        W3CTraceContext(traceparent="01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")

def test_w3c_trace_context_invalid_trace_id_length():
    # trace_id is 31 chars instead of 32
    with pytest.raises(ValidationError, match="traceparent field lengths must be"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e473-00f067aa0ba902b7-01")

    # trace_id is 33 chars instead of 32
    with pytest.raises(ValidationError, match="traceparent field lengths must be"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736a-00f067aa0ba902b7-01")

def test_w3c_trace_context_invalid_span_id_length():
    # span_id is 15 chars instead of 16
    with pytest.raises(ValidationError, match="traceparent field lengths must be"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b-01")

    # span_id is 17 chars instead of 16
    with pytest.raises(ValidationError, match="traceparent field lengths must be"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7a-01")

def test_w3c_trace_context_invalid_flags_length():
    # flags is 1 char instead of 2
    with pytest.raises(ValidationError, match="traceparent field lengths must be"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-0")

    # flags is 3 chars instead of 2
    with pytest.raises(ValidationError, match="traceparent field lengths must be"):
        W3CTraceContext(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-012")
