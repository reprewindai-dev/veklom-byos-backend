import os
import aiofiles
import logging
from typing import Optional

logger = logging.getLogger("local_storage")

class LocalArtifactStorage:
    """
    Stores Poltergeist generated capabilities locally on the NVMe volume.
    Replaces R2 for 100% free, zero-setup storage aligned with the BYOS stack.
    """
    def __init__(self, base_dir: str = "/app/data/artifacts"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        
    async def upload_artifact(self, fingerprint: str, revision: int, data: bytes, filename: str) -> Optional[str]:
        """
        Saves the compiled capability artifact to local disk.
        Returns the absolute local path to the artifact.
        """
        artifact_dir = os.path.join(self.base_dir, fingerprint, str(revision))
        os.makedirs(artifact_dir, exist_ok=True)
        
        file_path = os.path.join(artifact_dir, filename)
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(data)
            logger.info(f"Artifact saved to {file_path}")
            return f"local://{file_path}"
        except Exception as e:
            logger.error(f"Failed to save artifact {filename} locally: {e}")
            return None
            
local_storage = LocalArtifactStorage()
