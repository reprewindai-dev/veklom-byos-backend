"""Fail-closed GPC capability freshness gate.

Adapted from the GPCUPDATED package without mock PGL/CAPI approval. The gate
validates evidence-pack shaped objects before a generated capability can be
bound into GPC. Missing external governance clients are explicit failures, not
simulated success.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol


class CAPIApprovalClient(Protocol):
    async def request_binding_approval(self, **kwargs: Any) -> Mapping[str, Any]: ...


class PGLCertificateClient(Protocol):
    async def verify_certificate(self, certificate_id: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class FreshnessCheckResult:
    check_name: str
    passed: bool
    message: str
    details: Mapping[str, Any]


class FreshnessGate:
    """Pre-bind validation for generated GPC capability artifacts."""

    def __init__(self, *, capi_client: CAPIApprovalClient | None = None, pgl_client: PGLCertificateClient | None = None):
        self.capi_client = capi_client
        self.pgl_client = pgl_client

    async def validate_before_bind(self, capability_id: str, evidence_pack: Any) -> Mapping[str, Any]:
        checks = [
            self._check_build_hashes(evidence_pack),
            self._check_policy_evidence(evidence_pack),
            self._check_verifications(evidence_pack),
            await self._check_certificate(evidence_pack),
            await self._check_capi_approval(capability_id, evidence_pack),
        ]
        passed = all(check.passed for check in checks)
        return {
            "passed": passed,
            "capability_id": capability_id,
            "timestamp": datetime.utcnow().isoformat(),
            "checks_passed": sum(1 for check in checks if check.passed),
            "checks_failed": sum(1 for check in checks if not check.passed),
            "total_checks": len(checks),
            "details": [check.__dict__ for check in checks],
            "recommendation": "safe_to_bind" if passed else "queue_for_rebuild",
        }

    def _check_build_hashes(self, evidence_pack: Any) -> FreshnessCheckResult:
        build = getattr(evidence_pack, "build_evidence", None)
        if build is None:
            return FreshnessCheckResult("build_hashes", False, "No build evidence found", {})
        missing = [
            name for name in ("source_code_hash", "artifact_hash")
            if not str(getattr(build, name, "") or "").strip()
        ]
        if missing:
            return FreshnessCheckResult("build_hashes", False, f"Missing build hashes: {', '.join(missing)}", {"missing": missing})
        return FreshnessCheckResult(
            "build_hashes",
            True,
            "Build hashes present",
            {
                "source_code_hash": getattr(build, "source_code_hash"),
                "artifact_hash": getattr(build, "artifact_hash"),
            },
        )

    def _check_policy_evidence(self, evidence_pack: Any) -> FreshnessCheckResult:
        policy = getattr(evidence_pack, "policy_evidence", None)
        if policy is None:
            return FreshnessCheckResult("policy_evidence", False, "No policy evidence found", {})
        approved = bool(getattr(policy, "approved", False))
        decisions = list(getattr(policy, "decisions", []) or [])
        violations = [decision for decision in decisions if not bool(_mapping_get(decision, "approved", False))]
        if not approved or violations:
            return FreshnessCheckResult(
                "policy_evidence",
                False,
                "Policy evidence is not approved",
                {"approved": approved, "violations": violations},
            )
        return FreshnessCheckResult("policy_evidence", True, "Policy evidence approved", {"decision_count": len(decisions)})

    def _check_verifications(self, evidence_pack: Any) -> FreshnessCheckResult:
        verifications = list(getattr(evidence_pack, "verification_evidence", []) or [])
        if not verifications:
            return FreshnessCheckResult("verification_evidence", False, "No verification evidence found", {})
        failed = [item for item in verifications if str(getattr(item, "status", "")).lower() != "passed"]
        if failed:
            return FreshnessCheckResult(
                "verification_evidence",
                False,
                f"{len(failed)} verification checks failed",
                {"failed_checks": [getattr(item, "hook_name", "unknown") for item in failed]},
            )
        return FreshnessCheckResult("verification_evidence", True, f"All {len(verifications)} verification checks passed", {"total_checks": len(verifications)})

    async def _check_certificate(self, evidence_pack: Any) -> FreshnessCheckResult:
        pgl = getattr(evidence_pack, "pgl_evidence", None)
        certificate_id = str(getattr(pgl, "certificate_id", "") or "")
        if not certificate_id:
            return FreshnessCheckResult("pgl_certificate", False, "No PGL certificate evidence found", {})
        if self.pgl_client is None:
            return FreshnessCheckResult("pgl_certificate", False, "PGL verifier unavailable", {"certificate_id": certificate_id})
        result = await self.pgl_client.verify_certificate(certificate_id)
        valid = bool(result.get("valid", False)) and not bool(result.get("expired", False))
        return FreshnessCheckResult("pgl_certificate", valid, "PGL certificate valid" if valid else "PGL certificate invalid or expired", dict(result))

    async def _check_capi_approval(self, capability_id: str, evidence_pack: Any) -> FreshnessCheckResult:
        if self.capi_client is None:
            return FreshnessCheckResult("capi_approval", False, "CAPI approval service unavailable", {"capability_id": capability_id})
        build = getattr(evidence_pack, "build_evidence", None)
        result = await self.capi_client.request_binding_approval(
            capability_id=capability_id,
            requirement_type=getattr(build, "requirement_type", None),
            operations=_manifest_operations(build),
            external_system=getattr(build, "external_system", None),
        )
        approved = bool(result.get("approved", False))
        return FreshnessCheckResult("capi_approval", approved, "CAPI approval granted" if approved else "CAPI approval denied", dict(result))


def _mapping_get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _manifest_operations(build: Any) -> list[Any]:
    manifest = getattr(build, "manifest", None)
    if isinstance(manifest, Mapping):
        return list(manifest.get("operations", []) or [])
    return []
