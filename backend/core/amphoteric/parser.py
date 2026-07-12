"""
Amphoteric Parser

Extracts standard Amphoteric and W3C contexts from raw headers.
This serves as the single source of truth for transport-level evaluation.
"""

from typing import Dict, Tuple
import secrets

from backend.core.schemas.trust.connection import TransportMode
from backend.core.schemas.trust.context import AmphotericTransportContext, W3CTraceContext

def extract_amphoteric_context(headers: Dict[str, str]) -> Tuple[W3CTraceContext, AmphotericTransportContext]:
    """
    Parses and builds the Amphoteric Transport and W3C Trace contexts from a raw header dictionary.
    Keys in the headers dictionary should be lowercase.
    """
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    # 1. Resolve W3C Trace Context
    traceparent = headers_lower.get("traceparent")
    if not traceparent:
        trace_id = secrets.token_hex(16)
        span_id = secrets.token_hex(8)
        traceparent = f"00-{trace_id}-{span_id}-01"
        
    tracestate = headers_lower.get("tracestate", "")
    
    trace_context = W3CTraceContext(
        traceparent=traceparent,
        tracestate=tracestate
    )

    # 2. Resolve Amphoteric Transport Context
    raw_transport = headers_lower.get("x-transport", "").lower()
    spiffe_id = headers_lower.get("x-spiffe-id")
    
    spiffe_verified = False
    if spiffe_id and spiffe_id.startswith("spiffe://veklom.io/"):
        spiffe_verified = True
        
    # Enforce the invariant: if not verified via SPIFFE (for internal m2m), 
    # we shouldn't blindly trust the requested transport mode unless it's a known generic fallback.
    # In production, this would be more nuanced depending on mTLS vs public UI.
    if spiffe_verified:
        try:
            transport_mode = TransportMode(raw_transport)
        except ValueError:
            transport_mode = TransportMode.UNKNOWN
    else:
        # Without SPIFFE, we degrade to UNKNOWN to fail-closed on zero-trust policies,
        # unless it is a UI / public origin which is governed by JWT (handled by PGL/cAPI).
        # We assume UNKNOWN here and let CAPPO decide if a human session is enough.
        transport_mode = TransportMode.UNKNOWN

    transport_context = AmphotericTransportContext(
        transport_mode=transport_mode.value,
        spiffe_verified=spiffe_verified,
        spiffe_id=spiffe_id if spiffe_verified else None,
        raw_transport_header=raw_transport if raw_transport else None,
    )

    return trace_context, transport_context
