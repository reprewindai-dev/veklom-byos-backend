"""Policy Registry Service for version management, authorization, and bundle compilation."""

import hashlib
import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models.policy_bundle import PolicyVersion, EnforcementBundle


class PolicyRegistryService:
    """Manages versioned policy authorizations and compiles cryptographic enforcement bundles."""

    @staticmethod
    async def get_current_version(db: AsyncSession) -> str:
        """Retrieves the active policy version, defaulting to '1.0.0'."""
        query = select(PolicyVersion).where(PolicyVersion.is_active == True)
        result = await db.execute(query)
        active = result.scalar_one_or_none()
        return active.version if active else "1.0.0"

    @staticmethod
    async def authorize(
        db: AsyncSession,
        user_id: str,
        org_id: str,
        role: str,
        task_type: str,
        tier: str
    ) -> Dict[str, Any]:
        """
        Validates if the user's role is authorized to execute the task type
        at the specified risk tier.
        """
        query = select(PolicyVersion).where(PolicyVersion.is_active == True)
        result = await db.execute(query)
        active_version = result.scalar_one_or_none()

        # If no policy version is defined, use default authorization
        if not active_version:
            # Default Viewer role limits: restrict T2 execution
            if tier == "T2" and role.lower() == "viewer":
                return {"authorized": False, "reason": "Viewer role not permitted for T2 critical execution"}
            return {"authorized": True, "reason": "Authorized under default policy configuration"}

        policies = active_version.policies or {}
        role_rules = policies.get("roles", {}).get(role.lower(), {})
        max_allowed_tier = role_rules.get("max_tier", "T2")

        tier_hierarchy = {"T0": 0, "T1": 1, "T2": 2}
        requested_val = tier_hierarchy.get(tier.upper(), 1)
        allowed_val = tier_hierarchy.get(max_allowed_tier.upper(), 2)

        if requested_val > allowed_val:
            return {
                "authorized": False,
                "reason": f"Role '{role}' is restricted to max tier '{max_allowed_tier}' (requested '{tier}')"
            }

        restricted_tasks = role_rules.get("restricted_tasks", [])
        if task_type in restricted_tasks:
            return {
                "authorized": False,
                "reason": f"Role '{role}' is restricted from executing task type '{task_type}'"
            }

        return {
            "authorized": True,
            "reason": "Authorized under active policy bundle"
        }

    @staticmethod
    async def compile_bundle(
        db: AsyncSession,
        policy_version: str,
        constitution_version: str
    ) -> EnforcementBundle:
        """Compiles and registers an immutable cryptographic policy bundle."""
        query = select(PolicyVersion).where(PolicyVersion.version == policy_version)
        result = await db.execute(query)
        pol = result.scalar_one_or_none()

        pol_data = pol.policies if pol else {}

        raw_bundle = {
            "policy_version": policy_version,
            "constitution_version": constitution_version,
            "policies": pol_data
        }
        canonical_str = json.dumps(raw_bundle, sort_keys=True, separators=(',', ':'))
        bundle_hash = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

        # Check existing compilation
        bundle_query = select(EnforcementBundle).where(EnforcementBundle.bundle_hash == bundle_hash)
        bundle_result = await db.execute(bundle_query)
        existing = bundle_result.scalar_one_or_none()

        if existing:
            return existing

        new_bundle = EnforcementBundle(
            policy_version=policy_version,
            constitution_version=constitution_version,
            bundle_hash=bundle_hash,
            regression_passed=True
        )

        db.add(new_bundle)
        await db.commit()
        await db.refresh(new_bundle)
        return new_bundle
