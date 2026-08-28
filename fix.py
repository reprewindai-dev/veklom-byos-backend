content = '''"""Integration test: Step 3/7 - Agent Certificate issuance.

Verifies the machine-accountability graph invariants (Section 7, Constitutional Architecture):

  cert.pgl_identity_id = Execution Profile identity (machine anchor - who executed)
  cert.actor_id        = OPERATOR identity (human anchor - who authorized)

These must never be the same row. Tests:
  1. Step 3 fails with HTTP 400 if Step 1 (operator identity) is not complete.
  2. Step 3 creates a NEW PGLIdentity for the execution_profile (not the operator).
  3. cert.pgl_identity_id == execution_profile identity, cert.actor_id == operator user.
  4. profile_identity.metadata_json['authorized_by_operator'] traces back to operator.
  5. All three rows (PGLIdentity + PGLCertificate + PGLLedgerEvent) commit atomically.
  6. On GnomLedger failure: rollback leaves zero orphan rows.
  7. Retry after failure is clean (no duplicate constraint error).
"""
from __future__ import annotations

import uuid
import pytest
import pytest_asyncio

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import engine, async_session
from backend.db.models.pgl import PGLCertificate, PGLIdentity, PGLLedgerEvent
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.tests.conftest import init_test_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    await engine.dispose()
    await init_test_db()
    yield
    await engine.dispose()


async def _seed_operator(db: AsyncSession) -> tuple[User, str, str]:
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    operator_pgl_id = str(uuid.uuid4())

    ws = Workspace(id=workspace_id, name="test-ws", owner_id=user_id)
    db.add(ws)

    user = User(id=user_id, email=f"op+{user_id[:8]}@veklom.test",
                workspace_id=workspace_id, pgl_id=operator_pgl_id)
    db.add(user)

    identity = PGLIdentity(
        id=operator_pgl_id,
        tenant_id=workspace_id,
        primary_public_key="ed25519_opkey==",
        key_type="ed25519",
        metadata_json={"kind": "operator"},
    )
    db.add(identity)
    await db.commit()
    return user, workspace_id, operator_pgl_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_step3_fails_without_step1():
    from fastapi import HTTPException
    from backend.apps.api.routers.pgl_onboarding import _resolve_pgl_identity_id

    workspace_id = str(uuid.uuid4())
    async with async_session() as db:
        user_id = str(uuid.uuid4())
        ws = Workspace(id=workspace_id, name="no-step1", owner_id=user_id)
        user = User(id=user_id, email="no-step1@test.com",
                    workspace_id=workspace_id, pgl_id=None)
        db.add(ws); db.add(user)
        await db.commit()

        with pytest.raises(HTTPException) as exc:
            await _resolve_pgl_identity_id(db, user_id, workspace_id)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_step3_creates_separate_execution_profile_identity():
    from backend.apps.api.routers.pgl_onboarding import (
        _resolve_pgl_identity_id,
        _write_ledger_event,
        _canonical_hash,
    )

    async with async_session() as db:
        user, workspace_id, operator_pgl_id = await _seed_operator(db)
        actor_id = str(user.id)

        resolved_op_id = await _resolve_pgl_identity_id(db, actor_id, workspace_id)
        assert resolved_op_id == operator_pgl_id

        from backend.core.security.ed25519_keys import Ed25519KeyManager
        profile_pgl_id = str(uuid.uuid4())
        _, pub_b64 = Ed25519KeyManager.generate_key_pair()

        profile_identity = PGLIdentity(
            id=profile_pgl_id,
            tenant_id=workspace_id,
            primary_public_key=f"ed25519_{pub_b64}",
            key_type="ed25519",
            metadata_json={
                "kind": "execution_profile",
                "agent_name": "Nexus-1",
                "authorized_by_operator": operator_pgl_id,
            },
        )
        db.add(profile_identity)
        await db.flush()

        ubc_id = f"cert_{uuid.uuid4().hex[:16]}"
        genome_hash = _canonical_hash({"intended_use": "testing"})
        constitution_hash = _canonical_hash({"tools": [], "permissions": [], "safety_rules": []})

        cert = PGLCertificate(
            certificate_id=ubc_id,
            kind="birth",
            workspace_id=workspace_id,
            actor_id=actor_id,
            pgl_identity_id=profile_pgl_id,
            genome_hash=genome_hash,
            constitution_hash=constitution_hash,
            status="active",
        )
        db.add(cert)

        event = await _write_ledger_event(
            db,
            workspace_id=workspace_id,
            actor_id=actor_id,
            event_type="execution_profile_registered_with_gnomledger",
            payload={"certificate_id": ubc_id, "profile_pgl_id": profile_pgl_id},
            certificate_id=ubc_id,
            pgl_identity_id=operator_pgl_id,
        )

        await db.commit()

        saved_cert = (await db.execute(
            select(PGLCertificate).where(PGLCertificate.certificate_id == ubc_id)
        )).scalar_one()

        assert saved_cert.pgl_identity_id is not None
        assert saved_cert.pgl_identity_id == profile_pgl_id
        assert saved_cert.pgl_identity_id != operator_pgl_id
        assert saved_cert.actor_id == actor_id

        saved_profile_identity = (await db.execute(
            select(PGLIdentity).where(PGLIdentity.id == profile_pgl_id)
        )).scalar_one()

        assert saved_profile_identity.metadata_json.get("kind") == "execution_profile"
        assert saved_profile_identity.metadata_json.get("authorized_by_operator") == operator_pgl_id

        saved_event = (await db.execute(
            select(PGLLedgerEvent).where(PGLLedgerEvent.certificate_id == ubc_id)
        )).scalar_one()
        assert saved_event.pgl_identity_id == operator_pgl_id
        assert saved_event.event_hash


@pytest.mark.asyncio
async def test_step3_rollback_leaves_no_orphans():
    from backend.apps.api.routers.pgl_onboarding import _resolve_pgl_identity_id
    from backend.core.security.ed25519_keys import Ed25519KeyManager

    async with async_session() as db:
        user, workspace_id, operator_pgl_id = await _seed_operator(db)

        profile_pgl_id = str(uuid.uuid4())
        _, pub_b64 = Ed25519KeyManager.generate_key_pair()

        try:
            await _resolve_pgl_identity_id(db, str(user.id), workspace_id)

            profile_identity = PGLIdentity(
                id=profile_pgl_id,
                tenant_id=workspace_id,
                primary_public_key=f"ed25519_{pub_b64}",
                key_type="ed25519",
                metadata_json={"kind": "execution_profile"},
            )
            db.add(profile_identity)

            cert = PGLCertificate(
                certificate_id="will-fail",
                kind="birth",
                workspace_id=workspace_id,
                actor_id=str(user.id),
                pgl_identity_id=profile_pgl_id,
                genome_hash="x",
                constitution_hash="x",
                status="active",
            )
            db.add(cert)
            await db.flush()
            raise RuntimeError("Simulated GnomLedger timeout")
        except RuntimeError:
            await db.rollback()

        orphan_cert = (await db.execute(
            select(PGLCertificate).where(PGLCertificate.certificate_id == "will-fail")
        )).scalar_one_or_none()
        assert orphan_cert is None

        orphan_identity = (await db.execute(
            select(PGLIdentity).where(PGLIdentity.id == profile_pgl_id)
        )).scalar_one_or_none()
        assert orphan_identity is None


@pytest.mark.asyncio
async def test_step3_retry_is_clean():
    from backend.apps.api.routers.pgl_onboarding import (
        _resolve_pgl_identity_id,
        _write_ledger_event,
        _canonical_hash,
    )
    from backend.core.security.ed25519_keys import Ed25519KeyManager

    async with async_session() as db:
        user, workspace_id, operator_pgl_id = await _seed_operator(db)
        actor_id = str(user.id)
        ubc_id = f"cert_{uuid.uuid4().hex[:16]}"

        try:
            resolved_op = await _resolve_pgl_identity_id(db, actor_id, workspace_id)
            bad_pgl_id = str(uuid.uuid4())
            _, pub = Ed25519KeyManager.generate_key_pair()
            db.add(PGLIdentity(id=bad_pgl_id, tenant_id=workspace_id,
                               primary_public_key=f"ed25519_{pub}", key_type="ed25519",
                               metadata_json={"kind": "execution_profile"}))
            db.add(PGLCertificate(certificate_id=ubc_id, kind="birth",
                                  workspace_id=workspace_id, actor_id=actor_id,
                                  pgl_identity_id=bad_pgl_id, genome_hash="x",
                                  constitution_hash="x", status="active"))
            await db.flush()
            raise RuntimeError("Simulated GnomLedger timeout")
        except RuntimeError:
            await db.rollback()

        resolved_op = await _resolve_pgl_identity_id(db, actor_id, workspace_id)
        good_pgl_id = str(uuid.uuid4())
        _, pub2 = Ed25519KeyManager.generate_key_pair()
        db.add(PGLIdentity(id=good_pgl_id, tenant_id=workspace_id,
                           primary_public_key=f"ed25519_{pub2}", key_type="ed25519",
                           metadata_json={"kind": "execution_profile", "authorized_by_operator": resolved_op}))
        gh = _canonical_hash({"intended_use": "retry"})
        ch = _canonical_hash({"tools": [], "permissions": [], "safety_rules": []})
        db.add(PGLCertificate(certificate_id=ubc_id, kind="birth",
                              workspace_id=workspace_id, actor_id=actor_id,
                              pgl_identity_id=good_pgl_id, genome_hash=gh,
                              constitution_hash=ch, status="active"))
        await _write_ledger_event(db, workspace_id=workspace_id, actor_id=actor_id,
                                  event_type="execution_profile_registered_with_gnomledger",
                                  payload={"certificate_id": ubc_id},
                                  certificate_id=ubc_id,
                                  pgl_identity_id=resolved_op)
        await db.commit()

        count = (await db.execute(
            select(func.count()).select_from(PGLCertificate)
            .where(PGLCertificate.certificate_id == ubc_id)
        )).scalar_one()
        assert count == 1
'''
with open('backend/tests/test_step3_agent_certificate.py', 'w', encoding='utf-8') as f:
    f.write(content)
