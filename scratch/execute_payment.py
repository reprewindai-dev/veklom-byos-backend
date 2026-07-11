
import os
import sys
import json
import httpx
from web3 import Web3
from eth_account import Account

# Constants
RPC_URL = "https://sepolia.base.org"
BASE_URL = "https://api.veklom.com"
TREASURY_WALLET = "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970"
PRIVATE_KEY = "cc347eb918f18772b2a6bc5e403ae75db8688a194077dd02209974f6cf8c274f"

print(f"[*] Initializing with Private Key...")
account = Account.from_key(PRIVATE_KEY)
print(f"[*] Wallet Address: {account.address}")
print(f"[*] Treasury: {TREASURY_WALLET}")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    print("[!] Could not connect to Base Sepolia RPC")
    sys.exit(1)

balance_wei = w3.eth.get_balance(account.address)
print(f"[*] ETH Balance: {w3.from_wei(balance_wei, 'ether')} ETH")

print("\n[*] Attempting to execute payment for /score...")
try:
    tx = {
        "nonce": w3.eth.get_transaction_count(account.address),
        "to": TREASURY_WALLET,
        "value": w3.to_wei(0.0001, "ether"),
        "gas": 21000,
        "gasPrice": w3.eth.gas_price,
        "chainId": 84532
    }
    signed_tx = account.sign_transaction(tx)
    raw_tx = getattr(signed_tx, "rawTransaction", None) or getattr(signed_tx, "raw_transaction")
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    print(f"  [+] Transaction broadcasted! Hash: {tx_hash.hex()}")
    
    proof = {"payment_proof_hash": tx_hash.hex()}
    
    resp = httpx.post(
        f"{BASE_URL}/api/v1/x402/score",
        headers={"X-Payment-Verified": json.dumps(proof)}
    )
    print(f"  [>] API Response: {resp.status_code} {resp.text}")
    
except Exception as e:
    print(f"  [!] Failed to execute payment: {e}")

