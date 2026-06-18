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
    
    url = f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/{s3_key}" if settings.S3_ENDPOINT_URL else f"/files/{s3_key}"
    
    return {
        "asset_id": asset.id,
        "filename": asset.filename,
        "size_bytes": asset.file_size,
        "url": url
    }


import httpx
import json
from datetime import datetime, timezone

async def call_ollama_completion(prompt: str, system: str = None) -> str:
    # Try local Ollama docker host and fallback to localhost
    hosts = ["http://veklom-ollama:11434/api/generate", "http://localhost:11434/api/generate"]
    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "stream": False
    }
    if system:
        payload["system"] = system
        
    for host in hosts:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(host, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
        except Exception:
            continue
    return ""


@router.post("/transcribe")
async def transcribe_audio(body: dict, user=Depends(get_current_user)):
    from backend.core.tasks import transcribe_audio_task
    asset_id = body.get("asset_id", "test_asset_123")
    provider = body.get("provider", "local_whisper")
    
    task = transcribe_audio_task.delay(asset_id, provider)
    
    return {
        "job_id": task.id,
        "status": "queued",
        "message": "Transcription task dispatched to background worker."
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, user=Depends(get_current_user)):
    from celery.result import AsyncResult
    from backend.core.celery_app import celery_app
    
    result = AsyncResult(job_id, app=celery_app)
    
    return {
        "id": job_id,
        "status": result.state.lower() if result.state else "unknown",
        "result": result.result if result.ready() else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat() if result.ready() else None
    }


@router.post("/parse")
async def parse_content(body: dict, user=Depends(get_current_user)):
    from backend.core.tasks import parse_content_task
    content = body.get("content", "")
    parser = body.get("parser", "standard")
    
    task = parse_content_task.delay(content, parser)
    
    return {
        "job_id": task.id,
        "status": "queued",
        "parser": parser,
        "message": "Parse task dispatched to background worker."
    }


@router.post("/extract")
async def extract_structured_data(body: dict, user=Depends(get_current_user)):
    from backend.core.tasks import extract_data_task
    content = body.get("content", "")
    schema = body.get("extraction_schema", {})
    extractor = body.get("extractor", "standard")
    
    task = extract_data_task.delay(content, schema, extractor)
    
    return {
        "job_id": task.id,
        "status": "queued",
        "extractor": extractor,
        "message": "Extraction task dispatched to background worker."
    }


@router.post("/classify")
async def classify_content(body: dict, user=Depends(get_current_user)):
    from backend.core.tasks import classify_content_task
    content = body.get("content", "")
    categories = body.get("categories", ["invoices", "receipts", "contracts", "general"])
    classifier = body.get("classifier", "standard")
    
    task = classify_content_task.delay(content, categories, classifier)
    
    return {
        "job_id": task.id,
        "status": "queued",
        "classifier": classifier,
        "message": "Classification task dispatched to background worker."
    }
