import pytest
import time
from unittest import mock
import base64
import hmac
import hashlib

from backend.core.security.webhook_signatures import verify_resend_signature, verify_github_signature

# Valid mock data
VALID_BODY = b'{"event":"email.delivered"}'
VALID_DELIVERY_ID = "12345"
VALID_TIMESTAMP = "1672531200"

# Secret generation
RAW_SECRET = b"my-super-secret-key-123"
B64_SECRET = base64.b64encode(RAW_SECRET).decode("ascii").rstrip("=")
VALID_SECRET = f"whsec_{B64_SECRET}"

# Signature generation
_signed_payload = f"{VALID_DELIVERY_ID}.{VALID_TIMESTAMP}.".encode("utf-8") + VALID_BODY
_expected = base64.b64encode(hmac.new(RAW_SECRET, _signed_payload, hashlib.sha256).digest()).decode("ascii")
VALID_SIGNATURE = f"v1,{_expected}"

class TestVerifyResendSignature:
    @mock.patch("time.time", return_value=1672531200)
    def test_verify_resend_signature_success(self, mock_time):
        """Test a valid Resend webhook signature."""
        assert verify_resend_signature(
            body=VALID_BODY,
            secret=VALID_SECRET,
            delivery_id=VALID_DELIVERY_ID,
            timestamp=VALID_TIMESTAMP,
            signature=VALID_SIGNATURE,
        ) is True

    @mock.patch("time.time", return_value=1672531200)
    def test_verify_resend_signature_invalid_signature(self, mock_time):
        """Test with an invalid signature."""
        assert verify_resend_signature(
            body=VALID_BODY,
            secret=VALID_SECRET,
            delivery_id=VALID_DELIVERY_ID,
            timestamp=VALID_TIMESTAMP,
            signature="v1,invalidBase64Sig=",
        ) is False

    @mock.patch("time.time", return_value=1672531200)
    def test_verify_resend_signature_wrong_body(self, mock_time):
        """Test with modified body."""
        assert verify_resend_signature(
            body=b'{"event":"email.bounced"}',
            secret=VALID_SECRET,
            delivery_id=VALID_DELIVERY_ID,
            timestamp=VALID_TIMESTAMP,
            signature=VALID_SIGNATURE,
        ) is False

    def test_verify_resend_signature_expired(self):
        """Test with an expired timestamp (older than max_age_seconds)."""
        # Set current time to 5 minutes + 1 second after timestamp
        current_time = int(VALID_TIMESTAMP) + 301
        with mock.patch("time.time", return_value=current_time):
            assert verify_resend_signature(
                body=VALID_BODY,
                secret=VALID_SECRET,
                delivery_id=VALID_DELIVERY_ID,
                timestamp=VALID_TIMESTAMP,
                signature=VALID_SIGNATURE,
            ) is False

    @mock.patch("time.time", return_value=1672531200)
    def test_verify_resend_signature_future_timestamp_rejected(self, mock_time):
        """Test with a future timestamp (older than max_age_seconds)."""
        current_time = int(VALID_TIMESTAMP) - 301
        with mock.patch("time.time", return_value=current_time):
            assert verify_resend_signature(
                body=VALID_BODY,
                secret=VALID_SECRET,
                delivery_id=VALID_DELIVERY_ID,
                timestamp=VALID_TIMESTAMP,
                signature=VALID_SIGNATURE,
            ) is False

    def test_verify_resend_signature_missing_prefix(self):
        """Test secret missing 'whsec_' prefix."""
        assert verify_resend_signature(
            body=VALID_BODY,
            secret=B64_SECRET, # missing whsec_
            delivery_id=VALID_DELIVERY_ID,
            timestamp=VALID_TIMESTAMP,
            signature=VALID_SIGNATURE,
        ) is False

    def test_verify_resend_signature_missing_params(self):
        """Test missing required parameters."""
        assert verify_resend_signature(VALID_BODY, VALID_SECRET, "", VALID_TIMESTAMP, VALID_SIGNATURE) is False
        assert verify_resend_signature(VALID_BODY, VALID_SECRET, VALID_DELIVERY_ID, "", VALID_SIGNATURE) is False
        assert verify_resend_signature(VALID_BODY, VALID_SECRET, VALID_DELIVERY_ID, VALID_TIMESTAMP, "") is False

    def test_verify_resend_signature_invalid_timestamp(self):
        """Test with a non-integer timestamp."""
        assert verify_resend_signature(
            body=VALID_BODY,
            secret=VALID_SECRET,
            delivery_id=VALID_DELIVERY_ID,
            timestamp="not-an-int",
            signature=VALID_SIGNATURE,
        ) is False

    @mock.patch("time.time", return_value=1672531200)
    def test_verify_resend_signature_invalid_base64_secret(self, mock_time):
        """Test with an invalid base64 secret."""
        assert verify_resend_signature(
            body=VALID_BODY,
            secret="whsec_!@#invalid_b64",
            delivery_id=VALID_DELIVERY_ID,
            timestamp=VALID_TIMESTAMP,
            signature=VALID_SIGNATURE,
        ) is False

class TestVerifyGithubSignature:
    def test_verify_github_signature_success(self):
        body = b'{"action": "opened"}'
        secret = "my-github-secret"
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        assert verify_github_signature(body, secret, expected) is True

    def test_verify_github_signature_invalid_signature(self):
        body = b'{"action": "opened"}'
        secret = "my-github-secret"
        assert verify_github_signature(body, secret, "sha256=invalid") is False

    def test_verify_github_signature_missing_prefix(self):
        body = b'{"action": "opened"}'
        secret = "my-github-secret"
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        # Missing 'sha256=' prefix
        assert verify_github_signature(body, secret, expected) is False

    def test_verify_github_signature_empty_secret(self):
        body = b'{"action": "opened"}'
        assert verify_github_signature(body, "", "sha256=any") is False
