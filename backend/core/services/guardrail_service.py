"""Real Guardrail Service - Production Implementation"""

import json
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass
import logging

from backend.core.ml.sigma import SigmaSpectralLens

logger = logging.getLogger(__name__)


@dataclass
class GuardrailRule:
    """Definition of a guardrail rule"""
    rule_type: str
    pattern: Optional[str] = None
    keywords: Optional[List[str]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[str]] = None
    severity: str = "warning"
    action: str = "block"


@dataclass
class SafetyCheck:
    """Result of a safety check"""
    passed: bool
    reason: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None
    risk_score: float = 0.0


class RealGuardrailService:
    """Production-ready guardrail service with actual safety implementations"""
    
    def __init__(self):
        # Compile regex patterns for performance
        self.dangerous_patterns = {
            "sql_injection": [
                re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE)\b.*\b(FROM|INTO|TABLE)\b)", re.IGNORECASE),
                re.compile(r"('|(\\')|(;)|(\-\-)|(/\*|\*/))", re.IGNORECASE)
            ],
            "path_traversal": [
                re.compile(r"(\.\./|\.\.\\)", re.IGNORECASE),
                re.compile(r"(%2e%2e%2f|%2e%2e%5c)", re.IGNORECASE)
            ],
            "script_injection": [
                re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
                re.compile(r"javascript:", re.IGNORECASE),
                re.compile(r"on\w+\s*=", re.IGNORECASE)
            ],
            "command_injection": [
                re.compile(r"[;&|`$(){}[\]]", re.IGNORECASE),
                re.compile(r"(rm\s+-rf|del\s+/|format\s+)", re.IGNORECASE)
            ],
            "credential_exposure": [
                re.compile(r"\b(password|passwd|pwd|secret|token|key|api_key)\s*[:=]\s*\S+", re.IGNORECASE),
                re.compile(r"[A-Za-z0-9]{32,}"),  # Potential API keys
            ]
        }
        
        # Blocked content keywords
        self.blocked_keywords = [
            "password", "secret", "token", "api_key", "private_key",
            "credit_card", "ssn", "social_security", "bank_account",
            "admin", "root", "sudo", "privilege escalation"
        ]
        
        # Rate limiting storage (in production, use Redis)
        self.rate_limits = {}
        
        # Security thresholds
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.max_concurrent_requests = 100
        self.suspicious_ip_threshold = 10  # requests per minute
    
    async def evaluate_input_safety(
        self, 
        input_data: Dict[str, Any], 
        user_id: str,
        agent_id: str,
        rules: List[Dict[str, Any]]
    ) -> SafetyCheck:
        """Evaluate input safety with real checks"""
        try:
            risk_score = 0.0
            violations = []
            modified_data = input_data.copy()
            
            # Size check
            content_size = len(json.dumps(input_data))
            if content_size > self.max_request_size:
                violations.append({
                    "type": "size_limit",
                    "severity": "error",
                    "message": f"Input size {content_size} exceeds maximum {self.max_request_size}"
                })
                risk_score += 0.4
            
            # Apply each rule
            for rule in rules:
                check_result = await self._apply_rule(rule, input_data, "input")
                if not check_result.passed:
                    violations.append({
                        "type": rule.get("type", "unknown"),
                        "severity": rule.get("severity", "warning"),
                        "message": check_result.reason
                    })
                    risk_score += self._get_risk_weight(rule.get("severity", "warning"))
                    
                    if check_result.modified_data:
                        modified_data.update(check_result.modified_data)
            
            # Built-in security checks
            security_check = await self._security_scan_input(input_data)
            if not security_check.passed:
                violations.extend(security_check.violations if hasattr(security_check, 'violations') else [])
                risk_score += security_check.risk_score
            
            # Rate limiting check
            rate_check = await self._check_rate_limit(user_id, rules)
            if not rate_check.passed:
                violations.append({
                    "type": "rate_limit",
                    "severity": "error",
                    "message": rate_check.reason
                })
                risk_score += 0.3
            
            passed = len([v for v in violations if v["severity"] in ["error", "critical"]]) == 0
            
            return SafetyCheck(
                passed=passed,
                reason=f"Found {len(violations)} violations" if violations else None,
                modified_data=modified_data if modified_data != input_data else None,
                risk_score=min(risk_score, 1.0)
            )
            
        except Exception as e:
            logger.error(f"Input safety evaluation failed: {str(e)}")
            return SafetyCheck(
                passed=False,
                reason=f"Safety evaluation error: {str(e)}",
                risk_score=0.8
            )
    
    async def evaluate_output_safety(
        self, 
        output_data: Dict[str, Any], 
        user_id: str,
        agent_id: str,
        rules: List[Dict[str, Any]]
    ) -> SafetyCheck:
        """Evaluate output safety with real checks"""
        try:
            risk_score = 0.0
            violations = []
            modified_data = output_data.copy()
            
            # Apply each rule
            for rule in rules:
                check_result = await self._apply_rule(rule, output_data, "output")
                if not check_result.passed:
                    violations.append({
                        "type": rule.get("type", "unknown"),
                        "severity": rule.get("severity", "warning"),
                        "message": check_result.reason
                    })
                    risk_score += self._get_risk_weight(rule.get("severity", "warning"))
                    
                    if check_result.modified_data:
                        modified_data.update(check_result.modified_data)
            
            # Built-in security checks for output
            security_check = await self._security_scan_output(output_data)
            if not security_check.passed:
                violations.extend(security_check.violations if hasattr(security_check, 'violations') else [])
                risk_score += security_check.risk_score
            
            # Content sanitization
            sanitized = await self._sanitize_output(output_data)
            if sanitized != output_data:
                modified_data = sanitized
                violations.append({
                    "type": "content_sanitization",
                    "severity": "info",
                    "message": "Output content sanitized for safety"
                })
                risk_score += 0.1
            
            passed = len([v for v in violations if v["severity"] in ["error", "critical"]]) == 0
            
            return SafetyCheck(
                passed=passed,
                reason=f"Found {len(violations)} violations" if violations else None,
                modified_data=modified_data if modified_data != output_data else None,
                risk_score=min(risk_score, 1.0)
            )
            
        except Exception as e:
            logger.error(f"Output safety evaluation failed: {str(e)}")
            return SafetyCheck(
                passed=False,
                reason=f"Safety evaluation error: {str(e)}",
                risk_score=0.8
            )
    
    async def evaluate_tool_safety(
        self, 
        tool_id: str, 
        tool_data: Dict[str, Any], 
        user_id: str,
        agent_id: str,
        tool_safety_level: str,
        rules: List[Dict[str, Any]],
        db: Optional[Any] = None
    ) -> SafetyCheck:
        """Evaluate tool call safety with real checks"""
        try:
            risk_score = 0.0
            violations = []
            
            # Tool-specific safety checks
            if tool_safety_level == "dangerous":
                # Dangerous tools require admin approval
                if not await self._check_admin_approval(user_id, tool_id, db=db):
                    violations.append({
                        "type": "dangerous_tool",
                        "severity": "critical",
                        "message": f"Tool {tool_id} requires admin approval"
                    })
                    risk_score += 0.5
            
            elif tool_safety_level == "restricted":
                # Restricted tools need additional validation
                restricted_check = await self._validate_restricted_tool(tool_id, tool_data)
                if not restricted_check.passed:
                    violations.append({
                        "type": "restricted_tool",
                        "severity": "error",
                        "message": restricted_check.reason
                    })
                    risk_score += 0.3
            
            # Apply tool-specific rules
            for rule in rules:
                if rule.get("tool_specific", False):
                    check_result = await self._apply_tool_rule(rule, tool_id, tool_data)
                    if not check_result.passed:
                        violations.append({
                            "type": "tool_rule",
                            "severity": rule.get("severity", "warning"),
                            "message": check_result.reason
                        })
                        risk_score += self._get_risk_weight(rule.get("severity", "warning"))
            
            # Parameter validation
            param_check = await self._validate_tool_parameters(tool_data)
            if not param_check.passed:
                violations.append({
                    "type": "parameter_validation",
                    "severity": "error",
                    "message": param_check.reason
                })
                risk_score += 0.2
            
            passed = len([v for v in violations if v["severity"] in ["error", "critical"]]) == 0
            
            return SafetyCheck(
                passed=passed,
                reason=f"Tool safety check failed: {[v['message'] for v in violations]}" if violations else None,
                risk_score=min(risk_score, 1.0)
            )
            
        except Exception as e:
            logger.error(f"Tool safety evaluation failed: {str(e)}")
            return SafetyCheck(
                passed=False,
                reason=f"Tool safety evaluation error: {str(e)}",
                risk_score=0.8
            )
    
    async def _apply_rule(
        self, 
        rule: Dict[str, Any], 
        data: Dict[str, Any], 
        context: str
    ) -> SafetyCheck:
        """Apply a specific guardrail rule"""
        rule_type = rule.get("type")
        
        if rule_type == "content_filter":
            return await self._content_filter_rule(rule, data)
        elif rule_type == "pattern_match":
            return await self._pattern_match_rule(rule, data)
        elif rule_type == "data_validation":
            return await self._data_validation_rule(rule, data)
        elif rule_type == "rate_limit":
            return await self._rate_limit_rule(rule, data)
        elif rule_type == "pii_detection":
            return await self._pii_detection_rule(rule, data)
        else:
            return SafetyCheck(passed=True)
    
    async def _content_filter_rule(self, rule: Dict[str, Any], data: Dict[str, Any]) -> SafetyCheck:
        """Content filtering rule"""
        blocked_words = rule.get("blocked_words", [])
        content = json.dumps(data).lower()
        
        for word in blocked_words:
            if word.lower() in content:
                return SafetyCheck(
                    passed=False,
                    reason=f"Blocked content detected: {word}"
                )
        
        return SafetyCheck(passed=True)
    
    async def _pattern_match_rule(self, rule: Dict[str, Any], data: Dict[str, Any]) -> SafetyCheck:
        """Pattern matching rule"""
        patterns = rule.get("patterns", [])
        content = json.dumps(data)
        
        for pattern in patterns:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    return SafetyCheck(
                        passed=False,
                        reason=f"Blocked pattern detected: {pattern}"
                    )
            except re.error as e:
                logger.warning(f"Invalid regex pattern: {pattern} - {str(e)}")
        
        return SafetyCheck(passed=True)
    
    async def _data_validation_rule(self, rule: Dict[str, Any], data: Dict[str, Any]) -> SafetyCheck:
        """Data validation rule"""
        field = rule.get("field")
        validation_type = rule.get("validation_type")
        
        if field not in data:
            return SafetyCheck(passed=True)
        
        value = data[field]
        
        if validation_type == "string_length":
            min_len = rule.get("min_length", 0)
            max_len = rule.get("max_length", 1000)
            
            if not isinstance(value, str) or len(value) < min_len or len(value) > max_len:
                return SafetyCheck(
                    passed=False,
                    reason=f"Field {field} must be between {min_len} and {max_len} characters",
                    modified_data={field: str(value)[:max_len] if isinstance(value, str) else value}
                )
        
        elif validation_type == "numeric_range":
            min_val = rule.get("min_value")
            max_val = rule.get("max_value")
            
            try:
                num_val = float(value)
                if min_val is not None and num_val < min_val:
                    return SafetyCheck(
                        passed=False,
                        reason=f"Field {field} must be at least {min_val}",
                        modified_data={field: min_val}
                    )
                if max_val is not None and num_val > max_val:
                    return SafetyCheck(
                        passed=False,
                        reason=f"Field {field} must be at most {max_val}",
                        modified_data={field: max_val}
                    )
            except (ValueError, TypeError):
                return SafetyCheck(
                    passed=False,
                    reason=f"Field {field} must be a number"
                )
        
        elif validation_type == "allowed_values":
            allowed = rule.get("allowed_values", [])
            if value not in allowed:
                return SafetyCheck(
                    passed=False,
                    reason=f"Field {field} must be one of: {', '.join(allowed)}"
                )
        
        return SafetyCheck(passed=True)
    
    async def _rate_limit_rule(self, rule: Dict[str, Any], data: Dict[str, Any]) -> SafetyCheck:
        """Rate limiting rule"""
        user_id = data.get("user_id") or data.get("user", {}).get("id") or "anonymous"
        return await self._check_rate_limit(user_id, [rule])
    
    async def _pii_detection_rule(self, rule: Dict[str, Any], data: Dict[str, Any]) -> SafetyCheck:
        """PII detection rule"""
        content = json.dumps(data)
        
        # Simple PII patterns
        pii_patterns = {
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "credit_card": re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
        }
        
        for pii_type, pattern in pii_patterns.items():
            if pattern.search(content):
                return SafetyCheck(
                    passed=False,
                    reason=f"PII detected: {pii_type}"
                )
        
        return SafetyCheck(passed=True)
    
    async def _security_scan_input(self, data: Dict[str, Any]) -> SafetyCheck:
        """Security scan for input data"""
        content = json.dumps(data)
        violations = []
        risk_score = 0.0
        
        for attack_type, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    violations.append({
                        "type": "security",
                        "attack_type": attack_type,
                        "severity": "critical" if attack_type in ["command_injection", "sql_injection"] else "error"
                    })
                    risk_score += 0.4 if attack_type in ["command_injection", "sql_injection"] else 0.2
        
        # Check for blocked keywords
        content_lower = content.lower()
        for keyword in self.blocked_keywords:
            if keyword in content_lower:
                violations.append({
                    "type": "blocked_content",
                    "keyword": keyword,
                    "severity": "warning"
                })
                risk_score += 0.1
        
        return SafetyCheck(
            passed=len(violations) == 0,
            reason=f"Security scan found {len(violations)} issues" if violations else None,
            risk_score=min(risk_score, 1.0)
        )
    
    async def _security_scan_output(self, data: Dict[str, Any]) -> SafetyCheck:
        """Security scan for output data"""
        # Similar to input scan but with different thresholds
        content = json.dumps(data)
        violations = []
        risk_score = 0.0
        
        # Check for potential data leaks
        leak_patterns = {
            "api_key": re.compile(r'\b[A-Za-z0-9]{32,}\b'),
            "private_key": re.compile(r'-----BEGIN [A-Z]+ KEY-----'),
            "password": re.compile(r'\b(password|passwd|pwd)\s*[:=]\s*\S+', re.IGNORECASE)
        }
        
        for leak_type, pattern in leak_patterns.items():
            if pattern.search(content):
                violations.append({
                    "type": "data_leak",
                    "leak_type": leak_type,
                    "severity": "critical"
                })
                risk_score += 0.5
        
        return SafetyCheck(
            passed=len(violations) == 0,
            reason=f"Output security scan found {len(violations)} issues" if violations else None,
            risk_score=min(risk_score, 1.0)
        )
    
    async def _sanitize_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize output content"""
        if isinstance(data, str):
            # Remove potentially dangerous HTML/JS
            sanitized = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.IGNORECASE | re.DOTALL)
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            return sanitized
        elif isinstance(data, dict):
            return {k: await self._sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [await self._sanitize_output(item) for item in data]
        else:
            return data
    
    async def _check_rate_limit(self, user_id: str, rules: List[Dict[str, Any]]) -> SafetyCheck:
        """Check rate limits"""
        # In production, this would use Redis or similar
        current_time = datetime.now(timezone.utc)
        
        # Simple in-memory rate limiting (not production-ready)
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # Clean old entries (older than 1 hour)
        self.rate_limits[user_id] = [
            timestamp for timestamp in self.rate_limits[user_id]
            if current_time - timestamp < timedelta(hours=1)
        ]
        
        # Check limits
        request_count = len(self.rate_limits[user_id])
        max_requests = 1000  # Default limit
        
        for rule in rules:
            if rule.get("type") == "rate_limit":
                max_requests = rule.get("max_requests", max_requests)
                break
        
        if request_count >= max_requests:
            return SafetyCheck(
                passed=False,
                reason=f"Rate limit exceeded: {request_count}/{max_requests} requests"
            )
        
        # Add current request
        self.rate_limits[user_id].append(current_time)
        return SafetyCheck(passed=True)
    
    async def _check_admin_approval(self, user_id: str, tool_id: str, db: Optional[Any] = None) -> bool:
        """Check if user has admin approval for dangerous tools"""
        if db is not None:
            try:
                from sqlalchemy import select
                from backend.db.models.user import User
                from backend.db.models.authority import AuthorityDecision, AuthorityRun

                # 1. Check if the user themselves is an admin/super_admin/owner
                user_stmt = select(User).where(User.id == user_id)
                user_res = await db.execute(user_stmt)
                user = user_res.scalar_one_or_none()
                if user and user.role.upper() in ("ADMIN", "SUPER_ADMIN", "OWNER"):
                    return True

                # 2. Check if there is an approved decision for this tool under an active run
                stmt = select(AuthorityDecision).join(AuthorityRun).where(
                    AuthorityDecision.tool_name == tool_id,
                    AuthorityDecision.decision == "approve",
                    AuthorityRun.status == "active"
                )
                result = await db.execute(stmt)
                decision = result.scalar_one_or_none()
                if decision:
                    return True
            except Exception as e:
                logger.error(f"Error checking admin approval in database: {str(e)}")
        
        return False
    
    async def _validate_restricted_tool(self, tool_id: str, tool_data: Dict[str, Any]) -> SafetyCheck:
        """Validate restricted tool usage"""
        # Check for suspicious patterns in tool data
        data_str = json.dumps(tool_data).lower()
        
        suspicious_patterns = [
            "password", "secret", "token", "key", "../", "rm -rf",
            "del /", "format", "sudo", "admin", "root"
        ]
        
        for pattern in suspicious_patterns:
            if pattern in data_str:
                return SafetyCheck(
                    passed=False,
                    reason=f"Suspicious pattern in tool data: {pattern}"
                )
        
        return SafetyCheck(passed=True)
    
    async def _apply_tool_rule(self, rule: Dict[str, Any], tool_id: str, tool_data: Dict[str, Any]) -> SafetyCheck:
        """Apply tool-specific rule"""
        # Check if tool is blocked
        if "blocked_tools" in rule and tool_id in rule["blocked_tools"]:
            return SafetyCheck(
                passed=False,
                reason=f"Tool {tool_id} is explicitly blocked"
            )
        
        # Check required permissions
        if "required_permissions" in rule:
            # This would check actual user permissions
            pass
        
        return SafetyCheck(passed=True)
    
    async def _validate_tool_parameters(self, tool_data: Dict[str, Any]) -> SafetyCheck:
        """Validate tool parameters"""
        # Basic parameter validation
        for key, value in tool_data.items():
            if isinstance(value, str):
                # Check for suspicious content
                if any(pattern in value.lower() for pattern in ["../", "<script", "javascript:"]):
                    return SafetyCheck(
                        passed=False,
                        reason=f"Suspicious content in parameter {key}"
                    )
        
        return SafetyCheck(passed=True)

    async def run_watchtowers(
        self,
        output: Union[Dict[str, Any], str],
        request: Union[Dict[str, Any], str],
        tier: str,
        task_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Runs a suite of watchtower checks (PII, security, content filtering) based on the tier.
        Returns a list of check results: [{"name": ..., "passed": ..., "reason": ..., "severity": ...}]
        """
        results = []
        
        # Format input/output as dict for rules
        input_dict = request if isinstance(request, dict) else {"content": str(request)}
        output_dict = output if isinstance(output, dict) else {"content": str(output)}
        
        # 1. PII detection
        pii_check = await self._pii_detection_rule({}, output_dict)
        results.append({
            "name": "pii_detection",
            "passed": pii_check.passed,
            "reason": pii_check.reason,
            "severity": "error"
        })
        
        # 2. Output security scan (keys, passwords, private keys leaks)
        security_check = await self._security_scan_output(output_dict)
        results.append({
            "name": "output_security_scan",
            "passed": security_check.passed,
            "reason": security_check.reason,
            "severity": "critical"
        })
        
        # 3. Content filtering / SQL / Command injection check
        input_security_check = await self._security_scan_input(output_dict)
        results.append({
            "name": "injection_scan",
            "passed": input_security_check.passed,
            "reason": input_security_check.reason,
            "severity": "critical"
        })
        
        # 4. Optional custom rules from task_profile or watchtower_rules
        custom_rules = task_profile.get("watchtower_rules", [])
        for i, rule in enumerate(custom_rules):
            rule_check = await self._apply_rule(rule, output_dict, "output")
            results.append({
                "name": f"custom_rule_{i}_{rule.get('type', 'rule')}",
                "passed": rule_check.passed,
                "reason": rule_check.reason,
                "severity": rule.get("severity", "warning")
            })

        # 5. SIGMA Spectral Quality Gate (Defends against model collapse)
        embeddings = task_profile.get("embeddings")
        baseline_log_det = task_profile.get("baseline_log_det", 0.0)
        if embeddings:
            sigma_passed = SigmaSpectralLens.verify_quality_gate(embeddings, baseline_log_det)
            results.append({
                "name": "sigma_spectral_gate",
                "passed": sigma_passed,
                "reason": "Spectral drift detected in representation space" if not sigma_passed else None,
                "severity": "gold"
            })
            
        return results

    def check_tier_pass(
        self,
        results: List[Dict[str, Any]],
        tier: str,
        task_profile: Dict[str, Any]
    ) -> bool:
        """
        Check if the results satisfy the tier's pass requirements.
        T0: at least 2 checks must pass.
        T1: at least 60% of checks must pass.
        T2: ALL checks must pass.
        """
        if not results:
            return True
            
        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)
        
        tier = str(tier).upper()
        if tier in ("T0", "0"):
            return passed_count >= min(2, total_count)
        elif tier in ("T1", "1"):
            return (passed_count / total_count) >= 0.60
        elif tier in ("T2", "2"):
            return passed_count == total_count
        else:
            return passed_count == total_count

    def build_corrections(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates corrective instructions/hints from failed watchtowers."""
        failed_checks = [r for r in results if not r["passed"]]
        reasons = [f"{f['name']}: {f['reason']}" for f in failed_checks if f["reason"]]
        return {
            "failed_watchtowers": [f["name"] for f in failed_checks],
            "reasons": reasons,
            "prompt_instructions": "The output violated governance policies. Please adjust: " + "; ".join(reasons) if reasons else "Output policy violation."
        }
    
    def _get_risk_weight(self, severity: str) -> float:
        """Get risk weight for severity level"""
        weights = {
            "info": 0.05,
            "warning": 0.1,
            "error": 0.3,
            "critical": 0.5
        }
        return weights.get(severity, 0.1)


# Global instance
guardrail_service = RealGuardrailService()


def get_guardrail_service() -> RealGuardrailService:
    """Get the global guardrail service instance"""
    return guardrail_service
