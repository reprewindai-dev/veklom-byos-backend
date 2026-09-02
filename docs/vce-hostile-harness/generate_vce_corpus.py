import json
import hashlib
import unicodedata
from cryptography.hazmat.primitives.asymmetric import ed25519
from typing import Dict, Any, List

def check_no_floats(obj):
    if isinstance(obj, float):
        raise ValueError("Floats are strictly forbidden in VCE")
    elif isinstance(obj, dict):
        for v in obj.values():
            check_no_floats(v)
    elif isinstance(obj, list):
        for v in obj:
            check_no_floats(v)

def vce_nfc_normalize_and_check_keys(obj):
    if isinstance(obj, str):
        return unicodedata.normalize('NFC', obj)
    elif isinstance(obj, dict):
        normalized_dict = {}
        for k, v in obj.items():
            if v is None:
                continue
            norm_k = unicodedata.normalize('NFC', k)
            if norm_k in normalized_dict:
                raise ValueError(f"NFC Key Collision detected for key: {norm_k}")
            normalized_dict[norm_k] = vce_nfc_normalize_and_check_keys(v)
        return normalized_dict
    elif isinstance(obj, list):
        return [vce_nfc_normalize_and_check_keys(i) for i in obj]
    return obj

def vce_encode(payload: Dict[str, Any]) -> bytes:
    """Strict VEKLOM Canonical Semantic Encoding."""
    body = {k: v for k, v in payload.items() if k != "signature"}
    check_no_floats(body)
    nfc_cleaned = vce_nfc_normalize_and_check_keys(body)
    
    # We use json.dumps with separators to remove whitespace, sort_keys to ensure byte ordering
    # Note: Python's sort_keys sorts lexicographically by unicode code points, which matches UTF-8 byte sort for NFC.
    encoded = json.dumps(nfc_cleaned, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
    return encoded.encode('utf-8')

def hash_governed_request(payload: Dict[str, Any]) -> bytes:
    domain_separator = b"VEKLOM/VCE/1 GovernedRequest\0"
    return hashlib.sha256(domain_separator + vce_encode(payload)).digest()

def hash_admission_attestation(payload: Dict[str, Any]) -> bytes:
    domain_separator = b"VEKLOM/VCE/1 AdmissionAttestation\0"
    return hashlib.sha256(domain_separator + vce_encode(payload)).digest()

def hash_transition_receipt(payload: Dict[str, Any]) -> bytes:
    domain_separator = b"VEKLOM/VCE/1 TransitionReceipt\0"
    return hashlib.sha256(domain_separator + vce_encode(payload)).digest()

def generate_fixtures():
    # Generate Ed25519 Keys
    private_key = ed25519.Ed25519PrivateKey.generate()
    # In a real scenario we'd export public key too
    
    def sign_bytes(commitment: bytes) -> str:
        # VCE dictates we sign the 32-byte raw SHA-256 digest
        sig = private_key.sign(commitment)
        return sig.hex()

    fixtures = []
    
    base_req = {
        "audience": "urn:veklom:harness:target",
        "authorization_digest": "a" * 64,
        "authorization_generation": 1,
        "authorization_reference": "urn:veklom:pgl:auth:1",
        "intent": "withdraw_funds",
        "normalized_payload_digest": "b" * 64,
        "operation": "withdraw",
        "policy_identity_version": "urn:veklom:policy:finance:v1",
        "principal_binding": "did:veklom:agent:123",
        "replay_identity": "123e4567-e89b-42d3-a456-426614174000",
        "target_resource": "urn:veklom:account:456",
        "timestamp": "2026-09-01T12:00:00Z",
        "transition_id": "987e6543-e21b-42d3-a456-426614174000",
        "workspace": "urn:veklom:workspace:789",
        "signer_identity": "did:veklom:agent:123"
    }
    
    req_commit_bytes = hash_governed_request(base_req)
    base_req["signature"] = sign_bytes(req_commit_bytes)
    
    base_attest = {
        "decision": "ALLOW",
        "effective_policy_identity_version": "urn:veklom:policy:finance:v1",
        "lifecycle_disposition": "RESERVED",
        "normalized_principal": "did:veklom:agent:123",
        "normalized_workspace": "urn:veklom:workspace:789",
        "reason": "Authorized by PGL",
        "request_commitment": req_commit_bytes.hex(),
        "reservation_identity": "555e4567-e89b-42d3-a456-426614174000",
        "resolved_authorization_digest": "a" * 64,
        "resolved_authorization_generation": 1,
        "signer_identity": "did:veklom:authority:1",
        "timestamp": "2026-09-01T12:00:01Z",
        "transition_id": base_req["transition_id"]
    }
    
    attest_commit_bytes = hash_admission_attestation(base_attest)
    base_attest["signature"] = sign_bytes(attest_commit_bytes)
    
    base_receipt = {
        "actual_effect": {
            "effect_status": "OBSERVED",
            "mutated_fields": sorted(["/balance"]),
            "state_digest": "c" * 64
        },
        "admission_commitment": attest_commit_bytes.hex(),
        "decision": "ALLOW",
        "outcome": "SUCCESS",
        "timestamp": "2026-09-01T12:00:02Z",
        "transition_id": base_req["transition_id"]
    }
    
    fixtures.append({
        "test_name": "BASELINE_VALID",
        "request": base_req,
        "attestation": base_attest,
        "receipt": base_receipt,
        "expected_verdict": "VALID"
    })
    
    # 1. Invalid UUID v1
    req_v1 = dict(base_req)
    req_v1["transition_id"] = "123e4567-e89b-12d3-a456-426614174000"
    fixtures.append({
        "test_name": "INVALID_UUID_V1",
        "request": req_v1,
        "attestation": None,
        "receipt": None,
        "expected_verdict": "INVALID"
    })

    # 2. Invalid Timestamp (Fractional)
    req_ts = dict(base_req)
    req_ts["timestamp"] = "2026-09-01T12:00:00.123Z"
    fixtures.append({
        "test_name": "INVALID_TIMESTAMP_FRACTIONAL",
        "request": req_ts,
        "attestation": None,
        "receipt": None,
        "expected_verdict": "INVALID"
    })

    # 3. OUTCOME_UNKNOWN with non-empty mutation
    receipt_unk = dict(base_receipt)
    receipt_unk["actual_effect"] = {
        "effect_status": "UNKNOWN",
        "state_digest": "c" * 64,
        "mutated_fields": ["/balance"]
    }
    fixtures.append({
        "test_name": "INVALID_OUTCOME_UNKNOWN_WITH_STATE",
        "request": base_req,
        "attestation": base_attest,
        "receipt": receipt_unk,
        "expected_verdict": "INVALID"
    })

    # 4. DENY test case
    deny_attest = dict(base_attest)
    deny_attest["decision"] = "DENY"
    deny_attest_body = dict(deny_attest)
    if "signature" in deny_attest_body:
        del deny_attest_body["signature"]
    deny_attest["signature"] = sign_bytes(hash_admission_attestation(deny_attest_body))
    
    receipt_deny = dict(base_receipt)
    receipt_deny["decision"] = "DENY"
    receipt_deny["outcome"] = "NOT_ATTEMPTED"
    receipt_deny["actual_effect"] = {
        "effect_status": "NONE",
        "state_digest": "",
        "mutated_fields": []
    }
    receipt_deny["admission_commitment"] = hash_admission_attestation(deny_attest).hex()

    fixtures.append({
        "test_name": "BASELINE_DENY",
        "request": base_req,
        "attestation": deny_attest,
        "receipt": receipt_deny,
        "expected_verdict": "VALID"
    })

    # 5. Cross-artifact mismatch
    attest_mismatch = dict(base_attest)
    attest_mismatch["request_commitment"] = "f" * 64
    attest_mismatch_body = dict(attest_mismatch)
    del attest_mismatch_body["signature"]
    attest_mismatch["signature"] = sign_bytes(hash_admission_attestation(attest_mismatch_body))

    fixtures.append({
        "test_name": "CROSS_ARTIFACT_COMMITMENT_MISMATCH",
        "request": base_req,
        "attestation": attest_mismatch,
        "receipt": base_receipt,
        "expected_verdict": "INVALID"
    })

    # 6. INDETERMINATE case
    fixtures.append({
        "test_name": "INDETERMINATE_MISSING_ATTESTATION",
        "request": base_req,
        "attestation": None,
        "receipt": None,
        "expected_verdict": "INDETERMINATE"
    })
    
    # 7. NFC Collision
    # We will simulate this by passing raw dict with collision. 
    # Python dicts allow distinct keys if they have different byte reps,
    # so "e\u0301" and "\u00e9" are distinct keys in Python, but VCE NFC normalization will collide them.
    # Our vce_encode function correctly throws an error.
    # For the corpus, we want the generated JSON to actually contain the pre-NFC collision.
    # To do this, we manually build a JSON string since vce_encode will block it.
    
    nfc_req_body = dict(base_req)
    del nfc_req_body["signature"]
    nfc_req_body["e\u0301"] = "test"
    nfc_req_body["\u00e9"] = "test2"
    
    # Manually encode it to bypass our own encoder's collision guard
    raw_nfc_json = json.dumps(nfc_req_body, separators=(',', ':'), sort_keys=True, ensure_ascii=False).encode('utf-8')
    raw_nfc_commit = hashlib.sha256(b"VEKLOM/VCE/1 GovernedRequest\0" + raw_nfc_json).digest()
    
    nfc_req = dict(nfc_req_body)
    nfc_req["signature"] = sign_bytes(raw_nfc_commit)

    fixtures.append({
        "test_name": "NFC_COLLISION",
        "request": nfc_req,
        "attestation": None,
        "receipt": None,
        "expected_verdict": "INVALID"
    })

    with open("corpus.json", "w", encoding='utf-8') as f:
        json.dump(fixtures, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    generate_fixtures()
