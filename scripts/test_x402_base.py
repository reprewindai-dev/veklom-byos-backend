#!/usr/bin/env python3
"""
Veklom Base Mainnet x402 Payment Simulation Script.

Simulates the automated x402 facilitator for Bronze, Medium, and Good API tiers,
validating that the backend SettlementLedger properly records mainnet USDC transactions.
"""

import asyncio
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure backend folder is in path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Local testnet db config
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg: str):
    print(f"[{Colors.OKBLUE}INFO{Colors.ENDC}] {msg}")

def log_success(msg: str):
    print(f"[{Colors.OKGREEN}PASS{Colors.ENDC}] {Colors.BOLD}{msg}{Colors.ENDC}")

from fastapi.testclient import TestClient
from backend.apps.api.main import app
from backend.core.config.settings import settings
from backend.core.database.database import async_session, engine, Base
from backend.db.models.billing import Order, Ledger, WebhookReceipt, Payment

async def prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[Order.__table__, Ledger.__table__, WebhookReceipt.__table__, Payment.__table__]
        ))

def generate_signature(payload_bytes: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

async def run_base_tests():
    log_info("Initializing Base Mainnet Mock Metadata...")
    await prepare_database()
    
    original_secret = settings.WEBHOOK_SECRET
    settings.WEBHOOK_SECRET = "base_secret_key"
    client = TestClient(app)
    
    try:
        print(f"\n{Colors.HEADER}=== RUNNING BASE MAINNET FACILITATOR ==={Colors.ENDC}\n")
        
        # Test configurations for tiers
        tiers = [
            {"tier": "bronze", "amount": 0.001},
            {"tier": "medium", "amount": 0.05},
            {"tier": "good", "amount": 0.25}
        ]
        
        for t in tiers:
            tier_name = t["tier"].upper()
            amount = t["amount"]
            log_info(f"Simulating x402 Mainnet Webhook for {tier_name} API (${amount} USDC)...")
            
            order_id = f"order-{tier_name.lower()}-{uuid.uuid4().hex[:8]}"
            tx_hash = f"0xbase{uuid.uuid4().hex[:30]}"
            
            async with async_session() as db:
                db.add(Order(
                    order_id=order_id, amount=amount, currency="USDC",
                    user_id="base_agent", workspace_id="ws-mainnet", status="pending"
                ))
                await db.commit()
            
            payload = {
                "type": "tx_confirmed",
                "tx_hash": tx_hash,
                "order_id": order_id,
                "confirmations": 3,
                "amount": amount,
                "chain_id": 8453,
                "network": "base"
            }
            payload_bytes = json.dumps(payload).encode()
            signature = generate_signature(payload_bytes, settings.WEBHOOK_SECRET)
            
            response = client.post(
                "/api/v1/webhook/payment",
                content=payload_bytes,
                headers={
                    "X-Signature": signature,
                    "X-Idempotency-Key": f"idem-base-{uuid.uuid4().hex}"
                }
            )
            
            assert response.status_code == 200, f"Failed webhook for {tier_name}: {response.text}"
            
            async with async_session() as db:
                from sqlalchemy import select
                res = await db.execute(select(Ledger).where(Ledger.order_id == order_id))
                ledgers = res.scalars().all()
                assert len(ledgers) == 1
                assert ledgers[0].tx_hash == tx_hash
                assert ledgers[0].amount == amount
                
            log_success(f"{tier_name} API webhook settled correctly in ledger on Base Mainnet.")
        
        print(f"\n{Colors.OKGREEN}All Base Mainnet automated facilitator simulations passed!{Colors.ENDC}\n")
        
    finally:
        settings.WEBHOOK_SECRET = original_secret

if __name__ == "__main__":
    asyncio.run(run_base_tests())
