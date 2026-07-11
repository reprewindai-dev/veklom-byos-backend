import httpx
import pytest

from backend.apps.api.main import app
from backend.apps.api.routers import onboarding_demo
from backend.core.database.database import Base, engine
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


@pytest.fixture
async def onboarding_client():
    await engine.dispose()
    await init_db()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client

    await engine.dispose()


def test_calculate_semantic_drift():
    """Verify semantic drift increases over successive workflow cycles."""
    # Step 0: Initial step, drift should be exactly 0
    drift_0 = onboarding_demo.calculate_semantic_drift(0)
    assert drift_0 == 0.0

    # Step 1: Small increment in drift angle
    drift_1 = onboarding_demo.calculate_semantic_drift(1)
    assert drift_1 > 0.0

    # Step 5: High drift
    drift_5 = onboarding_demo.calculate_semantic_drift(5)
    assert drift_5 > drift_1


def test_epca_z3_satisfiable():
    """Verify that compliant user attributes satisfy the Z3 safety axioms (SAT)."""
    is_sat, message = onboarding_demo.evaluate_epca_z3(
        country="CA", age=25, identity_score=0.95, authorized=True
    )
    assert is_sat is True
    assert "SATISFIABLE" in message


def test_epca_z3_unsat_sanctioned():
    """Verify that sanctioned countries trigger an immediate UNSAT compliance veto."""
    is_sat, message = onboarding_demo.evaluate_epca_z3(
        country="RU", age=25, identity_score=0.95, authorized=True
    )
    assert is_sat is False
    assert "UNSATISFIABLE" in message


def test_epca_z3_unsat_underage():
    """Verify representative representative being underage triggers an UNSAT compliance veto."""
    is_sat, message = onboarding_demo.evaluate_epca_z3(
        country="CA", age=17, identity_score=0.95, authorized=True
    )
    assert is_sat is False
    assert "UNSATISFIABLE" in message


def test_epca_z3_unsat_low_biometrics():
    """Verify low biometric score triggers an UNSAT compliance veto."""
    is_sat, message = onboarding_demo.evaluate_epca_z3(
        country="CA", age=25, identity_score=0.79, authorized=True
    )
    assert is_sat is False
    assert "UNSATISFIABLE" in message


@pytest.mark.anyio
async def test_api_onboarding_run_satisfiable(onboarding_client):
    """Test full onboarding pipeline API endpoint for SAT execution."""
    payload = {
        "name": "Acme Corp",
        "country": "CA",
        "age": 30,
        "identity_score": 0.98,
        "tier": "T2",
    }
    response = await onboarding_client.post("/api/v1/onboarding/run", json=payload)

    assert response.status_code == 200, f"Unexpected response: {response.text}"
    res_data = response.json()
    assert res_data["name"] == "Acme Corp"
    assert res_data["status"] == "APPROVED"
    assert res_data["epca_result"] == "SATISFIABLE (SAT)"
    assert len(res_data["history"]) == 8  # 8 complete steps in onboarding
    assert "evidence_hash" in res_data


@pytest.mark.anyio
async def test_api_onboarding_run_unsat_veto(onboarding_client):
    """Test full onboarding pipeline API endpoint triggers 403 HTTP Exception on UNSAT."""
    payload = {
        "name": "Underage Tech",
        "country": "CA",
        "age": 16,
        "identity_score": 0.95,
        "tier": "T1",
    }
    response = await onboarding_client.post("/api/v1/onboarding/run", json=payload)

    assert response.status_code == 403, f"Unexpected response: {response.text}"
    assert "ePCA Algebraic Deadlock" in response.json()["detail"]
