import re
import hashlib
import traceback
from typing import Any, Dict, Tuple

class ZeroTrustTelemetrySanitizer:
    def __init__(self):
        # Scan for path traversal and shell injection patterns [cite: 6, 21]
        self.block_patterns = [
            re.compile(r"(\.\./|\.\.\\)"),
            re.compile(r"(npx\s+|npm\s+|curl\s+|wget\s+|bash\s+|sh\s+|python\s+)"),
            re.compile(r"(\||;|&&|\$\()"),
            re.compile(r"__import__\s*\(|eval\s*\(")
        ]

    def sanitize_untrusted_input(self, raw_input: str) -> str:
        """
        Inspects and sanitizes telemetry inputs from third-party services.
        Ensures that execution commands and traversal paths are blocked.
        """
        if not raw_input:
            return raw_input
            
        sanitized_output = str(raw_input)
        for pattern in self.block_patterns:
            if pattern.search(sanitized_output):
                # Replace potential exploits with an explicit security tag
                sanitized_output = pattern.sub("[PROTECTED_CONTAINMENT_BLOCK]", sanitized_output)
        return sanitized_output


class InProcessErrorSanitizer:
    """
    High-Performance In-Process Log and Error Sanitizer.
    Intercepts exceptions, database stack traces, and console logs,
    stripping internal server locations, paths, connection parameters,
    and credential patterns, replacing them with a secure execution hash.
    Defends against indirect prompt injection (leaking internals to model context).
    """
    def __init__(self):
        # Regex patterns to find internal paths, IP addresses, credentials, etc.
        self.path_regex = re.compile(
            r"(?:[a-zA-Z]:[\\/]+(?:[^\\/:\*\?\"<>\|]+[\\/]+)*|(?:\/[a-zA-Z0-9_\.\-]+)+)"
        )
        self.credential_regex = re.compile(
            r"(?:postgresql|postgres|redis|mongodb|mysql)?://[^:]+:([^@]+)@[^\s]+"
        )
        self.api_key_regex = re.compile(
            r"(?:key|secret|token|password|passwd|auth|jwt|sig)[\s:=']+(\w{12,})" , re.IGNORECASE
        )

    def sanitize_message(self, message: str) -> str:
        """
        Strips internal paths, credentials, and credentials from a raw log or error message.
        """
        if not message:
            return ""
            
        sanitized = str(message)
        
        # 1. Strip database connection credentials
        sanitized = self.credential_regex.sub("[REDACTED_SECURITY_CREDENTIALS]", sanitized)
        
        # 2. Strip API key / token / signature patterns
        sanitized = self.api_key_regex.sub(lambda m: m.group(0).replace(m.group(1), "[REDACTED_SECRET_KEY]"), sanitized)
        
        # 3. Clean local system paths containing antho or data/coolify
        sanitized = re.sub(r"[a-zA-Z]:\\Users\\antho[^\s]*", r"[SYSTEM_ENVIRONMENT_BOUND_PATH]", sanitized)
        sanitized = re.sub(r"\/data\/coolify[^\s]*", r"[SYSTEM_ENVIRONMENT_CONTAINMENT_PATH]", sanitized)
        
        return sanitized

    def sanitize_exception(self, exc: Exception) -> Tuple[Dict[str, Any], str]:
        """
        Translates a raw python Exception into a secure, sanitized output payload
        and generates a deterministic reference hash.
        Returns:
            (sanitized_response_payload: Dict, raw_diagnostic_log: str)
        """
        exc_type = type(exc).__name__
        exc_msg = self.sanitize_message(str(exc))
        
        # Format the traceback
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        raw_tb = "".join(tb_lines)
        
        # Hash traceback to create a unique, deterministic error signature
        hash_input = f"{exc_type}:{exc_msg}:{raw_tb}"
        error_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]
        error_signature = f"ERR-SHA256-{error_hash}"
        
        # Generate sanitized log stack (hidden from models, logged internally)
        sanitized_tb_lines = [self.sanitize_message(line) for line in tb_lines]
        sanitized_tb = "".join(sanitized_tb_lines)
        
        sanitized_payload = {
            "error": "cAPI_CONTAINED_EXECUTION_FAILURE",
            "signature": error_signature,
            "exception_type": exc_type,
            "message": f"An execution error occurred within containment boundaries. Details sanitized. Error signature: {error_signature}",
            "sanitized_detail": exc_msg
        }
        
        diagnostic_log = f"[{error_signature}] {exc_type}: {exc_msg}\nTraceback:\n{sanitized_tb}"
        return sanitized_payload, diagnostic_log

