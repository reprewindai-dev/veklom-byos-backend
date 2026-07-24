import pytest
from pydantic import ValidationError

from backend.core.schemas.trust.connection import TrustConnection


def test_trust_connection_id_default():
    """Test that default generated connection_id has 'conn_' prefix."""
    conn = TrustConnection(workspace_id="ws_123", operator_id="op_123", intent="test")
    assert conn.connection_id.startswith("conn_")
    assert len(conn.connection_id) > 5


def test_trust_connection_id_valid_custom():
    """Test that a custom connection_id with 'conn_' prefix is accepted."""
    conn = TrustConnection(connection_id="conn_custom_123", workspace_id="ws_123", operator_id="op_123", intent="test")
    assert conn.connection_id == "conn_custom_123"


def test_trust_connection_id_invalid_prefix():
    """Test that a connection_id without 'conn_' prefix raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TrustConnection(connection_id="invalid_123", workspace_id="ws_123", operator_id="op_123", intent="test")

    assert "connection_id must be prefixed 'conn_'" in str(exc_info.value)
