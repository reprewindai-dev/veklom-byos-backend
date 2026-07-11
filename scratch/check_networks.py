
from web3 import Web3
from eth_account import Account

pk = "cc347eb918f18772b2a6bc5e403ae75db8688a194077dd02209974f6cf8c274f"
acct = Account.from_key(pk)

networks = {
    "ETH Mainnet": "https://cloudflare-eth.com",
    "Arbitrum": "https://arb1.arbitrum.io/rpc",
    "Optimism": "https://mainnet.optimism.io",
    "Polygon": "https://polygon-rpc.com"
}

print(f"Checking balances for {acct.address} (Derived from the key you provided)")
for name, rpc in networks.items():
    try:
        w3 = Web3(Web3.HTTPProvider(rpc))
        bal = w3.eth.get_balance(acct.address)
        print(f"{name}: {w3.from_wei(bal, 'ether')} ETH/MATIC")
    except Exception as e:
        print(f"{name}: ERROR {e}")

