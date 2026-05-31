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
    
    Integrates with Web3 provider to fetch transaction receipt and parse
    Transfer logs for token transfers.
    """
    try:
        from web3 import Web3
        from web3.exceptions import TransactionNotFound
        
        # Initialize Web3 provider
        rpc_url = os.getenv("RPC_URL", "https://eth.llamarpc.com")
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not w3.is_connected():
            print(f"[{datetime.now(timezone.utc)}] Failed to connect to Web3 provider")
            return 0.0
        
        # Get transaction receipt
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        
        if not receipt or receipt.status != 1:
            print(f"[{datetime.now(timezone.utc)}] Transaction {tx_hash} failed or not found")
            return 0.0
        
        # Parse logs to find Transfer events
        # This is a simplified version - in production you would decode the logs
        # based on the token contract ABI
        total_amount = 0.0
        
        for log in receipt.logs:
            # Check if this is a Transfer event (topic[0] is the event signature)
            # Transfer(address indexed from, address indexed to, uint256 value)
            if len(log.topics) >= 3:
                # Extract value from log data (simplified)
                # In production, decode using ABI
                try:
                    value = int(log.data.hex(), 16) if log.data else 0
                    # Convert to float (assuming 18 decimals for ERC20)
                    amount = value / 1e18
                    total_amount += amount
                except (ValueError, AttributeError):
                    pass
        
        return total_amount
        
    except ImportError:
        print(f"[{datetime.now(timezone.utc)}] Web3 not installed, returning 0.0")
        return 0.0
    except Exception as e:
        print(f"[{datetime.now(timezone.utc)}] Error fetching on-chain value for {tx_hash}: {e}")
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
