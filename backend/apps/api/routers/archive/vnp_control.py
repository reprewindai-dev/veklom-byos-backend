import logging
from typing import List, Optional
import stripe

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.core.database.database import get_db
from backend.core.config.settings import settings
from backend.db.models.vnp import Customer, Provider

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/control",
    tags=["VNP Control Plane"],
    responses={404: {"description": "Not found"}},
)

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_mock")

# Pydantic models
class CustomerCreate(BaseModel):
    name: str
    billing_mode: str
    currency: str = "USD"
    email: Optional[str] = None

class ProviderCreate(BaseModel):
    legal_name: str
    slug: str
    support_email: Optional[str] = None
    billing_email: Optional[str] = None

@router.post("/customers")
async def create_customer(
    req: CustomerCreate = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new VNP Customer and provision a Stripe Customer automatically.
    """
    try:
        stripe_id = None
        if stripe.api_key != "sk_test_mock":
            # Provision Stripe Customer
            stripe_customer = stripe.Customer.create(
                name=req.name,
                email=req.email
            )
            stripe_id = stripe_customer.id

        new_customer = Customer(
            name=req.name,
            billing_mode=req.billing_mode,
            currency=req.currency,
            stripe_customer_id=stripe_id
        )
        db.add(new_customer)
        await db.commit()
        await db.refresh(new_customer)

        return {
            "customer_id": str(new_customer.id),
            "stripe_customer_id": stripe_id,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Failed to create customer: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Could not create customer.")

@router.post("/providers")
async def create_provider(
    req: ProviderCreate = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Onboard a new Provider to the VNP ecosystem.
    """
    # Check if slug exists
    stmt = select(Provider.id).where(Provider.slug == req.slug)
    res = await db.execute(stmt)
    if res.first():
        raise HTTPException(status_code=400, detail="Provider slug already exists.")

    try:
        new_provider = Provider(
            legal_name=req.legal_name,
            slug=req.slug,
            support_email=req.support_email,
            billing_email=req.billing_email
        )
        db.add(new_provider)
        await db.commit()
        await db.refresh(new_provider)

        return {
            "provider_id": str(new_provider.id),
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Failed to create provider: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Could not create provider.")
