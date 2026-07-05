import os
import redis
import json
import time
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("veklom.audit_anchor")

def anchor_audit_head():
    """
    Periodically fetches the latest Merkle audit head from Redis
    and anchors it (in a real system, this might write to AWS QLDB, an S3 immutable bucket,
    or a public blockchain).
    """
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        r = redis.Redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return

    head_key = "veklom:audit:head_hash"
    
    while True:
        try:
            current_head = r.get(head_key)
            if current_head:
                # Simulate cryptographic external anchoring (e.g., signing the head)
                # In production, this pushes to a tamper-proof external store.
                signature = hashlib.sha256(f"ANCHOR_SECRET_{current_head}".encode()).hexdigest()
                
                anchor_record = {
                    "timestamp": time.time(),
                    "head_hash": current_head,
                    "anchor_signature": signature
                }
                
                # Store the anchor locally for verification
                r.set(f"veklom:audit:anchor:{current_head}", json.dumps(anchor_record))
                logger.info(f"Anchored audit head: {current_head[:8]}... Sig: {signature[:8]}...")
            else:
                logger.info("No audit head found to anchor.")
                
        except Exception as e:
            logger.error(f"Error anchoring head: {e}")
            
        # Anchor every 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    logger.info("Starting Veklom Periodic Audit Anchoring Service...")
    anchor_audit_head()
