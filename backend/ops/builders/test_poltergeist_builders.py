import asyncio
import logging
from backend.ops.builders.coordinator import AutonomousBuilderCoordinator

logging.basicConfig(level=logging.INFO)

async def run_tests():
    fingerprint = "test-cap-12345"
    revision = 1
    
    # 1. Test OpenAPI Builder
    print("\n--- Testing OpenAPI Builder ---")
    openapi_manifest = {
        "type": "openapi_connector",
        "target_api": "GitHub",
        "risk_category": "low"
    }
    success, verification, artifact = await AutonomousBuilderCoordinator.build_capability(
        fingerprint, revision, openapi_manifest
    )
    print(f"Success: {success}")
    print(f"Verification: {verification}")
    print(f"Artifact Size: {len(artifact)} bytes")
    
    # 2. Test Python Transform Builder
    print("\n--- Testing Python Transform Builder ---")
    transform_manifest = {
        "type": "python_transform",
        "engine": "duckdb"
    }
    success, verification, artifact = await AutonomousBuilderCoordinator.build_capability(
        fingerprint, revision, transform_manifest
    )
    print(f"Success: {success}")
    print(f"Verification: {verification}")
    print(f"Artifact Size: {len(artifact)} bytes")
    
    # 3. Test Database Adapter Builder
    print("\n--- Testing Database Adapter Builder ---")
    db_manifest = {
        "type": "database_adapter",
        "db_type": "postgresql"
    }
    success, verification, artifact = await AutonomousBuilderCoordinator.build_capability(
        fingerprint, revision, db_manifest
    )
    print(f"Success: {success}")
    print(f"Verification: {verification}")
    print(f"Artifact Size: {len(artifact)} bytes")
    
    # 4. Test Verification Failure (Hardcoded Secret)
    print("\n--- Testing Verification Failure ---")
    fail_manifest = {
        "type": "openapi_connector",
        "target_api": "GitHub",
        "risk_category": "critical" # triggers failure
    }
    success, verification, artifact = await AutonomousBuilderCoordinator.build_capability(
        fingerprint, revision, fail_manifest
    )
    print(f"Success: {success}")
    print(f"Verification: {verification}")

if __name__ == "__main__":
    asyncio.run(run_tests())
