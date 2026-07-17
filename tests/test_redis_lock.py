import pytest
import asyncio
from backend.core.database.redis_client import lock_manager

@pytest.mark.asyncio
async def test_redis_lock_lifecycle():
    key = "lock:test:unit_test_run"
    owner = "client:worker_test_1"
    competitor = "client:worker_test_2"

    # Ensure clean state
    await lock_manager.release_lock(key, owner)
    await lock_manager.release_lock(key, competitor)

    # 1. Acquire Lock
    acquired = await lock_manager.acquire_lock(key, owner, 5000)
    assert acquired is True

    # 2. Confirm Status
    status = await lock_manager.get_lock_status(key)
    assert status["isLocked"] is True
    assert status["owner"] == owner
    assert status["ttlRemainingMs"] > 0

    # 3. Block Competitor Acquire
    blocked = await lock_manager.acquire_lock(key, competitor, 5000)
    assert blocked is False

    # 4. Reentrancy (Same owner can extend/re-enter)
    reentered = await lock_manager.acquire_lock(key, owner, 10000)
    assert reentered is True
    
    status_re = await lock_manager.get_lock_status(key)
    assert status_re["owner"] == owner
    assert status_re["ttlRemainingMs"] > 4000

    # 5. Renew Lock
    renewed = await lock_manager.renew_lock(key, owner, 8000)
    assert renewed is True

    # 6. Block Competitor Release
    stolen_release = await lock_manager.release_lock(key, competitor)
    assert stolen_release is False

    # 7. Release Lock Safely
    released = await lock_manager.release_lock(key, owner)
    assert released is True

    # 8. Confirm Free State
    status_free = await lock_manager.get_lock_status(key)
    assert status_free["isLocked"] is False
    assert status_free["owner"] is None
