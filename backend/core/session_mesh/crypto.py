"""
Veklom — Ed25519 signing upgrade for mesh_node.py
Replaces HMAC-SHA256 with asymmetric Ed25519.
Each zone has its own keypair. Public keys are registered in a shared key registry.
"""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
import json, hashlib


class ZoneKeyPair:
    """Ed25519 keypair for a zone enforcer node."""

    def __init__(self):
        self._private = Ed25519PrivateKey.generate()
        self._public  = self._private.public_key()

    def public_bytes(self) -> bytes:
        return self._public.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )

    def public_hex(self) -> str:
        return self.public_bytes().hex()

    def sign(self, payload: bytes) -> str:
        return self._private.sign(payload).hex()


class MeshKeyRegistry:
    """
    Shared registry of zone public keys.
    In production: backed by a PKI / secure key store.
    In single-process deployments: shared in-memory.
    """

    def __init__(self):
        self._keys: dict[str, bytes] = {}   # zone_id → raw public key bytes

    def register(self, zone_id: str, pub_hex: str):
        self._keys[zone_id] = bytes.fromhex(pub_hex)

    def verify(self, zone_id: str, payload: bytes, sig_hex: str) -> bool:
        raw = self._keys.get(zone_id)
        if not raw:
            return False
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub = Ed25519PublicKey.from_public_bytes(raw)
            pub.verify(bytes.fromhex(sig_hex), payload)
            return True
        except Exception:
            return False

    def zones(self) -> list[str]:
        return list(self._keys.keys())


def incident_payload(inc_dict: dict) -> bytes:
    """Canonical serialization for signing — sort_keys for determinism."""
    # Exclude signature field if present
    d = {k: v for k, v in inc_dict.items() if k != "signature"}
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def sign_incident_ed25519(inc_dict: dict, keypair: ZoneKeyPair) -> dict:
    payload = incident_payload(inc_dict)
    inc_dict["signature"] = keypair.sign(payload)
    return inc_dict


def verify_incident_ed25519(inc_dict: dict, registry: MeshKeyRegistry) -> bool:
    sig_hex   = inc_dict.get("signature")
    zone_id   = inc_dict.get("source_zone")
    if not sig_hex or not zone_id:
        return False
    payload = incident_payload(inc_dict)
    return registry.verify(zone_id, payload, sig_hex)
