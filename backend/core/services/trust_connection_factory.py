"""
TrustConnectionFactory — Phase 2 of the Trust Fabric.

This service is the definitive builder for TrustConnection + ConnectionContext.
It creates the canonical carry-forward context at the CAPI lane entry point,
solving M2M context loss and agent drift. Once sealed, this context is read-only
for downstream services.
"""

from __future__ import annotations

import secrets
from typing import Dict, Optional, Tuple

from backend.core.schemas.trust.connection import (
    ConnectionRequirements,
    ConnectionStatus,
    TransportMode,
    TrustConnection,
)
from backend.core.schemas.trust.context import (
    AmphotericTransportContext,
    ConnectionContext,
    W3CTraceContext,
)
from backend.core.schemas.trust.identity import ExecutionIdentity


class TrustConnectionFactory:
    """
    Factory for building the TrustConnection and ConnectionContext.
    """

    @classmethod
    def create_connection(
        cls,
        workspace_id: str,
        operator_id: str,
        intent: str,
        identity: ExecutionIdentity,
        trace_context: W3CTraceContext,
        transport_context: AmphotericTransportContext,
        requirements: Optional[ConnectionRequirements] = None,
    ) -> Tuple[TrustConnection, ConnectionContext]:
        """
        Builds and seals the TrustConnection + ConnectionContext pair at lane entry.
        
        Args:
            workspace_id: The PGL-governed workspace owning this connection.
            operator_id: The operator (org/user) initiating this connection.
            intent: The structured intent label (e.g. 'run:code').
            identity: The pre-resolved execution identity.
            trace_context: Pre-parsed W3C trace context.
            transport_context: Pre-parsed Amphoteric transport context.
            requirements: Optional overrides for connection requirements.
        
        Returns:
            A tuple of (TrustConnection, ConnectionContext).
        """
        # 1. Create the TrustConnection
        if requirements is None:
            requirements = ConnectionRequirements()
            
        try:
            transport_mode = TransportMode(transport_context.transport_mode)
        except ValueError:
            transport_mode = TransportMode.UNKNOWN
            
        connection = TrustConnection(
            workspace_id=workspace_id,
            operator_id=operator_id,
            intent=intent,
            status=ConnectionStatus.PENDING_REQUIREMENTS,
            transport_mode=transport_mode,
            requirements=requirements,
        )

        # 2. Create and Seal the ConnectionContext
        context = ConnectionContext(
            connection_id=connection.connection_id,
            trace=trace_context,
            transport=transport_context,
            identity_id=identity.identity_id,
            eat_jti=None,              # EAT is not issued yet
            eat_consumed=False,
            cappo_policy_id=None,
            cappo_decision_cached=False,
            cappo_decision_expires_at=None,
            pgl_receipt_id=None,
            trace_hops=[]
        )

        return connection, context
