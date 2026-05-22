import base64
import os
from cryptography.fernet import Fernet
from backend.core.config.settings import settings

def get_fernet() -> Fernet:
    """Returns a Fernet instance configured with the ENCRYPTION_KEY from settings."""
    # Ensure the key is exactly 32 bytes and url-safe base64-encoded for Fernet.
    # If settings.ENCRYPTION_KEY is not set or not 32 bytes, we can derive it or pad it.
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable is not set")
    
    # Fernet requires a 32-byte base64 encoded string.
    # If the provided key is a hex string (e.g., 64 hex chars = 32 bytes), we must convert it.
    if len(key) == 64:
        try:
            key_bytes = bytes.fromhex(key)
            fernet_key = base64.urlsafe_b64encode(key_bytes)
        except ValueError:
            # Fallback if not valid hex
            fernet_key = base64.urlsafe_b64encode(key[:32].encode().ljust(32, b'\0'))
    else:
        # Just use the first 32 bytes of whatever it is, and base64 it
        key_bytes = key[:32].encode().ljust(32, b'\0')
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        
    return Fernet(fernet_key)

def encrypt_token(token: str) -> str:
    """Encrypts a string token using Fernet symmetric encryption."""
    if not token:
        return ""
    fernet = get_fernet()
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a previously encrypted string token."""
    if not encrypted_token:
        return ""
    fernet = get_fernet()
    try:
        return fernet.decrypt(encrypted_token.encode()).decode()
    except Exception:
        # Return empty string or raise if decryption fails
        return ""
