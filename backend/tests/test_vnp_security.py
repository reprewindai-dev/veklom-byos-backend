import pytest
import base64
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from backend.core.security.vnp_security import VNPEventVerifier, VNPSecurityError
from backend.db.models.vnp import VnpNodeHeartbeat

def test_vnp_event_verifier():
    # 1. Generate a test keypair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    pub_key_base64 = base64.b64encode(public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )).decode('utf-8')

    # 2. Create a payload
    payload = {
        "event_id": "probe_123",
        "measurement": {"total_ms": 45}
    }

    # 3. Canonicalize and Sign
    canonical_data = VNPEventVerifier.canonicalize_payload(payload)
    sig_bytes = private_key.sign(canonical_data)
    sig_base64 = base64.b64encode(sig_bytes).decode('utf-8')

    # 4. Attach signature block
    full_payload = dict(payload)
    full_payload["signature"] = {
        "alg": "Ed25519",
        "key_id": "worker_key_1",
        "sig": sig_base64
    }

    # 5. Verify Success
    assert VNPEventVerifier.verify_event_signature(full_payload, pub_key_base64) == True

    # 6. Verify Tampering Failure
    tampered_payload = dict(full_payload)
    tampered_payload["measurement"]["total_ms"] = 10  # tampered
    with pytest.raises(VNPSecurityError):
        VNPEventVerifier.verify_event_signature(tampered_payload, pub_key_base64)


def test_payload_digest_uses_unsigned_canonical_payload():
    payload = {
        "region": "de-falkenstein",
        "timestamp": "2026-07-15T00:00:00+00:00",
        "payload_digest": "ignored",
        "signature": {"alg": "Ed25519", "sig": "ignored"},
    }

    assert VNPEventVerifier.payload_digest(payload) == VNPEventVerifier.payload_digest(
        {
            "timestamp": "2026-07-15T00:00:00+00:00",
            "region": "de-falkenstein",
        }
    )


def test_vnp_node_heartbeat_requires_signed_evidence_fields():
    columns = VnpNodeHeartbeat.__table__.columns

    assert columns["heartbeat_id"].nullable is False
    assert columns["sequence"].nullable is False
    assert columns["payload_digest"].nullable is False
