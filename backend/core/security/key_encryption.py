"""Symmetric encryption for BYOK provider keys at rest.

Uses Fernet (AES-128-CBC + HMAC-SHA256).
If PROVIDER_ENCRYPTION_KEY is not set, falls back to a deterministic key
derived from SECRET_KEY so keys are always recoverable within the same deployment.

Keys NEVER appear in logs. Always call decrypt() only in the provider router,
never in HTTP response bodies.
"""

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from backend.core.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = (settings.PROVIDER_ENCRYPTION_KEY or "").strip()
    if key:
        try:
            return Fernet(key.encode())
        except Exception:
            pass
    # Derive a stable Fernet key from SECRET_KEY
    raw = hashlib.sha256(settings.SECRET_KEY.encode() + b":provider_keys").digest()
    fernet_key = base64.urlsafe_b64encode(raw)
    return Fernet(fernet_key)


def encrypt_key(raw_key: str) -> str:
    """Encrypt a raw provider API key. Returns ciphertext string."""
    return _fernet().encrypt(raw_key.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """Decrypt a ciphertext back to a raw provider API key.
    Raises ValueError on tampered or invalid ciphertext.
    """
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Provider key decryption failed — key may be tampered") from e


def key_prefix(raw_key: str) -> str:
    """Return first 6 visible chars + '...' for safe UI display."""
    visible = raw_key[:6] if len(raw_key) >= 6 else raw_key
    return f"{visible}..."
