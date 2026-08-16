"""Regression tests for Settlement and Fault Attribution."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from backend.core.services.settlement_service import SettlementService
from backend.db.models.ledger import SettlementLedger, SettlementStatus

class MockSession:
    def __init__(self, entry=None):
        self.entry = entry
        self.committed = False
        self.added = []
    
    async def execute(self, stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = self.entry
        return result
        
    async def commit(self):
        self.committed = True

    def add(self, obj):
        self.added.append(obj)

@pytest.mark.asyncio
async def test_cappo_denial_voids_execution():
    ledger_id = uuid.uuid4()
    entry = SettlementLedger(id=ledger_id, status=SettlementStatus.PENDING, amount=100)
    db = MockSession(entry)
    
    success = await SettlementService.void_execution(db, ledger_id, reason="CAPPO_DENIED")
    assert success is True
    assert entry.status == SettlementStatus.VOID_NOT_EXECUTED
    assert entry.failure_reason == "CAPPO_DENIED"
    assert db.committed is True

@pytest.mark.asyncio
async def test_successful_execution_executed_gas():
    ledger_id = uuid.uuid4()
    entry = SettlementLedger(id=ledger_id, status=SettlementStatus.PENDING, amount=100, currency="USDC")
    db = MockSession(entry)
    
    # Mocking successful bind and finalize
    bound = await SettlementService.bind_execution(db, ledger_id, execution_hash="0x123")
    assert bound is True
    
    finalized = await SettlementService.finalize_settlement(db, ledger_id, released_amount=100)
    assert finalized is True
    assert entry.status == SettlementStatus.SETTLED

@pytest.mark.asyncio
async def test_unresolved_timeout_cannot_finalize():
    ledger_id = uuid.uuid4()
    # E.g. TIMEOUT_PENDING_ATTRIBUTION mapped to FAILED or a pending state without execution hash
    entry = SettlementLedger(id=ledger_id, status=SettlementStatus.PENDING, amount=100)
    db = MockSession(entry)
    
    # Try to finalize without binding execution hash
    finalized = await SettlementService.finalize_settlement(db, ledger_id, released_amount=100)
    assert finalized is False
    assert entry.status == SettlementStatus.PENDING
    assert db.committed is False

@pytest.mark.asyncio
async def test_over_release_prevented():
    ledger_id = uuid.uuid4()
    entry = SettlementLedger(id=ledger_id, status=SettlementStatus.PENDING, amount=100)
    db = MockSession(entry)
    
    await SettlementService.bind_execution(db, ledger_id, execution_hash="0x123")
    finalized = await SettlementService.finalize_settlement(db, ledger_id, released_amount=200)
    assert finalized is False
    assert entry.status == SettlementStatus.PENDING
