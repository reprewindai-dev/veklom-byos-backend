import base64
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class Ed25519KeyManager:
    """Generates and manages Ed25519 key pairs for PGL identities."""

    @staticmethod
    def generate_key_pair() -> Tuple[str, str]:
        """
        Generate a new Ed25519 key pair.
        Returns:
            Tuple[str, str]: (private_key_base64, public_key_base64)
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize private key to PKCS8 PEM format, then encode as base64url string
        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        priv_b64 = base64.urlsafe_b64encode(priv_bytes).decode('utf-8').rstrip('=')

        # Serialize public key to SubjectPublicKeyInfo, then encode as base64url string
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        pub_b64 = base64.urlsafe_b64encode(pub_bytes).decode('utf-8').rstrip('=')

        return priv_b64, pub_b64
