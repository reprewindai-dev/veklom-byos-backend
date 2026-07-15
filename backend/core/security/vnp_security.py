import json
import base64
import hashlib
import logging
from typing import Dict, Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

class VNPSecurityError(Exception):
    """Raised when VNP signature verification fails."""
    pass

class VNPEventVerifier:
    """
    Verifies Ed25519 signatures on VNP Probe and Usage events.
    Follows the canonicalization rules:
    - Deterministic JSON ordering.
    - Matches raw payload.
    """

    @staticmethod
    def canonicalize_payload(payload: Dict[str, Any]) -> bytes:
        """
        Serialize JSON with deterministic key ordering before signing.
        This ensures the payload matches exactly what the producer signed.
        """
        return json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')

    @staticmethod
    def payload_digest(payload: Dict[str, Any]) -> str:
        """Return the SHA-256 digest of the unsigned payload envelope."""
        unsigned = dict(payload)
        unsigned.pop("signature", None)
        unsigned.pop("payload_digest", None)
        return hashlib.sha256(
            VNPEventVerifier.canonicalize_payload(unsigned)
        ).hexdigest()

    @staticmethod
    def verify_event_signature(payload: Dict[str, Any], public_key_base64: str) -> bool:
        """
        Verifies that the `signature_value` within the payload's `signature` block 
        was produced by the provided public key for the canonicalized `payload` (excluding the signature block).
        
        Args:
            payload: The full event envelope, including the `signature` block.
            public_key_base64: The base64-encoded Ed25519 public key of the producer.
            
        Returns:
            True if valid, raises VNPSecurityError if invalid.
        """
        try:
            # 1. Extract and validate the signature block
            signature_block = payload.get("signature", {})
            if signature_block.get("alg") != "Ed25519":
                raise VNPSecurityError(f"Unsupported signature algorithm: {signature_block.get('alg')}")
                
            sig_base64 = signature_block.get("sig")
            if not sig_base64:
                raise VNPSecurityError("Missing 'sig' in signature block.")

            # 2. Extract the raw bytes
            signature_bytes = base64.b64decode(sig_base64)
            pub_key_bytes = base64.b64decode(public_key_base64)

            # 3. Reconstruct the payload WITHOUT the signature block for verification
            payload_copy = dict(payload)
            payload_copy.pop("signature", None)
            canonical_data = VNPEventVerifier.canonicalize_payload(payload_copy)

            # 4. Verify using cryptography
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)
            public_key.verify(signature_bytes, canonical_data)
            return True

        except InvalidSignature:
            logger.error("VNP Event Signature verification failed. Potential tampering or replay.")
            raise VNPSecurityError("Invalid signature.")
        except Exception as e:
            logger.error(f"Error during VNP Event Signature verification: {e}")
            raise VNPSecurityError(f"Signature verification error: {str(e)}")
