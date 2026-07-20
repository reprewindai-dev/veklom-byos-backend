import pytest
from datetime import datetime, timezone
from backend.services.anchoring import anchor_merkle_root_to_base
from backend.core.config.settings import settings
from web3 import Web3

def test_anchoring_failure_missing_key():
    """Test that missing Treasury key fails closed instead of returning a simulated zero hash."""
    original_key = settings.VEKLOM_TREASURY_PRIVATE_KEY
    settings.VEKLOM_TREASURY_PRIVATE_KEY = ""
    try:
        merkle = "0x" + "1" * 64
        now = datetime.now(timezone.utc)
        result = anchor_merkle_root_to_base(merkle, now, now)
        assert result is None, "Expected failure when missing config, but got a result."
    finally:
        settings.VEKLOM_TREASURY_PRIVATE_KEY = original_key

def test_live_base_smoke():
    """Smoke test to verify RPC connectivity and correct chain ID."""
    if not settings.VEKLOM_TREASURY_PRIVATE_KEY:
        pytest.skip("Skipping live Base smoke test: VEKLOM_TREASURY_PRIVATE_KEY not set")
        
    rpc_url = settings.FLASHBLOCKS_RPC_URL or "https://mainnet.base.org"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    assert w3.is_connected(), "Web3 must be connected to Base"
    
    chain_id = w3.eth.chain_id
    assert chain_id == 8453, f"Expected Base mainnet (8453), got {chain_id}"
