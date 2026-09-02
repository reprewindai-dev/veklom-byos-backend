import json
import hashlib
import unicodedata
import uuid
import re
from typing import Dict, Any

def vce_nfc_encode(obj):
    if isinstance(obj, str):
        return unicodedata.normalize('NFC', obj)
    elif isinstance(obj, dict):
        return {k: vce_nfc_encode(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [vce_nfc_encode(i) for i in obj]
    return obj

def vce_encode(payload: Dict[str, Any]) -> bytes:
    """Strict VEKLOM Canonical Semantic Encoding."""
    body = {k: v for k, v in payload.items() if k != "signature"}
    nfc_cleaned = vce_nfc_encode(body)
    return json.dumps(nfc_cleaned, separators=(',', ':'), sort_keys=True, ensure_ascii=False).encode('utf-8')

def hash_governed_request(payload: Dict[str, Any]) -> str:
    domain_separator = b"VEKLOM/VCE/1 GovernedRequest\0"
    return hashlib.sha256(domain_separator + vce_encode(payload)).hexdigest()

def hash_admission_attestation(payload: Dict[str, Any]) -> str:
    domain_separator = b"VEKLOM/VCE/1 AdmissionAttestation\0"
    return hashlib.sha256(domain_separator + vce_encode(payload)).hexdigest()

def hash_transition_receipt(payload: Dict[str, Any]) -> str:
    domain_separator = b"VEKLOM/VCE/1 TransitionReceipt\0"
    return hashlib.sha256(domain_separator + vce_encode(payload)).hexdigest()

def generate_fixtures():
    fixtures = []
    
    def sign_bytes(data: bytes) -> str:
        # Dummy 64-byte Ed25519 signature represented as 128-char hex string
        return "b" * 128

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
    
    req_commit = hash_governed_request(base_req)
    req_sig = sign_bytes(b"VEKLOM/VCE/1 GovernedRequest\0" + vce_encode(base_req))
    base_req["signature"] = req_sig
    
    base_attest = {
        "decision": "ALLOW",
        "effective_policy_identity_version": "urn:veklom:policy:finance:v1",
        "lifecycle_disposition": "RESERVED",
        "normalized_principal": "did:veklom:agent:123",
        "normalized_workspace": "urn:veklom:workspace:789",
        "reason": "Authorized by PGL",
        "request_commitment": req_commit,
        "reservation_identity": "555e4567-e89b-42d3-a456-426614174000",
        "resolved_authorization_digest": "a" * 64,
        "resolved_authorization_generation": 1,
        "signer_identity": "did:veklom:authority:1",
        "timestamp": "2026-09-01T12:00:01Z",
        "transition_id": base_req["transition_id"]
    }
    
    attest_commit = hash_admission_attestation(base_attest)
    attest_sig = sign_bytes(b"VEKLOM/VCE/1 AdmissionAttestation\0" + vce_encode(base_attest))
    base_attest["signature"] = attest_sig
    
    base_receipt = {
        "actual_effect": {
            "effect_status": "OBSERVED",
            "state_digest": "c" * 64,
            "mutated_fields": sorted(["/balance"])
        },
        "admission_commitment": attest_commit,
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
    deny_attest["signature"] = sign_bytes(b"VEKLOM/VCE/1 AdmissionAttestation\0" + vce_encode(deny_attest_body))
    
    receipt_deny = dict(base_receipt)
    receipt_deny["decision"] = "DENY"
    receipt_deny["outcome"] = "NOT_ATTEMPTED"
    receipt_deny["actual_effect"] = {
        "effect_status": "NONE",
        "state_digest": "",
        "mutated_fields": []
    }
    receipt_deny["admission_commitment"] = hash_admission_attestation(deny_attest)

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
    attest_mismatch["signature"] = sign_bytes(b"VEKLOM/VCE/1 AdmissionAttestation\0" + vce_encode(attest_mismatch_body))

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
    req_nfc = dict(base_req)
    req_nfc["e\u0301"] = "test"
    req_nfc["\u00e9"] = "test2"
    fixtures.append({
        "test_name": "NFC_COLLISION",
        # Python natively rejects this internally depending on structure,
        # but the JSON payload needs to be built manually or allowed 
        # to just encode it. We'll pass it as two distinct keys.
        "request": req_nfc,
        "attestation": None,
        "receipt": None,
        "expected_verdict": "INVALID"
    })

    with open("corpus.json", "w", encoding='utf-8') as f:
        json.dump(fixtures, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    generate_fixtures()
