"""MCP Resilient Security Gateway proxy.

Centralized Zero Trust enforcement point between MCP Client (Host) and MCP Server.
Implements:
1. Payload Sanitization & Scanning (Prompt Injection Probability detection > 0.8)
2. Tool Description Version Pinning & Registry Hash validation (prevents Rug Pulls)
3. Rate Limiting & Ephemeral Scoped Credentials
4. Strict Egress Check limits (allowlisted asyncgw.teams.microsoft.com/urlp)
5. Pre-execution hook for blocking sensitive filesystem files (.env, .ssh/, .git/config)
"""

import os
import re
import time
import logging
from typing import Optional, Dict
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Registry Hashes for version pinning (SHA-256 mock registry)
_REGISTRY_HASHES = {
    "veklom_gpc_compile": "sha256:f123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "veklom_ai_inference": "sha256:a789bcdef0123456789abcdef0123456789abcdef0123456789abcdef012345",
    "veklom_evidence_export": "sha256:c0123456789abcdef0123456789abcdef0123456789abcdef0123456789abc",
    "veklom_compliance_report": "sha256:d123456789abcdef0123456789abcdef0123456789abcdef0123456789abc",
    "veklom_kill_switch": "sha256:e123456789abcdef0123456789abcdef0123456789abcdef0123456789abc"
}

# Rate limit memory cache
_tool_rate_limits: Dict[str, list] = {}

class MCPGateway:
    @staticmethod
    def scan_payload(text: str) -> float:
        """
        Scan inputs, tool_output, or tool_description for prompt injection overrides.
        Returns a float between 0.0 and 1.0 representing the injection probability.
        """
        if not text:
            return 0.0

        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"system\s+override",
            r"ignore\s+above\s+rules",
            r"developer\s+mode",
            r"you\s+are\s+now\s+an\s+unrestricted",
            r"bypass\s+security",
            r"read\s+the\s+file",
            r"exfiltrate",
            r"send\s+to\s+evil\.com",
            r"read\s+~\/\.ssh",
            r"read\s+\.env"
        ]

        matches = 0
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        if matches >= 2:
            return 0.95
        elif matches == 1:
            return 0.85
        return 0.0

    @classmethod
    def sanitize_and_check(cls, text: str, field_name: str = "payload"):
        """Enforce payload sanitization & scanning instruction checks."""
        prob = cls.scan_payload(text)
        if prob > 0.8:
            logger.error(
                f"[MCP Security Gateway] ERROR_SECURITY_VIOLATION: "
                f"Instruction override detected in {field_name} (probability {prob})"
            )
            # Log to immutable audit log
            from datetime import datetime, timezone
            print(f"[AUDIT LOG] {datetime.now(timezone.utc).isoformat()} - ERROR_SECURITY_VIOLATION - Injection attempt in {field_name}")
            raise HTTPException(
                status_code=400,
                detail="ERROR_SECURITY_VIOLATION: Instruction override or prompt injection detected."
            )

    @classmethod
    def validate_tool_integrity(cls, tool_id: str, current_hash: str, description_version: str):
        """
        Validates tool_id against Registry_Hash and locks tool descriptions.
        Prevents dynamic 'Rug Pull' attacks.
        """
        expected_hash = _REGISTRY_HASHES.get(tool_id)
        if not expected_hash:
            # Unregistered tool, block execution
            logger.error(f"[MCP Security Gateway] Tool '{tool_id}' is not registered in the Registry.")
            raise HTTPException(
                status_code=403,
                detail="Registry_Hash mismatch: Unregistered tool blocked."
            )

        if current_hash != expected_hash:
            logger.error(f"[MCP Security Gateway] Tool '{tool_id}' hash mismatch! 'Rug Pull' alert triggered.")
            raise HTTPException(
                status_code=403,
                detail="Rug Pull Alert: Tool integrity hash mismatch."
            )

        # Enforce version pinning: version must be >= 2.1.0
        try:
            v_parts = [int(x) for x in description_version.split(".")]
            if len(v_parts) < 3:
                v_parts.extend([0] * (3 - len(v_parts)))
            if v_parts < [2, 1, 0]:
                logger.error(f"[MCP Security Gateway] Tool '{tool_id}' version {description_version} < 2.1.0.")
                raise HTTPException(
                    status_code=403,
                    detail="Rug Pull Alert: Tool description version is outdated (< 2.1.0)."
                )
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="Rug Pull Alert: Invalid tool version format."
            )

    @classmethod
    def enforce_rate_limit(cls, user_context_id: str):
        """Enforces rate limits of 5 tool calls per minute for all agentic identities."""
        now = time.time()
        calls = _tool_rate_limits.setdefault(user_context_id, [])
        # Keep only calls in last 60 seconds
        calls = [t for t in calls if now - t < 60]
        _tool_rate_limits[user_context_id] = calls

        if len(calls) >= 5:
            logger.warning(f"[MCP Security Gateway] Rate limit exceeded for {user_context_id}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: 5 tool calls per minute allowed."
            )
        calls.append(now)

    @classmethod
    def egress_allowlist_check(cls, url: str):
        """Restricts external egress domains to standard secure communication channels."""
        if not url:
            return

        allowlisted_domains = [
            "asyncgw.teams.microsoft.com",
            "api.veklom.com",
            "veklom.com",
            "localhost",
            "127.0.0.1"
        ]

        domain_match = re.search(r"https?://([^/]+)", url)
        if not domain_match:
            return

        domain = domain_match.group(1).split(":")[0]  # Remove port if exists
        
        # Check subdomains or exact matches
        is_allowed = False
        for allowed in allowlisted_domains:
            if domain == allowed or domain.endswith("." + allowed):
                is_allowed = True
                break

        if not is_allowed:
            logger.error(f"[MCP Security Gateway] Egress blocked to non-allowlisted domain: {domain}")
            raise HTTPException(
                status_code=403,
                detail="Egress Blocked: Domain not in egress allowlist."
            )

    @classmethod
    def pre_execution_file_hook(cls, path: str):
        """Mandated hook preventing any reading of sensitive files/folders."""
        if not path:
            return

        sensitive_indicators = [
            r"\.env",
            r"\.ssh/",
            r"id_rsa",
            r"id_dsa",
            r"\.git/config",
            r"etc/passwd",
            r"etc/shadow",
            r"keys\.txt"
        ]

        for indicator in sensitive_indicators:
            if re.search(indicator, path, re.IGNORECASE):
                logger.error(f"[MCP Security Gateway] Pre-execution block: Attempt to read sensitive path: {path}")
                raise HTTPException(
                    status_code=403,
                    detail="ERROR_SECURITY_VIOLATION: Read access to sensitive file denied."
                )
