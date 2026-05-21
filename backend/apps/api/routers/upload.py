"""Upload router for S3 / MinIO storage."""

import uuid
import boto3
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from botocore.exceptions import ClientError

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.asset import Asset
from backend.db.models.user import User


router = APIRouter(prefix="/upload", tags=["Upload"])

def get_s3_client():
    """Initialize boto3 client for S3/MinIO using settings."""
    if not settings.S3_ACCESS_KEY_ID or not settings.S3_SECRET_ACCESS_KEY or not settings.S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage is not configured."
        )

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL if settings.S3_ENDPOINT_URL else None,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to S3/MinIO and record it as an Asset."""
    s3_client = get_s3_client()
    
    file_id = str(uuid.uuid4())
    workspace_id = current_user.workspace_id or "default"
    s3_key = f"{workspace_id}/{file_id}/{file.filename}"
    
    file_content = await file.read()
    
    try:
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type,
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to S3: {str(e)}"
        )

    asset = Asset(
        id=file_id,
        workspace_id=workspace_id,
        filename=file.filename,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(file_content),
        s3_key=s3_key,
        s3_bucket=settings.S3_BUCKET_NAME,
    )
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return {
        "id": asset.id,
        "filename": asset.filename,
        "original_filename": asset.original_filename,
        "content_type": asset.content_type,
        "file_size": asset.file_size,
        "s3_key": asset.s3_key,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }
