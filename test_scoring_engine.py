import asyncio
from backend.apps.api.services.vnp_scoring_engine import VNPScoringEngine

async def test_engine():
    print("Starting VNP Scoring Engine Test...")
    try:
        # Manually trigger one computation
        # Note: This requires a working DB and Redis
        await VNPScoringEngine.compute_and_cache_snapshots()
        print("✓ Scoring computation completed successfully (or skipped if no data).")
    except Exception as e:
        print(f"✗ Scoring computation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_engine())
