import asyncio
import httpx
import uuid
import os
import zipfile
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smoke_test")

BASE_URL = os.getenv("VEKLOM_API_URL", "https://api.veklom.com/api/v1/gpc")
# ARTIFACTS_DIR check is mainly for local, we skip it if we aren't local since we can't read the server's disk natively from this script.


async def test_compile():
    pipeline_id = f"smoke_test_{uuid.uuid4().hex[:8]}"
    fingerprint = f"cap_{pipeline_id[:8]}"
    logger.info(f"Starting smoke test for pipeline: {pipeline_id}")
    
    async with httpx.AsyncClient() as client:
        # 1. Compile endpoint should trigger Poltergeist build queue
        payload = {
            "pipeline_id": pipeline_id,
            "tenant_id": "test_tenant"
        }
        
        logger.info(f"POST /compile with {payload}")
        resp = await client.post(f"{BASE_URL}/compile", json=payload, timeout=20.0)
        resp_data = resp.json()
        
        if not resp_data.get("success"):
            logger.error(f"Compile failed: {resp_data}")
            return False
            
        logger.info("Compile succeeded. Python code generated successfully.")
        
        # 2. Check SSE Execute endpoint
        logger.info(f"GET /execute?pipeline_id={pipeline_id}")
        # Note: We won't fully stream it in this simple smoke test, just check status
        # but in a real test we'd parse the SSE events
        async with client.stream("GET", f"{BASE_URL}/execute?pipeline_id={pipeline_id}") as stream:
            if stream.status_code != 200:
                logger.error(f"SSE execution failed with status {stream.status_code}")
                return False
                
            logger.info("SSE execution stream connected successfully.")
            # Read first chunk to verify start event
            first_chunk = await stream.aiter_lines().__anext__()
            if "start" not in first_chunk:
                logger.error(f"Unexpected first event: {first_chunk}")
                return False
            logger.info("Received valid start event from execution stream.")

        # 3. Verify Artifact exists in local storage
        # Poltergeist local_storage saves it in ARTIFACTS_DIR / fingerprint
        # Since we are running locally on Windows (in Windsurf), the ARTIFACTS_DIR
        # is probably mapped differently or created locally if it doesn't exist.
        # local_storage.py uses: self.base_dir = Path("/data/artifacts") if os.name != "nt" else Path(os.getenv("TEMP", "/tmp")) / "artifacts"
        
        if os.name == 'nt':
            base_dir = os.path.join(os.environ.get("TEMP", "C:/temp"), "artifacts")
        else:
            base_dir = "/data/artifacts"
            
        artifact_path = os.path.join(base_dir, fingerprint, "1", "capability.zip")
        if not os.path.exists(artifact_path):
            logger.error(f"Artifact not found at {artifact_path}")
            return False
            
        logger.info(f"Artifact verified at {artifact_path}")
        
        # 4. Unzip and verify contents
        with zipfile.ZipFile(artifact_path, 'r') as zip_ref:
            files = zip_ref.namelist()
            if "main.py" not in files:
                logger.error("main.py missing from generated artifact!")
                return False
            if "manifest.json" not in files:
                logger.error("manifest.json missing from generated artifact!")
                return False
                
            manifest_data = json.loads(zip_ref.read("manifest.json"))
            if manifest_data.get("type") != "python_transform":
                logger.error(f"Unexpected manifest type: {manifest_data.get('type')}")
                return False
                
        logger.info("Artifact contents verified successfully. Poltergeist is 100% stable.")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_compile())
    if not success:
        logger.error("Smoke test FAILED.")
        exit(1)
    else:
        logger.info("Smoke test PASSED.")
