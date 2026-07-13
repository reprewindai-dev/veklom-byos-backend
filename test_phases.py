import asyncio
import os
import sys

# Add backend to path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
from backend.core.replay.ingestion import replay_ingestion, CloudEvent
from backend.core.repogate.attestation import repogate_attestor
from backend.core.middleware.x402 import _price_usdc_string, _price_micro_usdc
from backend.apps.api.routers.gpc import post_bootstrap, BootstrapRequest
from decimal import Decimal

async def run_tests():
    print("--- Testing Phase 6 (Replay & RepoGate) ---")
    
    # Test 1: Replay Ingestion SHA-256
    event = CloudEvent(
        id="test-id",
        source="urn:test",
        type="test.event",
        data={"key": "value"}
    )
    packet_id = replay_ingestion.emit(event)
    print(f"Replay Ingestion Packet ID: {packet_id}")
    assert len(packet_id) == 64, "Packet ID should be a 64-char SHA-256 hash"
    
    # Test 2: RepoGate DSSE Attestation
    envelope = repogate_attestor.create_attestation(
        repository="veklom", commit_sha="abcdef123", branch="main", builder_id="coolify"
    )
    print(f"DSSE Envelope Payload: {envelope.payload}")
    verify_res = repogate_attestor.verify_attestation(envelope, required_slsa_level=2)
    print(f"Verify Level 2 (coolify): {verify_res}")
    assert verify_res["valid"] is True
    
    envelope_invalid = repogate_attestor.create_attestation(
        repository="veklom", commit_sha="abcdef123", branch="main", builder_id="other"
    )
    verify_res_invalid = repogate_attestor.verify_attestation(envelope_invalid, required_slsa_level=2)
    print(f"Verify Level 2 (other builder): {verify_res_invalid}")
    assert verify_res_invalid["valid"] is False

    print("\n--- Testing Phase 7 (Bootstrap & x402) ---")
    
    # Test 3: x402 Float Eradication
    route_cfg = {"price_usdc": 0.025, "name": "Pipeline Trigger"}
    price_str = _price_usdc_string(route_cfg)
    price_micro = _price_micro_usdc(route_cfg)
    print(f"x402 Price USDC string (0.025): {price_str}")
    print(f"x402 Price Micro USDC (0.025): {price_micro}")
    assert price_str == "0.0250" or price_str == "0.025"
    assert price_micro == 25000

    # Test 4: Bootstrap dry-run vs atomic vs quorum
    # Dry run should pass
    req = BootstrapRequest(dry_run=True, atomic=False, quorum=100)
    res = await post_bootstrap(req, user=None)
    print(f"Bootstrap Dry Run: {res}")
    assert res["success"] is True

    # Quorum failure (50% < 95%)
    req2 = BootstrapRequest(dry_run=False, atomic=False, quorum=95, nodes=["a","b"])
    res2 = await post_bootstrap(req2, user=None)
    print(f"Bootstrap Quorum Failure (50% < 95%): {res2}")
    assert res2["success"] is False

    print("\nAll local tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
