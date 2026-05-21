import asyncio
import json
from datetime import datetime, timezone
from backend.core.database.redis_client import get_redis
from backend.apps.api.routers.runtime_jobs import get_job_status

async def main():
    redis = await get_redis()
    if not redis:
        print("Redis is not available.")
        return
        
    transaction_id = "test-tx-12345"
    
    # 1. Test UNKNOWN state
    print("Testing UNKNOWN state...")
    await redis.delete(f"job:{transaction_id}")
    res_unknown = await get_job_status(transaction_id, redis)
    print(f"UNKNOWN Response: {res_unknown.json()}")
    
    # 2. Set PROCESSING state in Redis
    print("\nSetting PROCESSING state...")
    processing_state = {
        "status": "PROCESSING",
        "detail": "Worker has accepted the payload",
        "destination_node": "hetzner-fsn1-gpu",
        "progress": 45,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await redis.set(f"job:{transaction_id}", json.dumps(processing_state), ex=60)
    
    res_processing = await get_job_status(transaction_id, redis)
    print(f"PROCESSING Response: {res_processing.json()}")
    
    # 3. Set COMPLETED state
    print("\nSetting COMPLETED state...")
    completed_state = {
        "status": "COMPLETED",
        "detail": "Pipeline executed successfully",
        "destination_node": "hetzner-fsn1-gpu",
        "progress": 100,
        "proof_hash": "a1b2c3d4e5f6...",
        "result_ref": "minio://artifacts/run_123.zip",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await redis.set(f"job:{transaction_id}", json.dumps(completed_state), ex=60)
    
    res_completed = await get_job_status(transaction_id, redis)
    print(f"COMPLETED Response: {res_completed.json()}")
    
    # Cleanup
    await redis.delete(f"job:{transaction_id}")

if __name__ == "__main__":
    asyncio.run(main())
