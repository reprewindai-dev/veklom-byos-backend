import base64
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from cryptography.hazmat.primitives.asymmetric import rsa

def int_to_base64url(val: int) -> str:
    """Encode an integer as base64url byte string."""
    val_bytes = val.to_bytes((val.bit_length() + 7) // 8, byteorder='big')
    return base64.urlsafe_b64encode(val_bytes).decode('utf-8').rstrip('=')

class RSAKeyManager:
    """Manages rotating RSA public/private key pairs for token signing and JWKS verification."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RSAKeyManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.keys: Dict[str, Dict[str, Any]] = {}  # kid -> {private_key, public_key, created_at}
        self.current_kid: str = ""
        self.rotate_key()
        self._initialized = True

    def rotate_key(self) -> str:
        """Generate a new RSA key pair or load from persistent environment variable."""
        import os
        b64_key = os.environ.get("JWT_RSA_PRIVATE_KEY_B64")
        
        if b64_key and len(self.keys) == 0:
            # Load persistent key from environment
            from cryptography.hazmat.primitives import serialization
            import base64
            private_bytes = base64.b64decode(b64_key)
            private_key = serialization.load_pem_private_key(private_bytes, password=None)
            public_key = private_key.public_key()
            # Generate deterministic kid based on key to prevent rotation mismatch
            kid = f"veklom-sig-persistent"
        else:
            # Ephemeral fallback
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()
            kid = f"veklom-sig-{uuid.uuid4().hex[:12]}"
        
        self.keys[kid] = {
            "private_key": private_key,
            "public_key": public_key,
            "created_at": datetime.now(timezone.utc)
        }
        self.current_kid = kid
        
        # Keep only the latest 2 keys for rotation grace periods
        if len(self.keys) > 2:
            # Find the oldest kid
            sorted_kids = sorted(self.keys.keys(), key=lambda k: self.keys[k]["created_at"])
            del self.keys[sorted_kids[0]]
            
        return kid

    @property
    def active_key_id(self) -> str:
        """Return the current active signing key ID."""
        return self.current_kid

    def get_signing_key(self) -> Dict[str, Any]:
        """Return the current active key pair for signing."""
        return {
            "kid": self.current_kid,
            "private_key": self.keys[self.current_kid]["private_key"]
        }

    def get_jwks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get the public key set in JWKS format."""
        jwks_keys = []
        for kid, key_data in self.keys.items():
            pub = key_data["public_key"]
            numbers = pub.public_numbers()
            n = int_to_base64url(numbers.n)
            e = int_to_base64url(numbers.e)
            
            jwks_keys.append({
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": n,
                "e": e
            })
        return {"keys": jwks_keys}

# Singleton instance
key_manager = RSAKeyManager()
