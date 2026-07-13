import pytest
from backend.core.schemas.trust.connection import TransportMode
from backend.core.schemas.trust.identity import ExecutionIdentity, IdentityKind
from backend.core.services.trust_connection_factory import TrustConnectionFactory
from backend.core.amphoteric.parser import extract_amphoteric_context

def test_trust_connection_factory_creates_new_trace():
    identity = ExecutionIdentity(
        kind=IdentityKind.HUMAN,
        subject="test_user"
    )
    headers = {}
    trace_context, transport_context = extract_amphoteric_context(headers)
    conn, ctx = TrustConnectionFactory.create_connection(
        workspace_id="ws_1",
        operator_id="user_1",
        intent="run:code",
        identity=identity,
        trace_context=trace_context,
        transport_context=transport_context
    )

    assert conn.workspace_id == "ws_1"
    assert ctx.trace.traceparent is not None
    assert ctx.trace.traceparent.startswith("00-")
    assert ctx.trace.traceparent.endswith("-01")
    assert ctx.transport.spiffe_verified is False
    assert ctx.transport.transport_mode == TransportMode.UNKNOWN.value


def test_trust_connection_factory_uses_existing_trace():
    identity = ExecutionIdentity(
        kind=IdentityKind.HUMAN,
        subject="test_user"
    )
    headers = {
        "traceparent": "00-12345678901234567890123456789012-1234567890123456-01",
        "tracestate": "vendor=1"
    }
    trace_context, transport_context = extract_amphoteric_context(headers)
    conn, ctx = TrustConnectionFactory.create_connection(
        workspace_id="ws_1",
        operator_id="user_1",
        intent="run:code",
        identity=identity,
        trace_context=trace_context,
        transport_context=transport_context
    )

    assert ctx.trace.traceparent == "00-12345678901234567890123456789012-1234567890123456-01"
    assert ctx.trace.tracestate == "vendor=1"


def test_trust_connection_factory_validates_spiffe_and_transport():
    identity = ExecutionIdentity(
        kind=IdentityKind.SERVICE,
        subject="spiffe://veklom.io/ns/test/svc/test"
    )
    headers = {
        "x-spiffe-id": "spiffe://veklom.io/ns/test/svc/test",
        "x-transport": "mcp"
    }
    trace_context, transport_context = extract_amphoteric_context(headers)
    conn, ctx = TrustConnectionFactory.create_connection(
        workspace_id="ws_1",
        operator_id="user_1",
        intent="run:mcp",
        identity=identity,
        trace_context=trace_context,
        transport_context=transport_context
    )

    assert ctx.transport.spiffe_verified is True
    assert ctx.transport.spiffe_id == "spiffe://veklom.io/ns/test/svc/test"
    assert ctx.transport.transport_mode == TransportMode.MCP.value
    assert conn.transport_mode == TransportMode.MCP


def test_trust_connection_factory_invalid_spiffe_forces_unknown():
    identity = ExecutionIdentity(
        kind=IdentityKind.SERVICE,
        subject="spiffe://other.io/ns/test/svc/test"
    )
    headers = {
        "x-spiffe-id": "spiffe://other.io/ns/test/svc/test",
        "x-transport": "mcp"
    }
    trace_context, transport_context = extract_amphoteric_context(headers)
    conn, ctx = TrustConnectionFactory.create_connection(
        workspace_id="ws_1",
        operator_id="user_1",
        intent="run:mcp",
        identity=identity,
        trace_context=trace_context,
        transport_context=transport_context
    )

    assert ctx.transport.spiffe_verified is False
    assert ctx.transport.spiffe_id is None
    assert ctx.transport.transport_mode == TransportMode.UNKNOWN.value
    assert conn.transport_mode == TransportMode.UNKNOWN
