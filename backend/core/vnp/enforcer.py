"""
VNP Safety Enforcer and Policy Engine.
Aligned with interlink-runtime (Rust prototype).
"""

import json
import logging
from typing import List, Optional, Tuple, Any
from jsonschema import validate, ValidationError

from backend.core.vnp.models import Capability, InvocationRequest, RiskLevel, CapabilityContext

logger = logging.getLogger(__name__)

class SafetyEnforcer:
    def __init__(self, capabilities: List[Capability]):
        self.registry = {cap.id: cap for cap in capabilities}

    def validate_invocation(self, req: InvocationRequest) -> Tuple[Optional[Capability], Optional[str]]:
        # 1. Discovery & Toolset Slicing
        cap = self.registry.get(req.capability_id)
        if not cap:
            return None, f"Capability '{req.capability_id}' not found in registry"

        if cap.toolset not in req.context.enabled_toolsets:
            return None, f"Toolset '{cap.toolset}' is not enabled for this agent session"

        # 2. Lockdown Mode
        if req.context.is_untrusted_content and cap.risk in [RiskLevel.High, RiskLevel.Critical]:
            return None, "Lockdown Mode: High-risk action blocked during untrusted content analysis"

        # 3. Schema Enforcement
        try:
            validate(instance=req.arguments, schema=cap.input_schema)
        except ValidationError as e:
            return None, f"Input validation failed: {e.message}"

        # 4. Push Protection
        error = self.detect_secrets(req.arguments)
        if error:
            return None, error

        return cap, None

    def detect_secrets(self, args: Any) -> Optional[str]:
        args_str = json.dumps(args)
        if "ghp_" in args_str or "sk-" in args_str:
            return "Security Violation: Credentials detected in tool arguments (Push Protection)"
        return None

    def sanitize_output(self, result: Any) -> Any:
        if isinstance(result, dict):
            new_dict = {}
            for key, value in result.items():
                lower_key = key.lower()
                if any(k in lower_key for k in ["secret", "token", "password", "key"]):
                    new_dict[key] = "[REDACTED]"
                else:
                    new_dict[key] = self.sanitize_output(value)
            return new_dict
        elif isinstance(result, list):
            return [self.sanitize_output(item) for item in result]
        else:
            return result

class PolicyDecision:
    def __init__(self, decision: str, reason: Optional[str] = None, message: Optional[str] = None):
        self.decision = decision # "Allow", "Deny", "RequireApproval"
        self.reason = reason
        self.message = message

class PolicyEngine:
    @staticmethod
    def evaluate(req: InvocationRequest, cap: Capability) -> PolicyDecision:
        # 1. Scope Validation (Mocked)
        if cap.id == "admin.delete_all":
            return PolicyDecision("Deny", reason="Actor lacks required scope: admin:write")

        # 2. Environment-Aware Policy
        env = req.context.environment
        risk = cap.risk

        if env == "prod" and risk == RiskLevel.High:
            return PolicyDecision("RequireApproval", message=f"Operation '{cap.title}' on production requires human authorization.")

        if risk == RiskLevel.Critical:
            return PolicyDecision("RequireApproval", message="Critical operation requires senior operator oversight.")

        if req.context.is_untrusted_content and risk == RiskLevel.Medium:
            return PolicyDecision("RequireApproval", message="Elevated risk while processing untrusted content requires verification.")

        return PolicyDecision("Allow")
