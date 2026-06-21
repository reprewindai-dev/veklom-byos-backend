"""Tests for real-data compliance scoring (no hardcoded scores)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.apps.api.routers.compliance import _compute_compliance
from backend.core.database.database import Base
from backend.db.models.security import AuditLog, ComplianceCheck, SecurityEvent


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [AuditLog.__table__, ComplianceCheck.__table__, SecurityEvent.__table__]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _chain(ws: str, n: int) -> list[AuditLog]:
    """Build n audit rows with a valid prev_hash -> hash_chain linkage."""
    rows = []
    prev = ""
    for i in range(n):
        h = f"h{i}"
        rows.append(AuditLog(workspace_id=ws, action=f"a{i}", prev_hash=prev, hash_chain=h))
        prev = h
    return rows


async def test_empty_workspace_reflects_missing_audit_evidence(session):
    result = await _compute_compliance(session, "ws-empty", "HIPAA")
    # No checks, no audit trail -> audit_component baseline (60), not a fake 97.
    assert result["score"] == 60
    assert result["signals"]["audit_events"] == 0
    assert any("No audit-trail evidence" in f for f in result["findings"])


async def test_intact_audit_and_passing_checks_scores_high(session):
    ws = "ws-good"
    session.add_all(_chain(ws, 5))
    session.add(ComplianceCheck(workspace_id=ws, regulation="HIPAA", result="pass", score=0.98))
    await session.commit()

    result = await _compute_compliance(session, ws, "HIPAA")
    # 0.6*98 + 0.4*100 = 98.8 -> 99, no incident penalty.
    assert result["score"] == 99
    assert result["signals"]["audit_chain_intact"] is True
    assert result["signals"]["controls_evaluated"] == 1


async def test_open_incidents_penalize_score(session):
    ws = "ws-incidents"
    session.add_all(_chain(ws, 3))
    session.add(ComplianceCheck(workspace_id=ws, regulation="SOC2", result="pass", score=1.0))
    session.add(SecurityEvent(workspace_id=ws, event_type="intrusion", severity="critical", status="open"))
    session.add(SecurityEvent(workspace_id=ws, event_type="anomaly", severity="low", status="open"))
    await session.commit()

    result = await _compute_compliance(session, ws, "SOC2")
    # base = 0.6*100 + 0.4*100 = 100; penalty = 2*3 + 1*7 = 13 -> 87.
    assert result["signals"]["open_security_events"] == 2
    assert result["signals"]["incident_penalty"] == 13
    assert result["score"] == 87


async def test_broken_audit_chain_lowers_score(session):
    ws = "ws-tampered"
    rows = _chain(ws, 4)
    rows[2].prev_hash = "does-not-match"  # break the chain
    session.add_all(rows)
    await session.commit()

    result = await _compute_compliance(session, ws, "GDPR")
    assert result["signals"]["audit_chain_intact"] is False
    assert result["score"] == 40  # audit_component only, no checks
    assert any("hash-chain integrity" in f for f in result["findings"])


async def test_check_excludes_stored_checks(session):
    ws = "ws-check"
    session.add_all(_chain(ws, 2))
    # A previously stored failing check must NOT feed back into a fresh posture eval.
    session.add(ComplianceCheck(workspace_id=ws, regulation="HIPAA", result="review", score=0.10))
    await session.commit()

    posture = await _compute_compliance(session, ws, "HIPAA", use_stored_checks=False)
    assert posture["signals"]["controls_evaluated"] == 0
    assert posture["score"] == 100  # intact audit, no incidents
