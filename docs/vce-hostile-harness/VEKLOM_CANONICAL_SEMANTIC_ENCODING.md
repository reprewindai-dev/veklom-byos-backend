# Veklom Canonical Semantic Encoding (VCE) Profile

This profile defines a deterministic, strictly bounded serialization format for cryptographic hashing and verification of Veklom semantic artifacts (Governed Requests, Admission Attestations, Transition Receipts). 

It specifically diverges from generic RFC 8785 (JSON Canonicalization Scheme) by imposing stricter domain constraints required for governed consequence architecture.

## 1. Encoding Rules

1. **Character Encoding & Normalization:** MUST be strict UTF-8. All strings MUST be normalized to Unicode Normalization Form C (NFC). No byte order marks (BOM).
2. **Duplicate-Key Rejection:** Parsers MUST reject JSON payloads containing duplicate keys *before* object construction. Furthermore, verifiers MUST reject payloads if any member names collide *after* NFC normalization (e.g. `e` + combining acute accent vs `é`).
3. **Unknown-Field Behavior:** Unknown fields are strictly REJECTED. A verifier must return INVALID if a field not defined in the semantic schema is present.
4. **Number Types (Integer Range):** Floating-point numbers (`1.0`, `1e0`, `1E0`) and negative zero (`-0`) are strictly forbidden and MUST be rejected before conversion. All numbers MUST be signed 64-bit integers matching the grammar `0` or `-?[1-9][0-9]*`. Unbounded counters, monetary values, or epochs exceeding 64-bit bounds MUST be encoded as strings.
5. **String Escaping:** Printable Unicode characters (U+0020 and above) MUST be emitted directly as raw UTF-8, with the exception of `"` (U+0022), `\` (U+005C), which MUST be escaped as `\"` and `\\` respectively. The forward slash `/` (U+002F) MUST NOT be escaped. Control characters (U+0000 to U+001F) MUST be escaped using the 2-character sequence (`\b`, `\f`, `\n`, `\r`, `\t`) where defined, or otherwise as a lowercase hex unicode sequence (e.g., `\u000b`). The line separator (U+2028) and paragraph separator (U+2029) MUST be emitted as raw UTF-8 bytes and NOT escaped.
6. **Arrays:** Arrays are permitted. Array order is semantically significant and MUST be strictly preserved unless the schema explicitly defines sorting rules (e.g., `mutated_fields`).
7. **Required vs Optional Fields:** 
   - Required fields MUST be present (they cannot be omitted or `null`).
   - Optional fields with no value MUST be omitted entirely from the serialized payload.
   - Explicit `null` values are INVALID unless the schema explicitly defines a field as strictly nullable (distinguishing between "absent" and "explicitly cleared").
8. **Key Ordering:** All dictionary/object keys MUST be sorted lexicographically by their UTF-8 byte values (not locale-specific alphabetical sorts). Sorting MUST occur after NFC normalization.
9. **Whitespace:** All structural whitespace (spaces, tabs, newlines) outside of string literals MUST be omitted. Separators MUST be exactly `,` and `:`.
10. **Timestamps:** MUST strictly adhere to a valid Gregorian ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SSZ`. Fractional seconds are explicitly FORBIDDEN. Leap seconds are explicitly FORBIDDEN (the seconds value must be `00` through `59`). The uppercase `T` and `Z` are mandatory. The date must be a valid Gregorian calendar date (accounting for leap years). Any deviation is INVALID.
11. **UUID Syntax:** Any field expecting a UUID MUST be encoded in the canonical 8-4-4-4-12 lowercase textual format (e.g., `123e4567-e89b-42d3-a456-426614174000`). Only UUIDv4 and UUIDv7 are permitted. The RFC 4122 variant bits (10xx) MUST be correct. Other versions (e.g. v1) or uppercase letters are strictly INVALID.

## 2. Cryptographic Byte Profile

Verifiers MUST enforce the following byte-level exactness constraints:
- **`hex_string`:** A string composed exactly of `[0-9a-f]`. No `0x` prefix. No uppercase letters.
- **SHA-256 Digest:** Exactly 32 bytes of raw entropy, represented externally as a 64-character `hex_string`.
- **Ed25519 Signature:** Exactly 64 bytes of raw entropy, represented externally as a 128-character `hex_string`.
- **Ed25519 Public Key:** Exactly 32 bytes of raw entropy, represented externally as a 64-character `hex_string`.
- **Domain Separators:** Must be evaluated as exact ASCII/UTF-8 byte strings. The suffix `\0` represents exactly one `0x00` byte.
- **Ed25519 Profile:** MUST use standard Ed25519 (PureEdDSA), NOT Ed25519ph. The verifier MUST cryptographically sign the raw 32 SHA-256 bytes, NOT the ASCII bytes of the 64-character hex rendering.
- **Malformed Signatures/Keys:** Non-canonical Ed25519 signatures (e.g. non-canonical `S` scalars) or non-canonical public keys MUST be rejected as INVALID.

## 3. Artifact Structures

### Governed Request
*Binds intended semantics and expected authorization artifact/generation.*
**Semantic Invariant:** A verifier MUST enforce the strict binding of the authorization fields. `authorization_reference` MUST identify the artifact/profile/instance according to the domain dictionary. `authorization_digest` MUST be `SHA-256(exactly defined authorization-artifact bytes)`. `authorization_generation` MUST match the generation embedded/signed by that same authority artifact.
```json
{
  "audience": "string",
  "authorization_digest": "hex_string",
  "authorization_generation": "integer",
  "authorization_reference": "string",
  "intent": "string",
  "normalized_payload_digest": "hex_string",
  "operation": "string",
  "policy_identity_version": "string",
  "principal_binding": "string",
  "replay_identity": "string",
  "signature": "hex_string",
  "signer_identity": "string",
  "target_resource": "string",
  "timestamp": "ISO8601",
  "transition_id": "UUID",
  "workspace": "string"
}
```

### Admission Attestation
*Independently records what the authorization boundary actually resolved, evaluated, decided and reserved.*
```json
{
  "decision": "ALLOW|DENY",
  "effective_policy_identity_version": "string",
  "lifecycle_disposition": "string",
  "normalized_principal": "string",
  "normalized_workspace": "string",
  "reason": "string",
  "request_commitment": "hex_string",
  "reservation_identity": "string",
  "resolved_authorization_digest": "hex_string",
  "resolved_authorization_generation": "integer",
  "signature": "hex_string",
  "signer_identity": "string",
  "timestamp": "ISO8601",
  "transition_id": "UUID"
}
```

### Transition Receipt
*Records the actual outcome with strict separation between decision and state.*
```json
{
  "actual_effect": {
    "effect_status": "NONE|OBSERVED|UNKNOWN",
    "mutated_fields": ["string"],
    "state_digest": "hex_string"
  },
  "admission_commitment": "hex_string",
  "decision": "ALLOW|DENY",
  "outcome": "NOT_ATTEMPTED|SUCCESS|FAILED|OUTCOME_UNKNOWN",
  "timestamp": "ISO8601",
  "transition_id": "UUID"
}
```
*Note:*
- `DENY` implies `NOT_ATTEMPTED`.
- `ALLOW` implies one of `SUCCESS`, `FAILED`, or `OUTCOME_UNKNOWN`.
- `actual_effect` MUST be a discriminated state.
- `NONE`: Valid only for `DENY` or `NOT_ATTEMPTED`. `state_digest` MUST be `""` and `mutated_fields` MUST be `[]`.
- `OBSERVED`: Target state change was definitively measured. `state_digest` and `mutated_fields` MUST be populated if mutations occurred. `mutated_fields` elements MUST be strictly unique RFC 6901 JSON Pointers, sorted lexicographically by their UTF-8 byte values.
- `UNKNOWN`: The system crashed or partitioned after commit but before observation. `state_digest` MUST be `""` and `mutated_fields` MUST be `[]`. This refuses to assert the target state remained unchanged.

## 4. Cryptographic Hashing & Domain Separation

To compute the commitment of a payload, artifact-specific domain separators MUST be used to prevent cross-context substitution attacks.

**Crucially, to prevent circular definitions, any `signature` field MUST be detached before computing the commitment.**
The canonical bytes are computed over the *unsigned body* (the artifact object exactly as defined, but with the `signature` key entirely omitted). 

```text
artifact_body = Artifact object minus "signature" key
commitment = SHA-256(DomainSeparator || VCE(artifact_body))
signature = Ed25519.Sign(private_key, commitment)
```

**Domain Separators:**

**Governed Request:**
`SHA-256("VEKLOM/VCE/1 GovernedRequest\0" || VCE(request_body))`

**Admission Attestation:**
`SHA-256("VEKLOM/VCE/1 AdmissionAttestation\0" || VCE(attestation_body))`

**Transition Receipt:**
`SHA-256("VEKLOM/VCE/1 TransitionReceipt\0" || VCE(receipt_body))`

## 5. Cross-Artifact Semantic Verifier Contract

The verifier MUST return strictly `VALID`, `INVALID`, or `INDETERMINATE`.
The verifier MUST return the complete, deterministically ordered failure set, not just the first failure.

### Verdict Definitions
- **INVALID**: Represents a definitive, unrecoverable violation (e.g., malformed JSON, unknown field, bad signature, commitment mismatch, wrong workspace, revoked authorization, cross-artifact mismatch).
- **INDETERMINATE**: Represents a failure due to missing necessary state that prevents evaluation (e.g., required freshness snapshot absent, required external target evidence unavailable, trusted key status unavailable if the Trust Profile says so).
- **VALID**: Fully validated payload matching all rules.

### Validation Matrix

**1. Binding Chain**
- `attestation.request_commitment` MUST exactly equal the `GovernedRequest` unsigned-body commitment.
- `receipt.admission_commitment` MUST exactly equal the `AdmissionAttestation` unsigned-body commitment.
- `request.transition_id` MUST equal `attestation.transition_id`, which MUST equal `receipt.transition_id`.

**2. Decision Alignment**
- `receipt.decision` MUST exactly match `attestation.decision`.

**3. State on ALLOW**
If `attestation.decision` == `ALLOW`:
- `attestation.resolved_authorization_digest` MUST equal `request.authorization_digest`.
- `attestation.resolved_authorization_generation` MUST equal `request.authorization_generation`.
- `attestation.normalized_principal` and `attestation.normalized_workspace` MUST satisfy the request bindings.
- `attestation.effective_policy_identity_version` MUST satisfy the request's policy identity requirement.

**4. State on DENY**
If `attestation.decision` == `DENY`:
- The attestation MAY report a mismatched `resolved_authorization_digest` or `resolved_authorization_generation` (e.g., if the request was stale).
- The transaction MUST halt. The `receipt` MUST report `outcome` == `NOT_ATTEMPTED` and `effect_status` == `NONE`.

## 6. Hostile Independence Handoff (The Public Bundle)

The independent verifier (Rust/Go) MUST NOT be given signing private keys and MUST NOT consume precomputed commitment values as an oracle. The verifier derives canonical bytes and hashes itself, then verifies supplied Ed25519 signatures with public keys.

The immutable public bundle provided to the foreign implementation consists of:
- VCE specification
- Semantic schemas
- Fixture manifest
- Governed Request fixtures
- Admission Attestation fixtures
- Transition Receipt fixtures
- Authorization artifact bytes
- Public trust keys / trust profile
- Evidence fixtures
- Optional signed freshness/revocation snapshots
- Expected verdict + expected failed-check identifiers
