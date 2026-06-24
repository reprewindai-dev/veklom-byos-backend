"""Tests for SettlementLedgerRepository.

Coverage
--------
1. Duplicate-request replay  – idempotency key constraint returns existing row
2. Settlement success        – PENDING → SETTLED transition
3. Failed settlement         – PENDING → FAILED transition
4. Terminal re-transition    – SETTLED/FAILED cannot be transitioned again
5. Cross-tenant isolation    – get_for_execution respects tenant_id filter
6. list_unsettled ordering   – oldest-first, tenant-scoped

Fixture strategy
----------------
Uses an in-memory SQLite database via SQLAlchemy's async engine so the
test suite runs without a live Postgres instance.  The GUID TypeDecorator
and JSONB variant fall back to CHAR/JSON cleanly in SQLite.
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database.database import Base
from backend.db.models.ledger import SettlementLedger, SettlementStatus  # noqa: F401 – registers model
from backend.db.repositories.settlement_repo import SettlementLedgerRepository

# ── Fixtures ──────────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh in-memory SQLite session per test."""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _repo(session: AsyncSession) -> SettlementLedgerRepository:
    return SettlementLedgerRepository(session)


def _key(suffix: str = "") -> str:
    return f"test-idem-{uuid.uuid4().hex}{suffix}"


# ── Helper to create a standard fee entry ─────────────────────────────────────

async def _make_entry(
    repo: SettlementLedgerRepository,
    *,
    tenant_id: str = "tenant-alpha",
    execution_id: str | None = None,
    idempotency_key: str | None = None,
    amount: int = 1_000_000,
) -> SettlementLedger:
    return await repo.create_fee_entry(
        tenant_id=tenant_id,
        provider="veklom",
        fee_type="test_fee",
        amount=amount,
        currency="USDC",
        idempotency_key=idempotency_key or _key(),
        execution_id=execution_id or uuid.uuid4().hex,
    )


# ── Test 1: Idempotency key replay ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_fee_entry_idempotent_replay(db_session: AsyncSession) -> None:
    """Calling create_fee_entry twice with the same idempotency_key must return
    the same row both times without raising and without creating a duplicate."""
    repo = _repo(db_session)
    key = _key()
    exec_id = uuid.uuid4().hex

    first = await repo.create_fee_entry(
        tenant_id="tenant-alpha",
        provider="veklom",
        fee_type="rag",
        amount=500_000,
        currency="USDC",
        idempotency_key=key,
        execution_id=exec_id,
    )
    await db_session.flush()

    second = await repo.create_fee_entry(
        tenant_id="tenant-alpha",
        provider="veklom",
        fee_type="rag",
        amount=999_999,  # different amount – must be ignored
        currency="USDC",
        idempotency_key=key,
        execution_id=exec_id,
    )

    assert first.id == second.id, "Replay must return the original row"
    assert second.amount == 500_000, "Original amount must be preserved on replay"
    assert second.status == SettlementStatus.PENDING


# ── Test 2: Settlement success transition ─────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_settled_transitions_status(db_session: AsyncSession) -> None:
    repo = _repo(db_session)
    entry = await _make_entry(repo)
    await db_session.flush()

    settled = await repo.mark_settled(
        ledger_id=str(entry.id),
        settlement_tx_hash="0xdeadbeef",
        external_payment_id="pay_123",
    )

    assert settled.status == SettlementStatus.SETTLED
    assert settled.settlement_tx_hash == "0xdeadbeef"
    assert settled.external_payment_id == "pay_123"


# ── Test 3: Failed settlement transition ──────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_failed_transitions_status(db_session: AsyncSession) -> None:
    repo = _repo(db_session)
    entry = await _make_entry(repo)
    await db_session.flush()

    failed = await repo.mark_failed(
        ledger_id=str(entry.id),
        failure_code="PROVIDER_TIMEOUT",
        failure_reason="Upstream timed out after 30 s",
    )

    assert failed.status == SettlementStatus.FAILED
    assert failed.failure_code == "PROVIDER_TIMEOUT"
    assert "30 s" in (failed.failure_reason or "")


# ── Test 4: Terminal state re-transition is rejected ──────────────────────────

@pytest.mark.asyncio
async def test_cannot_retransition_settled_row(db_session: AsyncSession) -> None:
    repo = _repo(db_session)
    entry = await _make_entry(repo)
    await db_session.flush()

    await repo.mark_settled(ledger_id=str(entry.id))

    with pytest.raises(ValueError, match="already settled"):
        await repo.mark_failed(
            ledger_id=str(entry.id),
            failure_code="LATE_FAIL",
        )


@pytest.mark.asyncio
async def test_cannot_retransition_failed_row(db_session: AsyncSession) -> None:
    repo = _repo(db_session)
    entry = await _make_entry(repo)
    await db_session.flush()

    await repo.mark_failed(ledger_id=str(entry.id), failure_code="ERR")

    with pytest.raises(ValueError, match="already failed"):
        await repo.mark_settled(ledger_id=str(entry.id))


# ── Test 5: Cross-tenant isolation ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_for_execution_cross_tenant_isolation(db_session: AsyncSession) -> None:
    """get_for_execution with tenant_id must not return rows from other tenants
    sharing the same execution_id (impossible in practice but guarded by design)."""
    repo = _repo(db_session)
    shared_exec = uuid.uuid4().hex

    alpha = await _make_entry(repo, tenant_id="tenant-alpha", execution_id=shared_exec)
    beta = await _make_entry(repo, tenant_id="tenant-beta", execution_id=shared_exec)
    await db_session.flush()

    alpha_rows = await repo.get_for_execution(shared_exec, tenant_id="tenant-alpha")
    beta_rows = await repo.get_for_execution(shared_exec, tenant_id="tenant-beta")
    all_rows = await repo.get_for_execution(shared_exec)

    assert len(alpha_rows) == 1 and alpha_rows[0].id == alpha.id
    assert len(beta_rows) == 1 and beta_rows[0].id == beta.id
    assert len(all_rows) == 2


# ── Test 6: list_unsettled ordering and tenant scoping ────────────────────────

@pytest.mark.asyncio
async def test_list_unsettled_ordering_and_tenant_scope(db_session: AsyncSession) -> None:
    repo = _repo(db_session)

    a = await _make_entry(repo, tenant_id="tenant-alpha", amount=100)
    b = await _make_entry(repo, tenant_id="tenant-alpha", amount=200)
    c = await _make_entry(repo, tenant_id="tenant-beta", amount=300)
    await db_session.flush()

    # Mark c as settled – must not appear in list_unsettled
    await repo.mark_settled(ledger_id=str(c.id))

    alpha_unsettled = await repo.list_unsettled(tenant_id="tenant-alpha")
    all_unsettled = await repo.list_unsettled()

    assert len(alpha_unsettled) == 2
    # Oldest first (a before b)
    assert alpha_unsettled[0].id == a.id
    assert alpha_unsettled[1].id == b.id

    # c is SETTLED so must not appear in all_unsettled
    all_ids = {str(r.id) for r in all_unsettled}
    assert str(c.id) not in all_ids
