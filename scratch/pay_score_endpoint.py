
import os
import sys
import httpx
from web3 import Web3
from eth_account import Account

# Constants
RPC_URL = "https://sepolia.base.org"
BASE_URL = "http://localhost:8088"
TREASURY_WALLET = "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970"
COST_USD = 0.01  # /score premium identity cost

# Validate private key
pk = os.environ.get("MY_WALLET_PRIVATE_KEY")
if not pk:
    print("[!] ERROR: No private key found. Please set MY_WALLET_PRIVATE_KEY in your environment.")
    print("    Command: $env:MY_WALLET_PRIVATE_KEY=\"your_private_key\"")
    print("    Then run this script again.")
    sys.exit(1)

account = Account.from_key(pk)
print(f"[*] Using Sender Wallet: {account.address}")
print(f"[*] Treasury Wallet: {TREASURY_WALLET}")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    print("[!] Could not connect to Base Sepolia RPC")
    sys.exit(1)

balance_wei = w3.eth.get_balance(account.address)
balance_eth = w3.from_wei(balance_wei, "ether")
print(f"[*] Wallet Balance: {balance_eth} Base Sepolia ETH")

if balance_wei == 0:
    print("[!] Wallet has 0 ETH for gas. Cannot proceed.")
    sys.exit(1)

print("\n[*] 1) Executing payment transaction for /score...")
tx = {
    "nonce": w3.eth.get_transaction_count(account.address),
    "to": TREASURY_WALLET,
    "value": w3.to_wei(0.0001, "ether"), # Approximate ETH equivalent
    "gas": 21000,
    "gasPrice": w3.eth.gas_price,
    "chainId": 84532
}

signed_tx = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
print(f"  [+] Transaction broadcasted! Hash: {tx_hash.hex()}")
print("  [+] Waiting for receipt...")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print(f"  [+] Transaction confirmed in block {receipt.blockNumber}")

print("\n[*] 2) Verifying payment with Veklom API at /api/v1/x402/score...")
resp = httpx.post(
    f"{BASE_URL}/api/v1/x402/score",
    headers={"X-Payment-Proof": tx_hash.hex()}
)

if resp.status_code == 200:
    print("  [OK] Payment Accepted! 200 OK.")
    print(resp.json())
else:
    print(f"  [FAIL] Payment rejected. Status {resp.status_code}")
    print(resp.text)

