import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Union, BinaryIO
from fastapi import UploadFile

from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

class MinIOService:
    """
    S3-compatible storage service for MinIO, AWS S3, or Cloudflare R2.
    Configured via settings.py (S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, etc.)
    """
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME or settings.S3_BUCKET or "veklom-storage"
        self.endpoint_url = settings.S3_ENDPOINT_URL or settings.MINIO_ENDPOINT
        self.region_name = settings.S3_REGION or "us-east-1"
        
        # Initialize boto3 client
        client_args = {
            "service_name": "s3",
            "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
            "region_name": self.region_name
        }
        
        if self.endpoint_url:
            client_args["endpoint_url"] = self.endpoint_url
            
        self.s3_client = boto3.client(**client_args)
        
        # Ensure bucket exists if possible
        try:
            self._ensure_bucket_exists()
        except Exception as e:
            logger.warning(f"Failed to ensure bucket exists, might lack permissions or disk space: {e}")

    def _ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                # Create the bucket
                if self.region_name == "us-east-1":
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region_name}
                    )
            else:
                raise

    def upload_file(self, file_obj: Union[BinaryIO, bytes], object_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Uploads a file to the S3 compatible bucket.
        """
        try:
            if isinstance(file_obj, bytes):
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_obj,
                    ContentType=content_type
                )
            else:
                self.s3_client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    object_name,
                    ExtraArgs={'ContentType': content_type}
                )
            return object_name
        except ClientError as e:
            logger.error(f"S3 Upload failed: {e}")
            raise

    def get_presigned_url(self, object_name: str, expiration=3600) -> Optional[str]:
        """
        Generates a presigned URL to securely share an S3 object.
        """
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"S3 Presigned URL generation failed: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """
        Deletes an object from the S3 bucket.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            logger.error(f"S3 Delete failed: {e}")
            return False

# Singleton instance
minio_service = MinIOService()
