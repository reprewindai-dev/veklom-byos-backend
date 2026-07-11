from fastapi import APIRouter, Depends
import uuid
import datetime

router = APIRouter(prefix="/wallet", tags=["Workspace Treasury Wallet"])

@router.get("/balance")
async def get_wallet_balance():
    # Return true balance for demo workspace
    return {
        "balance": 450.75,
        "tokens": 450.75
    }

@router.get("/transactions")
async def get_wallet_transactions():
    now = datetime.datetime.utcnow()
    # Mocking ledger history as expected by UI. 
    # In full production this hits SettlementLedger.
    return [
        {
            "id": str(uuid.uuid4()),
            "type": "deposit",
            "amount": 500.00,
            "status": "completed",
            "timestamp": (now - datetime.timedelta(days=2)).isoformat(),
            "description": "Stripe Top-up",
            "txHash": "0x5fca4b76a086a9f4e242a4b89968a41bc9eb92f153a4c495914ab77de0fc855"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "withdrawal",
            "amount": -49.25,
            "status": "completed",
            "timestamp": (now - datetime.timedelta(days=1)).isoformat(),
            "description": "SLA Slash Payment",
            "txHash": "0x12a4b89968a41bc9eb92f153a4c495914ab77de0fc855b7fca4b76a086a9f4e2"
        }
    ]

@router.get("/stats/usage")
async def get_wallet_usage():
    return {
        "last_30d": 124.50,
        "spent_30d": 124.50,
        "avg_per_day": 4.15
    }

@router.get("/topup/options")
async def get_topup_options():
    return [
        {"id": "tier1", "amount": 50, "bonus": 0},
        {"id": "tier2", "amount": 100, "bonus": 5},
        {"id": "tier3", "amount": 500, "bonus": 50},
        {"id": "tier4", "amount": 1000, "bonus": 150}
    ]

@router.post("/topup/checkout")
async def topup_checkout(payload: dict):
    # Simulated stripe checkout url
    amount = payload.get("amount", 50)
    return {"url": f"https://checkout.stripe.com/pay/cs_test_mock?amount={amount}"}
