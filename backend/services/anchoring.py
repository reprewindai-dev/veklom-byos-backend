import hashlib
import logging
from typing import List
from datetime import datetime, timezone
import json

from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

# Base Mainnet RPC
BASE_RPC_URL = "https://mainnet.base.org"

def hash_payload(data: dict) -> str:
    """Creates a deterministic SHA-256 hash of a JSON payload."""
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def create_merkle_root(hashes: List[str]) -> str:
    """
    Computes a Merkle root from a list of SHA-256 hex hashes.
    """
    if not hashes:
        return "0x0000000000000000000000000000000000000000000000000000000000000000"
    
    current_level = hashes
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            h1 = current_level[i]
            h2 = current_level[i+1] if i+1 < len(current_level) else current_level[i]
            # Concatenate and hash the pair
            combined = h1 + h2
            next_level.append(hashlib.sha256(combined.encode('utf-8')).hexdigest())
        current_level = next_level
        
    return "0x" + current_level[0]

def anchor_merkle_root_to_base(merkle_root: str, window_start: datetime, window_end: datetime) -> str:
    """
    Anchors the Merkle root to the VNP Registry Smart Contract on Base L2.
    Returns the transaction hash.
    """
    rpc_url = settings.FLASHBLOCKS_RPC_URL or BASE_RPC_URL
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    if not w3.is_connected():
        logger.error(f"Failed to connect to Base RPC at {rpc_url}")
        return ""
        
    private_key = settings.VEKLOM_TREASURY_PRIVATE_KEY
    if not private_key:
        logger.warning("No treasury private key provided for L2 anchoring. Simulating success.")
        return "0x0000000000000000000000000000000000000000000000000000000000000000"
        
    account = w3.eth.account.from_key(private_key)
    
    # Contract setup (Standard Data Availability Anchor ABI)
    contract_address = settings.VNP_L2_REGISTRY_ADDRESS
    if not contract_address:
        logger.warning("No L2 Registry address. Simulating success.")
        return "0x0000000000000000000000000000000000000000000000000000000000000000"
        
    abi = [{
        "inputs": [
            {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"internalType": "uint256", "name": "windowStart", "type": "uint256"},
            {"internalType": "uint256", "name": "windowEnd", "type": "uint256"}
        ],
        "name": "anchorTelemetry",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }]
    
    contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=abi)
    
    try:
        # Convert hex string to bytes32 format
        merkle_bytes = Web3.to_bytes(hexstr=merkle_root)
        
        tx = contract.functions.anchorTelemetry(
            merkle_bytes,
            int(window_start.timestamp()),
            int(window_end.timestamp())
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'maxFeePerGas': w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': w3.to_wei(1, 'gwei')
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logger.info(f"Anchored VNP telemetry to Base L2: {tx_hash.hex()}")
        return tx_hash.hex()
        
    except Exception as e:
        logger.error(f"Error anchoring to Base L2: {str(e)}")
        return ""
