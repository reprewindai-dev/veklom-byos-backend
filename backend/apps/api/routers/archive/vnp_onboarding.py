import logging
from typing import Optional
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database.database import get_db
from backend.db.models.vnp import Api, ApiRegion

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/vnp/onboard",
    tags=["VNP Onboarding"],
)

class VNPClaimRequest(BaseModel):
    provider_name: str
    api_name: str
    base_url: str
    healthcheck_path: str
    contact_email: str

@router.post("")
async def submit_api_claim(claim: VNPClaimRequest, db: AsyncSession = Depends(get_db)):
    """
    Accepts an API submission from a provider.
    Registers the API in the VNP ledger for edge-probing baselining.
    """
    
    # Check if this base URL is already registered
    stmt = select(Api).where(Api.endpoint_url == claim.base_url)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="This API base URL is already registered on the VNP network.")
        
    # Create the API record
    new_api = Api(
        id=f"api_{uuid.uuid4().hex[:12]}",
        provider_id=claim.provider_name.lower().replace(" ", "-"),
        name=claim.api_name,
        endpoint_url=claim.base_url,
        health_path=claim.healthcheck_path,
        pricing_model="metered",
        x402_ready=False,
        stability_rating="Evaluating",
        current_composite_score=50.0 # Starts at 50 until baseline is established
    )
    db.add(new_api)
    
    # We will automatically register it for global probing by adding an ApiRegion record
    # VNP requires evaluating from a "default" global stance initially
    new_region = ApiRegion(
        api_id=new_api.id,
        region_code="global",
        endpoint_url=claim.base_url,
        active=True
    )
    db.add(new_region)
    
    await db.commit()
    
    logger.info(f"[VNP] New API Claim Registered: {claim.provider_name} - {claim.api_name} at {claim.base_url}")
    
    return {
        "status": "success",
        "message": "API submitted for evaluation",
        "api_id": new_api.id
    }
