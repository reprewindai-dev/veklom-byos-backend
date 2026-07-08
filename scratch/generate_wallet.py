"""
Veklom Banker Agent — Wallet Generator
---------------------------------------
Runs LOCALLY only. Never send output to chat, logs, or CI.
Outputs a fresh EVM wallet address + private key for Base Mainnet.

Requires: pip install eth-account
"""

from eth_account import Account
import secrets

def generate_wallet():
    # Generate cryptographically secure entropy
    private_key_bytes = secrets.token_bytes(32)
    private_key_hex = "0x" + private_key_bytes.hex()

    account = Account.from_key(private_key_hex)

    print("\n" + "=" * 60)
    print("  VEKLOM BANKER AGENT WALLET")
    print("=" * 60)
    print(f"\n  Public Address  : {account.address}")
    print(f"  Private Key     : {private_key_hex}")
    print("\n" + "=" * 60)
    print("  INSTRUCTIONS:")
    print("  1. Copy the Public Address")
    print("  2. Send a small amount of USDC + ETH (for gas) to it")
    print("     on Base Mainnet only.")
    print("  3. In Coolify, set these env vars:")
    print("     VEKLOM_AGENT_ADDRESS  = <Public Address above>")
    print("     VEKLOM_AGENT_PRIVATE_KEY = <Private Key above>")
    print("     BANKER_AGENT_ENABLED  = true")
    print("  4. NEVER share the Private Key in chat, logs, or git.")
    print("  5. DELETE this terminal output when done.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    generate_wallet()
