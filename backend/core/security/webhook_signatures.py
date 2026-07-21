"""Signature verification helpers for external webhook providers."""

import base64
import hashlib
import hmac
import time


def verify_github_signature(body: bytes, secret: str, signature: str) -> bool:
    if not secret or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_resend_signature(
    body: bytes,
    secret: str,
    delivery_id: str,
    timestamp: str,
    signature: str,
    max_age_seconds: int = 300,
) -> bool:
    if not secret.startswith("whsec_") or not delivery_id or not timestamp or not signature:
        return False
    try:
        timestamp_int = int(timestamp)
        if abs(time.time() - timestamp_int) > max_age_seconds:
            return False
        encoded_secret = secret.removeprefix("whsec_")
        padding = "=" * (-len(encoded_secret) % 4)
        signing_secret = base64.b64decode(encoded_secret + padding)
    except (ValueError, base64.binascii.Error):
        return False

    signed_payload = f"{delivery_id}.{timestamp}.".encode("utf-8") + body
    expected = base64.b64encode(
        hmac.new(signing_secret, signed_payload, hashlib.sha256).digest()
    ).decode("ascii")
    return any(
        hmac.compare_digest(value.strip(), expected)
        for value in signature.split()
        for value in [value.removeprefix("v1,")]
    )
