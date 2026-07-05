import uuid
import secrets
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr

from backend.core.database.database import get_db_session
from backend.db.models.vnp import ClaimRequest, ClaimedAPI
import aiodns
import os
import smtplib
from email.message import EmailMessage

router = APIRouter(prefix="/claims", tags=["vnp-claims"])

# ============================================================================
# Pydantic Schemas
# ============================================================================

class ClaimCreateRequest(BaseModel):
    api_domain: str
    company_name: str
    company_email: EmailStr

class ClaimCreateResponse(BaseModel):
    claim_id: str
    api_id: str
    dns_record: str
    dns_value: str
    instructions: str
    expires_at: datetime

class ClaimStatusResponse(BaseModel):
    status: str
    claim_id: Optional[str] = None
    api_id: Optional[str] = None
    api_domain: Optional[str] = None
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    dashboard_url: Optional[str] = None
    claimed_api: Optional[Dict[str, Any]] = None

# ============================================================================
# Core Logic
# ============================================================================

def send_verification_email(to_email: str, api_domain: str):
    """Sends a verification success email via Resend SMTP (or any standard SMTP)."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print(f"[MAIL MOCK] Sent verification email to {to_email} for {api_domain} (Set RESEND_API_KEY to send real emails)")
        return
        
    msg = EmailMessage()
    msg.set_content(f"Congratulations!\\n\\nYour domain {api_domain} has been successfully verified on the Veklom Nexus Protocol.\\nYou can now access your provider dashboard and govern your endpoints.")
    msg["Subject"] = "VNP Provider Ownership Verified"
    msg["From"] = "VNP Admin <admin@veklom.com>"
    msg["To"] = to_email
    
    try:
        with smtplib.SMTP("smtp.resend.com", 587) as server:
            server.starttls()
            server.login("resend", api_key)
            server.send_message(msg)
        print(f"Successfully sent verification email via Resend SMTP to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

async def verify_dns_txt_record(dns_record: str, expected_value: str) -> bool:
    """Uses aiodns to query the TXT record and verify it contains the expected value."""
    resolver = aiodns.DNSResolver()
    try:
        result = await resolver.query(dns_record, 'TXT')
        for txt_record in result:
            # aiodns returns TXT records as an object with a .text property which is a list of strings
            combined = "".join([t.decode('utf-8') if isinstance(t, bytes) else t for t in txt_record.text])
            if expected_value in combined:
                return True
        return False
    except aiodns.error.DNSError:
        return False

async def background_dns_polling(claim_id: uuid.UUID):
    """
    Polls DNS for a pending claim up to a certain number of attempts.
    This simulates the polling worker in the original architecture.
    """
    max_attempts = 360 # 1 hour at 10s intervals
    
    for attempt in range(max_attempts):
        async with get_db_session() as db:
            request = await db.get(ClaimRequest, claim_id)
            if not request or request.status != 'pending':
                return
            
            if datetime.now(timezone.utc) > request.expires_at:
                request.status = 'failed'
                await db.commit()
                return

            verified = await verify_dns_txt_record(request.dns_record, request.dns_value)
            
            if verified:
                request.status = 'verified'
                request.verified_at = datetime.now(timezone.utc)
                
                # Check if ClaimedAPI already exists
                existing = await db.execute(select(ClaimedAPI).where(ClaimedAPI.api_id == request.api_id))
                claimed_api = existing.scalars().first()
                
                if not claimed_api:
                    claimed_api = ClaimedAPI(
                        api_id=request.api_id,
                        company_name=request.company_name,
                        company_email=request.company_email,
                        score_low_alert=True,
                        score_low_threshold=80
                    )
                    db.add(claimed_api)
                
                await db.commit()
                send_verification_email(request.company_email, request.api_domain)
                return
                
        await asyncio.sleep(10)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("", response_model=ClaimCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(request: ClaimCreateRequest, background_tasks: BackgroundTasks):
    """Generate a DNS TXT challenge to claim an API."""
    
    # Normalize domain
    normalized_domain = request.api_domain.lower().replace('http://', '').replace('https://', '').strip('/')
    api_id = f"did:vnp:api:{normalized_domain.replace('.', '-')}"
    
    dns_value = secrets.token_hex(16)
    
    async with get_db_session() as db:
        claim_request = ClaimRequest(
            api_id=api_id,
            api_domain=normalized_domain,
            company_name=request.company_name,
            company_email=request.company_email,
            dns_record=f"_vnp-claim.{uuid.uuid4().hex[:8]}.{normalized_domain}",
            dns_value=dns_value,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        # Update dns_record to use actual ID
        db.add(claim_request)
        await db.commit()
        await db.refresh(claim_request)
        
        # Patch the record name to include actual UUID for consistency with the TS version
        claim_request.dns_record = f"_vnp-claim.{claim_request.id.hex}.{normalized_domain}"
        await db.commit()
        await db.refresh(claim_request)
        
        # Start background polling
        background_tasks.add_task(background_dns_polling, claim_request.id)
        
        return ClaimCreateResponse(
            claim_id=str(claim_request.id),
            api_id=claim_request.api_id,
            dns_record=claim_request.dns_record,
            dns_value=claim_request.dns_value,
            instructions=f"Add this TXT record to your DNS provider:\\n\\nName: {claim_request.dns_record}\\nValue: {claim_request.dns_value}\\n\\nThen we'll automatically verify.",
            expires_at=claim_request.expires_at
        )

@router.get("/{claim_id}/status", response_model=ClaimStatusResponse)
async def check_claim_status(claim_id: uuid.UUID):
    """Check the verification status of a claim request."""
    async with get_db_session() as db:
        request = await db.get(ClaimRequest, claim_id)
        if not request:
            raise HTTPException(status_code=404, detail="Claim request not found")
            
        if request.status == 'verified':
            existing = await db.execute(select(ClaimedAPI).where(ClaimedAPI.api_id == request.api_id))
            claimed_api = existing.scalars().first()
            
            return ClaimStatusResponse(
                status='verified',
                api_id=request.api_id,
                verified_at=request.verified_at,
                dashboard_url=f"https://vnp.io/provider/{request.api_id}",
                claimed_api={
                    "company_name": claimed_api.company_name if claimed_api else request.company_name,
                    "alerts_enabled": claimed_api.score_low_alert if claimed_api else True
                }
            )
            
        return ClaimStatusResponse(
            status=request.status,
            claim_id=str(request.id),
            api_domain=request.api_domain,
            expires_at=request.expires_at
        )

@router.post("/{claim_id}/verify")
async def trigger_manual_verification(claim_id: uuid.UUID):
    """Manually trigger verification (e.g. user clicks 'Verify Now' in UI)."""
    async with get_db_session() as db:
        request = await db.get(ClaimRequest, claim_id)
        if not request:
            raise HTTPException(status_code=404, detail="Claim request not found")
            
        if request.status == 'verified':
            return {"status": "verified", "message": "Claim is already verified."}
            
        verified = await verify_dns_txt_record(request.dns_record, request.dns_value)
        
        if verified:
            request.status = 'verified'
            request.verified_at = datetime.now(timezone.utc)
            
            # Check if ClaimedAPI already exists
            existing = await db.execute(select(ClaimedAPI).where(ClaimedAPI.api_id == request.api_id))
            claimed_api = existing.scalars().first()
            
            if not claimed_api:
                claimed_api = ClaimedAPI(
                    api_id=request.api_id,
                    company_name=request.company_name,
                    company_email=request.company_email,
                    score_low_alert=True,
                    score_low_threshold=80
                )
                db.add(claimed_api)
            
            await db.commit()
            send_verification_email(request.company_email, request.api_domain)
            
            return {"status": "verified", "message": "Claim verified successfully."}
            
        return {
            "status": "pending",
            "message": "DNS record not yet detected. Please ensure TXT record is added and DNS has propagated."
        }
