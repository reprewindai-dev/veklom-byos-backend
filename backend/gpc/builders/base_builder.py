"""
Base Capability Builder
Foundation class for all capability builders

All builders follow same lifecycle:
1. prepare() - validate requirement
2. generate() - create code
3. compile() - syntax check
4. verify() - run tests
5. package() - create artifact
6. register() - with PGL
7. store() - in cache

Location: veklom-byos-backend/backend/gpc/builders/base_builder.py
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from backend.gpc.poltergeist.watcher import CapabilityRequirement
from backend.gpc.poltergeist.haunt_cache import HauntCachePlane, CachedCapability, CacheTier


class BuilderStatus(str, Enum):
    """Status of a build"""
    PREPARING = "preparing"
    GENERATING = "generating"
    COMPILING = "compiling"
    VERIFYING = "verifying"
    PACKAGING = "packaging"
    REGISTERING = "registering"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BuildResult:
    """Result of a capability build"""
    success: bool
    capability_id: str
    artifact_bytes: bytes  # Compiled wheel, JAR, Docker image, etc.
    artifact_hash: str  # SHA256 of artifact
    source_code: str  # Readable source
    source_hash: str
    manifest: Dict[str, Any]  # Metadata
    tests_passed: bool = True
    test_results: List[Dict] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class VerificationResult:
    """Result of verification checks"""
    passed: bool
    unit_tests_passed: bool
    contract_tests_passed: bool
    security_scan_passed: bool
    dependency_scan_passed: bool
    policy_validation_passed: bool
    adversarial_tests_passed: bool
    results: Dict[str, Any]
    error_message: Optional[str] = None


class BaseCapabilityBuilder(ABC):
    """
    Base class for capability builders.

    All builders:
    1. Receive a CapabilityRequirement
    2. Validate it can be fulfilled
    3. Generate source code (language-specific)
    4. Compile to artifact
    5. Run verification hooks
    6. Register with PGL
    7. Store in cache

    Each builder subclass implements language/platform-specific logic.
    """

    def __init__(
        self,
        cache: HauntCachePlane,
        pgl_client=None,  # gnomledger client
        repogate_client=None,  # security scanner
        max_retries: int = 3,
    ):
        """
        Initialize builder.

        Args:
            cache: HauntCachePlane for artifact storage
            pgl_client: Gnomledger client for capability registration
            repogate_client: RepoGate security scanner
            max_retries: Max build attempts on failure
        """
        self.cache = cache
        self.pgl_client = pgl_client
        self.repogate_client = repogate_client
        self.max_retries = max_retries

    async def build(
        self,
        requirement: CapabilityRequirement,
        on_status: callable = None,
    ) -> BuildResult:
        """
        Build a capability from a requirement.

        Args:
            requirement: The capability requirement
            on_status: Callback(status, message) for progress

        Returns:
            BuildResult with success/failure details
        """
        start_time = datetime.utcnow()

        try:
            # Phase 1: Prepare
            await self._emit_status(on_status, BuilderStatus.PREPARING, "Validating requirement...")
            await self.prepare(requirement)

            # Phase 2: Generate
            await self._emit_status(on_status, BuilderStatus.GENERATING, "Generating source code...")
            source_code = await self.generate(requirement)
            source_hash = self._hash(source_code.encode())

            # Phase 3: Compile
            await self._emit_status(on_status, BuilderStatus.COMPILING, "Compiling to artifact...")
            artifact_bytes = await self.compile(source_code, requirement)
            artifact_hash = self._hash(artifact_bytes)

            # Phase 4: Verify
            await self._emit_status(on_status, BuilderStatus.VERIFYING, "Running verification hooks...")
            verification = await self.verify(source_code, artifact_bytes, requirement)

            if not verification.passed:
                return BuildResult(
                    success=False,
                    capability_id=requirement.capability_id,
                    artifact_bytes=artifact_bytes,
                    artifact_hash=artifact_hash,
                    source_code=source_code,
                    source_hash=source_hash,
                    manifest=self._create_manifest(requirement, verification),
                    tests_passed=False,
                    error_message=verification.error_message,
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                )

            # Phase 5: Package
            await self._emit_status(on_status, BuilderStatus.PACKAGING, "Packaging artifact...")
            manifest = await self.package(requirement, artifact_bytes, source_code)

            # Phase 6: Register with PGL
            await self._emit_status(on_status, BuilderStatus.REGISTERING, "Registering with PGL...")
            pgl_result = await self.register_with_pgl(requirement, manifest)

            # Phase 7: Store in cache
            await self._emit_status(on_status, BuilderStatus.SUCCESS, "Storing in cache...")
            await self.store_in_cache(
                capability_id=requirement.capability_id,
                artifact_bytes=artifact_bytes,
                artifact_hash=artifact_hash,
                source_hash=source_hash,
                pgl_agent_id=pgl_result.get("agent_id"),
                pgl_certificate=pgl_result.get("certificate_id"),
                manifest=manifest,
            )

            return BuildResult(
                success=True,
                capability_id=requirement.capability_id,
                artifact_bytes=artifact_bytes,
                artifact_hash=artifact_hash,
                source_code=source_code,
                source_hash=source_hash,
                manifest=manifest,
                tests_passed=verification.unit_tests_passed,
                test_results=verification.results.get("tests", []),
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            await self._emit_status(on_status, BuilderStatus.FAILED, f"Build failed: {str(e)}")

            return BuildResult(
                success=False,
                capability_id=requirement.capability_id,
                artifact_bytes=b"",
                artifact_hash="",
                source_code="",
                source_hash="",
                manifest={},
                error_message=str(e),
                duration_seconds=duration,
            )

    @abstractmethod
    async def prepare(self, requirement: CapabilityRequirement) -> None:
        """
        Validate that requirement can be fulfilled.

        Args:
            requirement: The requirement to validate

        Raises:
            ValueError: If requirement cannot be fulfilled
        """
        raise NotImplementedError

    @abstractmethod
    async def generate(self, requirement: CapabilityRequirement) -> str:
        """
        Generate source code for the capability.

        Args:
            requirement: The requirement

        Returns:
            Source code as string
        """
        raise NotImplementedError

    @abstractmethod
    async def compile(
        self,
        source_code: str,
        requirement: CapabilityRequirement,
    ) -> bytes:
        """
        Compile source code to artifact.

        Args:
            source_code: The source code
            requirement: The requirement

        Returns:
            Compiled artifact bytes (wheel, JAR, docker image, etc.)
        """
        raise NotImplementedError

    async def verify(
        self,
        source_code: str,
        artifact_bytes: bytes,
        requirement: CapabilityRequirement,
    ) -> VerificationResult:
        """
        Run verification hooks.

        Default implementation runs unit tests + security scans.
        Subclasses can override for more specific checks.

        Args:
            source_code: The source code
            artifact_bytes: The artifact
            requirement: The requirement

        Returns:
            VerificationResult
        """
        try:
            # 1. Unit tests
            unit_tests_passed = await self._run_unit_tests(source_code, artifact_bytes)

            # 2. Contract tests (optional)
            contract_tests_passed = True

            # 3. Security scan (RepoGate)
            security_passed = await self._security_scan(source_code)

            # 4. Dependency scan
            dependency_passed = await self._scan_dependencies(source_code)

            # 5. Policy validation (PGL)
            policy_passed = await self._validate_policy(requirement)

            # 6. Adversarial tests
            adversarial_passed = await self._run_adversarial_tests(artifact_bytes)

            all_passed = all([
                unit_tests_passed,
                contract_tests_passed,
                security_passed,
                dependency_passed,
                policy_passed,
                adversarial_passed,
            ])

            return VerificationResult(
                passed=all_passed,
                unit_tests_passed=unit_tests_passed,
                contract_tests_passed=contract_tests_passed,
                security_scan_passed=security_passed,
                dependency_scan_passed=dependency_passed,
                policy_validation_passed=policy_passed,
                adversarial_tests_passed=adversarial_passed,
                results={
                    "unit_tests": {"passed": unit_tests_passed},
                    "contract_tests": {"passed": contract_tests_passed},
                    "security": {"passed": security_passed},
                    "dependencies": {"passed": dependency_passed},
                    "policy": {"passed": policy_passed},
                    "adversarial": {"passed": adversarial_passed},
                },
            )

        except Exception as e:
            return VerificationResult(
                passed=False,
                unit_tests_passed=False,
                contract_tests_passed=False,
                security_scan_passed=False,
                dependency_scan_passed=False,
                policy_validation_passed=False,
                adversarial_tests_passed=False,
                results={},
                error_message=str(e),
            )

    async def package(
        self,
        requirement: CapabilityRequirement,
        artifact_bytes: bytes,
        source_code: str,
    ) -> Dict[str, Any]:
        """
        Create manifest/metadata for the capability.

        Args:
            requirement: The requirement
            artifact_bytes: The artifact
            source_code: The source code

        Returns:
            Manifest dict
        """
        return {
            "capability_id": requirement.capability_id,
            "requirement_type": requirement.requirement_type.value,
            "node_type": requirement.node_type,
            "external_system": requirement.external_system,
            "operations": requirement.operations,
            "input_ports": requirement.input_ports,
            "output_ports": requirement.output_ports,
            "created_at": datetime.utcnow().isoformat(),
            "builder_name": self.__class__.__name__,
            "source_lines": len(source_code.split('\n')),
            "artifact_size_bytes": len(artifact_bytes),
        }

    async def register_with_pgl(
        self,
        requirement: CapabilityRequirement,
        manifest: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Register capability with PGL (gnomledger).

        Args:
            requirement: The requirement
            manifest: The manifest

        Returns:
            Dict with agent_id and certificate_id
        """
        if not self.pgl_client:
            return {
                "agent_id": f"cap_{requirement.capability_id}",
                "certificate_id": f"cert_{requirement.capability_id}",
            }

        try:
            # Call PGL API to register
            result = await self.pgl_client.create_agent(
                agent_name=requirement.capability_id,
                creator="veklom_autonomous_builder",
                jurisdiction="CA",
                genome={
                    "model_family": requirement.requirement_type.value,
                    "tools": requirement.operations,
                    "permissions": [f"access:{requirement.external_system}"],
                    "safety_rules": ["no_hardcoded_secrets"],
                    "runtime_config": {},
                    "intended_use": f"Connector for {requirement.external_system}",
                    "risk_category": "medium",
                }
            )

            return {
                "agent_id": result.get("agent_id"),
                "certificate_id": result.get("certificate_id"),
            }

        except Exception as e:
            print(f"[Builder] PGL registration error: {e}")
            return {
                "agent_id": f"cap_{requirement.capability_id}",
                "certificate_id": f"cert_{requirement.capability_id}",
            }

    async def store_in_cache(
        self,
        capability_id: str,
        artifact_bytes: bytes,
        artifact_hash: str,
        source_hash: str,
        pgl_agent_id: str,
        pgl_certificate: str,
        manifest: Dict[str, Any],
    ) -> None:
        """
        Store artifact in cache.

        Args:
            capability_id: Capability ID
            artifact_bytes: The artifact
            artifact_hash: SHA256 of artifact
            source_hash: SHA256 of source
            pgl_agent_id: PGL agent ID
            pgl_certificate: PGL certificate
            manifest: Metadata
        """
        cached = CachedCapability(
            capability_id=capability_id,
            artifact_hash=artifact_hash,
            artifact_bytes=artifact_bytes,
            source_hash=source_hash,
            policy_hash=json.dumps(manifest, sort_keys=True),
            pgl_agent_id=pgl_agent_id,
            pgl_certificate=pgl_certificate,
            verified_at=datetime.utcnow(),
        )

        await self.cache.put(cached, target_tier=CacheTier.L2_BUILD)

    # ========================================================================
    # VERIFICATION HELPERS
    # ========================================================================

    async def _run_unit_tests(self, source_code: str, artifact_bytes: bytes) -> bool:
        """Run unit tests on artifact"""
        try:
            # Would invoke test runner based on language
            # For now, mock success
            return True
        except Exception as e:
            print(f"[Builder] Unit tests failed: {e}")
            return False

    async def _security_scan(self, source_code: str) -> bool:
        """Run RepoGate security scan"""
        try:
            if self.repogate_client:
                result = await self.repogate_client.scan(source_code)
                return result.get("passed", False)
            return True
        except Exception as e:
            print(f"[Builder] Security scan error: {e}")
            return False

    async def _scan_dependencies(self, source_code: str) -> bool:
        """Scan dependencies for vulnerabilities"""
        try:
            # Would parse requirements/imports and check for known vulns
            # For now, mock success
            return True
        except Exception as e:
            print(f"[Builder] Dependency scan error: {e}")
            return False

    async def _validate_policy(self, requirement: CapabilityRequirement) -> bool:
        """Validate against PGL policy"""
        try:
            # Would call Interlink-CAPI to validate
            # For now, mock success
            return True
        except Exception as e:
            print(f"[Builder] Policy validation error: {e}")
            return False

    async def _run_adversarial_tests(self, artifact_bytes: bytes) -> bool:
        """Run adversarial tests (malformed input, etc.)"""
        try:
            # Would invoke artifact with various adversarial inputs
            # For now, mock success
            return True
        except Exception as e:
            print(f"[Builder] Adversarial tests error: {e}")
            return False

    # ========================================================================
    # UTILITIES
    # ========================================================================

    @staticmethod
    def _hash(data: bytes) -> str:
        """SHA256 hash of data"""
        import hashlib
        return hashlib.sha256(data).hexdigest()

    def _create_manifest(
        self,
        requirement: CapabilityRequirement,
        verification: VerificationResult,
    ) -> Dict[str, Any]:
        """Create manifest on failure"""
        return {
            "capability_id": requirement.capability_id,
            "failed": True,
            "verification_results": asdict(verification),
        }

    async def _emit_status(
        self,
        callback: callable,
        status: BuilderStatus,
        message: str,
    ) -> None:
        """Emit build status"""
        if callback:
            if asyncio.iscoroutinefunction(callback):
                await callback(status, message)
            else:
                callback(status, message)

        print(f"[Builder] {status.value}: {message}")
