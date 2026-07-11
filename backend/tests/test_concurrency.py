import asyncio

import httpx
import pytest

# Ensure models are imported so they register with Base.metadata.
from backend.apps.api.main import app
from backend.core.database.database import Base, engine
from backend.core.security.jwt_keys import key_manager
from backend.db.models.billing import WalletTransaction
from backend.db.models.pgl import PGLCertificate, PGLIdentity, PGLLedgerEvent
from backend.db.models.user import User
from backend.db.models.workspace import Workspace


# Run database initialization of specific tables for the CI PostgreSQL service.
async def init_db():
    tables_to_create = [
        User.__table__,
        Workspace.__table__,
        PGLIdentity.__table__,
        PGLCertificate.__table__,
        PGLLedgerEvent.__table__,
        WalletTransaction.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn,
                tables=tables_to_create,
            )
        )


@pytest.fixture(autouse=True)
async def setup_database():
    await init_db()


@pytest.mark.anyio
async def test_health_head_method():
    """Verify that HEAD requests to health check endpoints return 200 OK instead of 405."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        # Test GET /health
        res_get = await client.get("/health")
        assert res_get.status_code == 200

        # Test HEAD /health
        res_head = await client.head("/health")
        assert res_head.status_code == 200

        # Test HEAD /api/v1/health
        res_v1_head = await client.head("/api/v1/health")
        assert res_v1_head.status_code == 200


@pytest.mark.anyio
async def test_onboarding_pipeline_concurrency_and_rotation():
    """Verify end-to-end integration under concurrent database hits and active JWKS key rotation."""

    # 1. Warm up the keys
    initial_kid = key_manager.active_key_id
    assert initial_kid != ""

    payload = {
        "name": "Concurrent Enterprise Corp",
        "country": "CA",
        "age": 35,
        "identity_score": 0.97,
        "tier": "T2",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        # Define a single request task
        async def run_single_onboarding(idx: int):
            # We can slightly vary names to verify distinct writes
            custom_payload = payload.copy()
            custom_payload["name"] = f"Concurrent Corp {idx}"

            # Add some brief, realistic async delay to interleave execution
            await asyncio.sleep(0.01 * (idx % 5))

            response = await client.post("/api/v1/onboarding/run", json=custom_payload)
            assert (
                response.status_code == 200
            ), f"Failed at request {idx}: {response.text}"
            res_data = response.json()
            assert res_data["status"] == "APPROVED"
            assert res_data["epca_result"] == "SATISFIABLE (SAT)"
            return res_data

        # Define a key rotation task to run mid-flight
        async def rotate_keys_mid_flight():
            await asyncio.sleep(0.05)  # Wait for requests to be in flight
            new_kid = key_manager.rotate_key()
            # Verify we rotated correctly
            assert new_kid != initial_kid
            assert key_manager.active_key_id == new_kid

            # Fetch public JWKS to verify both old and new keys are served (rotation grace period)
            jwks_res = await client.get("/.well-known/jwks.json")
            assert jwks_res.status_code == 200
            jwks = jwks_res.json()
            kids = [k["kid"] for k in jwks["keys"]]
            assert initial_kid in kids
            assert new_kid in kids
            return new_kid

        # Spawn 25 concurrent onboarding requests + 1 mid-flight key rotation task
        tasks = [run_single_onboarding(i) for i in range(25)]
        rotation_task = asyncio.create_task(rotate_keys_mid_flight())

        # Execute concurrent batch
        results = await asyncio.gather(*tasks, rotation_task)

        onboarding_results = results[:-1]
        new_active_kid = results[-1]

        # Check that we have 25 successful onboarding certificates and events written to the DB
        assert len(onboarding_results) == 25
        for res_data in onboarding_results:
            # Verified signed key id should be either the initial one or the new one
            # History step 5 is the "SPIFFE_DB_WRITE" step
            assert res_data["history"][5]["signing_key_id"] in [
                initial_kid,
                new_active_kid,
            ]
            assert "certificate_id" in res_data["history"][5]
