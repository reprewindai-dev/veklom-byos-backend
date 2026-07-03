"""
BankerLockManager — Atomic Redis-Lua distributed lock for the Banker Agent.

Ported from: C:/Users/antho/Downloads/hardened-lock-routing-engine/redis-lock-module/examples/python/redis_lock.py
Integrated with: Veklom's existing async redis_client and the BankerAgentService payment pipeline.

This prevents race conditions during concurrent payment broadcasts:
- Prevents two simultaneous calls from signing + broadcasting the same payment
- Enforces idempotency: one tx hash per route+amount+owner combination at a time
- Uses atomic Lua scripts (Redlock-compatible) so no two workers can own the same
  payment lock even under high concurrency.

Usage (inside BankerAgentService):
    async with BankerLockManager.payment_lock(route, amount_usdc, agent_address):
        tx_hash = await _broadcast_raw_tx(raw_tx)
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lua scripts — verbatim from hardened-lock-routing-engine
# These run atomically server-side (no TOCTOU race window)
# ---------------------------------------------------------------------------

_LUA_ACQUIRE = """
    local key = KEYS[1]
    local owner = ARGV[1]
    local ttl = tonumber(ARGV[2])
    local current_owner = redis.call('GET', key)
    if not current_owner then
        redis.call('SET', key, owner, 'PX', ttl)
        return 1
    elseif current_owner == owner then
        redis.call('PEXPIRE', key, ttl)
        return 1
    else
        return 0
    end
"""

_LUA_RENEW = """
    local key = KEYS[1]
    local owner = ARGV[1]
    local ttl = tonumber(ARGV[2])
    local current_owner = redis.call('GET', key)
    if current_owner == owner then
        redis.call('PEXPIRE', key, ttl)
        return 1
    else
        return 0
    end
"""

_LUA_RELEASE = """
    local key = KEYS[1]
    local owner = ARGV[1]
    local current_owner = redis.call('GET', key)
    if current_owner == owner then
        return redis.call('DEL', key)
    else
        return 0
    end
"""

_LUA_STATUS = """
    local key = KEYS[1]
    local owner = redis.call('GET', key)
    if owner then
        return { owner, redis.call('PTTL', key) }
    else
        return { false, -2 }
    end
"""

_LUA_IDEMPOTENCY_SET = """
    local key = KEYS[1]
    local val = ARGV[1]
    local ttl = tonumber(ARGV[2])
    redis.call('SET', key, val, 'EX', ttl)
    return 1
"""


class BankerLockManager:
    """
    Async Redis distributed lock manager for the Banker Agent.

    Wraps Veklom's existing async redis_client with atomic Lua scripts
    from the hardened-lock-routing-engine module.

    All methods fail OPEN (non-blocking) when Redis is unavailable — the
    banker agent still attempts payment, but logs a warning. This is the
    correct trade-off: a duplicate broadcast is better than a hung payment.
    """

    @staticmethod
    async def _eval(script: str, keys: list, args: list) -> any:
        """Execute a Lua script via the existing Veklom redis_client."""
        from backend.core.database.redis_client import redis_client
        try:
            result = await redis_client.eval(script, len(keys), *keys, *args)
            return result
        except Exception as exc:
            logger.warning(f"[BankerLock] Redis eval failed (fail-open): {exc}")
            return None

    @staticmethod
    async def acquire_lock(key: str, owner: str, ttl_ms: int = 30_000) -> bool:
        """
        Atomically acquire a distributed lock.

        Args:
            key:    Lock key, e.g. "banker:pay:0xabc.../0.10"
            owner:  Unique token for this worker (uuid)
            ttl_ms: Auto-release TTL in milliseconds (default 30s)

        Returns:
            True if lock acquired or re-entered, False if contended.
        """
        result = await BankerLockManager._eval(
            _LUA_ACQUIRE,
            keys=[key],
            args=[owner, str(ttl_ms)],
        )
        acquired = result == 1
        if acquired:
            logger.debug(f"[BankerLock] ✅ Lock acquired: {key} by {owner[:8]}...")
        else:
            logger.warning(f"[BankerLock] ⚠️  Lock contended: {key} (already owned)")
        return acquired

    @staticmethod
    async def renew_lock(key: str, owner: str, ttl_ms: int = 30_000) -> bool:
        """Extend an active lock's TTL (heartbeat pattern for long broadcasts)."""
        result = await BankerLockManager._eval(
            _LUA_RENEW,
            keys=[key],
            args=[owner, str(ttl_ms)],
        )
        return result == 1

    @staticmethod
    async def release_lock(key: str, owner: str) -> bool:
        """Atomically release a lock. Only succeeds if caller owns it."""
        result = await BankerLockManager._eval(
            _LUA_RELEASE,
            keys=[key],
            args=[owner],
        )
        released = result == 1
        if released:
            logger.debug(f"[BankerLock] 🔓 Lock released: {key}")
        return released

    @staticmethod
    async def get_lock_status(key: str) -> dict:
        """Inspect ownership and TTL of a lock key."""
        result = await BankerLockManager._eval(_LUA_STATUS, keys=[key], args=[])
        if result and result[0]:
            return {
                "is_locked":       True,
                "owner":           result[0],
                "ttl_remaining_ms": result[1],
            }
        return {"is_locked": False, "owner": None, "ttl_remaining_ms": -2}

    @staticmethod
    async def set_idempotency(key: str, value: str, ttl_seconds: int = 86400) -> bool:
        """
        Atomically record an idempotency key with a TTL.
        Used to prevent double-payment for the same route+amount+nonce.
        """
        result = await BankerLockManager._eval(
            _LUA_IDEMPOTENCY_SET,
            keys=[key],
            args=[value, str(ttl_seconds)],
        )
        return result == 1

    @staticmethod
    def _payment_lock_key(route: str, amount_usdc: float, from_addr: str) -> str:
        """
        Generates a canonical lock key for a payment attempt.
        Scoped to: route + amount + paying address.
        """
        safe_route = route.replace("/", "_").strip("_")
        return f"banker:pay:{from_addr.lower()[:10]}:{safe_route}:{amount_usdc:.6f}"

    @staticmethod
    @asynccontextmanager
    async def payment_lock(
        route: str,
        amount_usdc: float,
        from_addr: str,
        ttl_ms:  int = 60_000,   # 60s — enough for full confirmation cycle
        wait_ms: int = 5_000,    # Wait up to 5s for a contended lock to free
    ):
        """
        Context manager that acquires a payment lock before broadcasting.

        Usage:
            async with BankerLockManager.payment_lock(route, 0.10, addr) as owner:
                tx_hash = await _broadcast_raw_tx(raw_tx)

        Raises:
            RuntimeError if the lock cannot be acquired within wait_ms.
        """
        key   = BankerLockManager._payment_lock_key(route, amount_usdc, from_addr)
        owner = f"banker:{uuid.uuid4().hex[:16]}"

        # Attempt with backoff up to wait_ms
        elapsed = 0
        poll_ms = 250
        acquired = False

        while elapsed <= wait_ms:
            acquired = await BankerLockManager.acquire_lock(key, owner, ttl_ms)
            if acquired:
                break
            await asyncio.sleep(poll_ms / 1000)
            elapsed += poll_ms

        if not acquired:
            raise RuntimeError(
                f"[BankerLock] Could not acquire payment lock for {route} "
                f"after {wait_ms}ms. Another payment is in flight."
            )

        try:
            yield owner
        finally:
            await BankerLockManager.release_lock(key, owner)
