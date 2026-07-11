from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.core.services import banker_agent


@pytest.mark.asyncio
async def test_verify_payment_receipt_accepts_base_account_outer_transaction(monkeypatch):
    tx_hash = "0xbc6d472ce1a4d9df26801f746c19ab925f06861c71386ccd54deee3268baf3cc"
    usdc = banker_agent.BASE_USDC_CONTRACT
    treasury = "0x3a74772e925b54f7dad7fd95c9ba30825033f970"
    smart_wallet = "0x1111111111111111111111111111111111111111"
    entrypoint = "0x2222222222222222222222222222222222222222"

    async def fake_rpc(method, params):
        if method == "eth_getTransactionReceipt":
            return {
                "status": "0x1",
                "blockNumber": "0x10",
                "gasUsed": "0x5208",
                "logs": [
                    {
                        "address": usdc,
                        "topics": [
                            banker_agent.ERC20_TRANSFER_TOPIC,
                            "0x" + smart_wallet[2:].rjust(64, "0"),
                            "0x" + treasury[2:].rjust(64, "0"),
                        ],
                        "data": hex(100000),
                        "logIndex": "0x0",
                    }
                ],
            }
        if method == "eth_getTransactionByHash":
            return {
                "from": smart_wallet,
                "to": entrypoint,
                "gasPrice": "0x1",
            }
        raise AssertionError(f"unexpected rpc method {method}")

    monkeypatch.setattr(banker_agent, "_base_rpc", fake_rpc)

    payment = SimpleNamespace(
        asset="USDC",
        to_address=treasury,
        amount=Decimal("0.10"),
    )

    proof = await banker_agent._verify_payment_receipt(payment, tx_hash, 8453)

    assert proof["tx_hash"] == tx_hash
    assert proof["tx_to"] == entrypoint
    assert proof["usdc_contract"] == usdc.lower()
    assert proof["transfer"]["to"] == treasury
    assert proof["transfer"]["amount_micro"] == 100000
