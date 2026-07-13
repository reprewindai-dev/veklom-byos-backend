import pytest
from fastapi import Request
from backend.core.amphoteric.extractor import extract_amphoteric_context

class MockRequest:
    def __init__(self, headers: dict):
        self.headers = headers
        self.client = type('obj', (object,), {'host': '127.0.0.1'})

def test_amphoteric_requires_spiffe_for_trust():
    """
    PROVES: A request that spoofs machine trust headers (X-Transport: mcp)
    but lacks a valid SPIFFE SVID is correctly categorized as having no authenticated_identity.
    """
    spoofed_headers = {
        "X-Transport": "mcp",
        "X-Protocol-Version": "2.0"
    }
    req = MockRequest(spoofed_headers)
    
    ctx = extract_amphoteric_context(req)
    
    # Heuristics detect the transport intent
    assert ctx.transport == "mcp"
    assert ctx.protocol_version == "2.0"
    
    # BUT trust is explicitly rejected because there is no SPIFFE SVID
    assert ctx.authenticated_identity is None, "Spoofed headers MUST NOT grant machine trust!"

def test_amphoteric_valid_spiffe_trust():
    """
    PROVES: A valid SPIFFE SVID passed from the mTLS terminator grants trust.
    """
    valid_headers = {
        "X-Transport": "mcp",
        "X-Spiffe-Id": "spiffe://veklom.io/ns/prod/sa/capi"
    }
    req = MockRequest(valid_headers)
    
    ctx = extract_amphoteric_context(req)
    
    assert ctx.transport == "mcp"
    assert ctx.authenticated_identity == "spiffe://veklom.io/ns/prod/sa/capi"
    
if __name__ == "__main__":
    print("Running Amphoteric Contract Tests...")
    test_amphoteric_requires_spiffe_for_trust()
    test_amphoteric_valid_spiffe_trust()
    print("[Contract Tests Passed]: Spoofed headers cannot bypass zero-trust boundary.")
