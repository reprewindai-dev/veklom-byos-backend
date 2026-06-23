import os
import json
from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
    poa_middleware = geth_poa_middleware
except ImportError:
    from web3.middleware import ExtraDataToPOAMiddleware
    poa_middleware = ExtraDataToPOAMiddleware


# Public Base Sepolia RPC (in production this should be an Alchemy/Infura URL from env)
BASE_SEPOLIA_RPC_URL = os.getenv("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org")

# The orchestrator wallet private key
ORCHESTRATOR_PRIVATE_KEY = os.getenv("ORCHESTRATOR_PRIVATE_KEY")

# Hardcoded addresses for MVP testnet (these would be populated after deployment)
STAKING_CONTRACT_ADDRESS = os.getenv("STAKING_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")

# Minimal ABI for the slashing function
STAKING_ABI = json.loads("""
[
    {
        "inputs": [
            {"internalType": "string", "name": "providerId", "type": "string"},
            {"internalType": "uint256", "name": "penaltyAmount", "type": "uint256"}
        ],
        "name": "slashBond",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "providerId", "type": "string"}],
        "name": "getBond",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]
""")

class Web3Orchestrator:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC_URL))
        # Inject POA middleware for Base L2
        self.w3.middleware_onion.inject(poa_middleware, layer=0)
        
        self.staking_contract = self.w3.eth.contract(address=STAKING_CONTRACT_ADDRESS, abi=STAKING_ABI)
        
        if ORCHESTRATOR_PRIVATE_KEY:
            self.account = self.w3.eth.account.from_key(ORCHESTRATOR_PRIVATE_KEY)
        else:
            self.account = None

    def is_connected(self) -> bool:
        return self.w3.is_connected()

    def get_provider_bond(self, provider_id: str) -> float:
        """Fetch real on-chain bond balance. Returns the value scaled from 6 decimals."""
        if not self.is_connected() or STAKING_CONTRACT_ADDRESS == "0x0000000000000000000000000000000000000000":
            return 0.0 # Return 0 if not fully configured yet
        try:
            # Assuming 6 decimals for vUSDC
            raw_balance = self.staking_contract.functions.getBond(provider_id).call()
            return float(raw_balance) / 1e6
        except Exception as e:
            print(f"[web3] Error fetching bond for {provider_id}: {e}")
            return 0.0

    def slash_bond(self, provider_id: str, penalty_usdc: float) -> str:
        """Submits a real on-chain transaction to slash a provider's bond."""
        if not self.account:
            print("[web3] Skipping slash: No orchestrator private key configured.")
            return ""
        
        if STAKING_CONTRACT_ADDRESS == "0x0000000000000000000000000000000000000000":
            print("[web3] Skipping slash: No staking contract configured.")
            return ""

        try:
            # Convert float USDC back to 6 decimal integer
            penalty_raw = int(penalty_usdc * 1e6)
            
            # Build the transaction
            tx = self.staking_contract.functions.slashBond(provider_id, penalty_raw).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign the transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)
            
            # Send the transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            hex_hash = tx_hash.hex()
            print(f"[web3] Successfully submitted slashing tx for {provider_id}: {hex_hash}")
            return hex_hash
            
        except Exception as e:
            print(f"[web3] Failed to submit slashing tx for {provider_id}: {e}")
            return ""

# Singleton instance
web3_client = Web3Orchestrator()
