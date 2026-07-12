"""Cloudflare R2 storage service for Poltergeist artifacts."""

import os
import aioboto3
from typing import Optional, Tuple
from loguru import logger

class R2StorageService:
    def __init__(self):
        self.account_id = os.environ.get("CF_ACCOUNT_ID")
        self.access_key = os.environ.get("CF_R2_ACCESS_KEY")
        self.secret_key = os.environ.get("CF_R2_SECRET_KEY")
        self.bucket_name = os.environ.get("CF_R2_BUCKET", "veklom-capabilities")
        
        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com" if self.account_id else None

        self.enabled = bool(self.account_id and self.access_key and self.secret_key)
        
    def _get_session(self):
        return aioboto3.Session()

    async def upload_artifact(self, fingerprint: str, revision: int, file_content: bytes, filename: str) -> Optional[str]:
        """Uploads an artifact and returns its pointer."""
        if not self.enabled:
            logger.warning("R2StorageService is not configured. Skipping artifact upload.")
            return f"local://{fingerprint}/v{revision}/{filename}"
            
        object_key = f"artifacts/{fingerprint}/v{revision}/{filename}"
        
        try:
            session = self._get_session()
            async with session.client('s3', 
                                     endpoint_url=self.endpoint_url, 
                                     aws_access_key_id=self.access_key, 
                                     aws_secret_access_key=self.secret_key,
                                     region_name="auto") as s3:
                
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=file_content
                )
                
            return f"r2://{self.bucket_name}/{object_key}"
        except Exception as e:
            logger.error(f"Failed to upload artifact to R2: {str(e)}")
            return None

    async def download_artifact(self, pointer: str) -> Optional[bytes]:
        """Downloads an artifact by its pointer."""
        if not self.enabled or not pointer.startswith(f"r2://{self.bucket_name}/"):
            return None
            
        object_key = pointer.replace(f"r2://{self.bucket_name}/", "")
        
        try:
            session = self._get_session()
            async with session.client('s3', 
                                     endpoint_url=self.endpoint_url, 
                                     aws_access_key_id=self.access_key, 
                                     aws_secret_access_key=self.secret_key,
                                     region_name="auto") as s3:
                
                response = await s3.get_object(Bucket=self.bucket_name, Key=object_key)
                return await response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to download artifact from R2: {str(e)}")
            return None

r2_storage = R2StorageService()
