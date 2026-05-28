#!/usr/bin/env python3
"""
Reconciliation job to detect drift between ledger and on-chain state.

This script compares the ledger entries with on-chain transaction receipts
to identify any discrepancies in payment amounts.

Usage:
    python scripts/reconciliation.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.core.config.settings import settings
from backend.db.models.billing import Ledger, ReconFinding


async def get_ledger_sum(db: AsyncSession) -> dict:
    """Get the sum of ledger entries per tx_hash."""
    result = await db.execute(
        text("""
            SELECT tx_hash, SUM(amount) AS ledger_sum
            FROM ledger
            WHERE tx_hash IS NOT NULL
            GROUP BY tx_hash
        """)
    )
    return {row[0]: row[1] for row in result}


async def get_onchain_value(tx_hash: str) -> float:
    """
    Get the on-chain value for a transaction.
    
    This is a placeholder - in production, you would:
    - Call eth_getTransactionReceipt via Web3
    - Parse Transfer logs for token transfers
    - Decode the amount with proper decimals
    - Return the authoritative value
    
    For now, this returns 0.0 as a placeholder.
    """
    # TODO: Integrate with Web3 provider
    # from web3 import Web3
    # w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
    # receipt = w3.eth.get_transaction_receipt(tx_hash)
    # Parse logs to get transfer amount
    return 0.0


async def run_reconciliation(db: AsyncSession):
    """Run the reconciliation job."""
    print(f"[{datetime.now(timezone.utc)}] Starting reconciliation job...")
    
    # Get ledger sums
    ledger_sums = await get_ledger_sum(db)
    
    print(f"[{datetime.now(timezone.utc)}] Checking {len(ledger_sums)} transactions...")
    
    findings_count = 0
    
    for tx_hash, ledger_sum in ledger_sums.items():
        try:
            # Get on-chain value
            chain_sum = await get_onchain_value(tx_hash)
            
            # Compare
            if abs(ledger_sum - chain_sum) > 0.0001:  # Allow small floating point differences
                # Record finding
                finding = ReconFinding(
                    tx_hash=tx_hash,
                    ledger_sum=ledger_sum,
                    chain_sum=chain_sum,
                    detected_at=datetime.now(timezone.utc)
                )
                
                # Upsert (insert or update)
                await db.execute(
                    text("""
                        INSERT INTO recon_findings (tx_hash, ledger_sum, chain_sum, detected_at)
                        VALUES (:tx_hash, :ledger_sum, :chain_sum, :detected_at)
                        ON CONFLICT (tx_hash) DO UPDATE
                        SET ledger_sum = :ledger_sum, chain_sum = :chain_sum, detected_at = :detected_at
                    """),
                    {
                        "tx_hash": tx_hash,
                        "ledger_sum": ledger_sum,
                        "chain_sum": chain_sum,
                        "detected_at": datetime.now(timezone.utc)
                    }
                )
                
                findings_count += 1
                print(f"[{datetime.now(timezone.utc)}] Mismatch found: {tx_hash} - ledger: {ledger_sum}, chain: {chain_sum}")
            
        except Exception as e:
            print(f"[{datetime.now(timezone.utc)}] Error processing {tx_hash}: {e}")
    
    await db.commit()
    print(f"[{datetime.now(timezone.utc)}] Reconciliation complete. {findings_count} findings recorded.")


async def main():
    """Main entry point."""
    # Create database engine
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        await run_reconciliation(db)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
