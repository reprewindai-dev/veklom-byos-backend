import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.apps.api.main import app
from backend.apps.api.routers.onboarding_demo import evaluate_epca_z3, calculate_semantic_drift
from backend.core.database.database import Base, engine

# Ensure models are imported so they register with Base.metadata
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.pgl import PGLIdentity, PGLCertificate, PGLLedgerEvent
from backend.db.models.billing import WalletTransaction

client = TestClient(app)


# Run database initialization of specific tables to avoid SQLite JSONB compile errors on unrelated tables
async def init_db_on_import():
    tables_to_create = [
        User.__table__,
        Workspace.__table__,
        PGLIdentity.__table__,
        PGLCertificate.__table__,
        PGLLedgerEvent.__table__,
        WalletTransaction.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=tables_to_create,
        ))

asyncio.run(init_db_on_import())


def test_calculate_semantic_drift():
    """Verify semantic drift increases over successive workflow cycles."""
    # Step 0: Initial step, drift should be exactly 0
    drift_0 = calculate_semantic_drift(0)
    assert drift_0 == 0.0

    # Step 1: Small increment in drift angle
    drift_1 = calculate_semantic_drift(1)
    assert drift_1 > 0.0

    # Step 5: High drift
    drift_5 = calculate_semantic_drift(5)
    assert drift_5 > drift_1


def test_epca_z3_satisfiable():
    """Verify that compliant user attributes satisfy the Z3 safety axioms (SAT)."""
    is_sat, message = evaluate_epca_z3(
        country="CA",
        age=25,
        identity_score=0.95,
        authorized=True
    )
    assert is_sat is True
    assert "SATISFIABLE" in message


def test_epca_z3_unsat_sanctioned():
    """Verify that sanctioned countries trigger an immediate UNSAT compliance veto."""
    is_sat, message = evaluate_epca_z3(
        country="RU",
        age=25,
        identity_score=0.95,
        authorized=True
    )
    assert is_sat is False
    assert "UNSATISFIABLE" in message


def test_epca_z3_unsat_underage():
    """Verify representative representative being underage triggers an UNSAT compliance veto."""
    is_sat, message = evaluate_epca_z3(
        country="CA",
        age=17,
        identity_score=0.95,
        authorized=True
    )
    assert is_sat is False
    assert "UNSATISFIABLE" in message


def test_epca_z3_unsat_low_biometrics():
    """Verify low biometric score triggers an UNSAT compliance veto."""
    is_sat, message = evaluate_epca_z3(
        country="CA",
        age=25,
        identity_score=0.79,
        authorized=True
    )
    assert is_sat is False
    assert "UNSATISFIABLE" in message


def test_api_onboarding_run_satisfiable():
    """Test full onboarding pipeline API endpoint for SAT execution."""
    payload = {
        "name": "Acme Corp",
        "country": "CA",
        "age": 30,
        "identity_score": 0.98,
        "tier": "T2"
    }
    response = client.post("/api/v1/onboarding/run", json=payload)

    assert response.status_code == 200, f"Unexpected response: {response.text}"
    res_data = response.json()
    assert res_data["name"] == "Acme Corp"
    assert res_data["status"] == "APPROVED"
    assert res_data["epca_result"] == "SATISFIABLE (SAT)"
    assert len(res_data["history"]) == 8  # 8 complete steps in onboarding
    assert "evidence_hash" in res_data


def test_api_onboarding_run_unsat_veto():
    """Test full onboarding pipeline API endpoint triggers 403 HTTP Exception on UNSAT."""
    payload = {
        "name": "Underage Tech",
        "country": "CA",
        "age": 16,
        "identity_score": 0.95,
        "tier": "T1"
    }
    response = client.post("/api/v1/onboarding/run", json=payload)

    assert response.status_code == 403, f"Unexpected response: {response.text}"
    assert "ePCA Algebraic Deadlock" in response.json()["detail"]
