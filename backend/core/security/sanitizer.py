import re

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
