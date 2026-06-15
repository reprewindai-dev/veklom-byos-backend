"""Referral system routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import uuid

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.referral import ReferralCode, Referral, ReferralPayout
from backend.db.models.user import User

router = APIRouter(tags=["Referrals"])


# --- Referral Code Management ---
@router.post("/referrals/codes")
async def create_referral_code(
    reward_type: str = "percentage",
    reward_value: float = 10.0,
    max_uses: int = 100,
    expires_days: int = 365,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new referral code for the user."""
    try:
        # Check if user already has an active referral code
        existing_code = await db.execute(
            select(ReferralCode).where(
                ReferralCode.user_id == user.id,
                ReferralCode.status == "active"
            )
        )
        if existing_code.scalar_one_or_none():
            return {
                "status": "error",
                "error": "User already has an active referral code"
            }
        
        # Generate unique referral code
        code = f"VEK{user.id[:8].upper()}{uuid.uuid4().hex[:6].upper()}"
        
        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timezone.timedelta(days=expires_days) if expires_days > 0 else None
        
        # Create referral code
        referral_code = ReferralCode(
            user_id=user.id,
            code=code,
            reward_type=reward_type,
            reward_value=reward_value,
            max_uses=max_uses,
            expires_at=expires_at
        )
        
        db.add(referral_code)
        await db.commit()
        
        return {
            "status": "success",
            "referral_code": {
                "id": referral_code.id,
                "code": code,
                "reward_type": reward_type,
                "reward_value": reward_value,
                "max_uses": max_uses,
                "current_uses": 0,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "share_url": f"https://veklom.com/signup?ref={code}",
                "created_at": referral_code.created_at.isoformat()
            }
        }
        
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": f"Failed to create referral code: {str(e)}"}


@router.get("/referrals/codes")
async def get_user_referral_codes(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get user's referral codes."""
    try:
        result = await db.execute(
            select(ReferralCode).where(ReferralCode.user_id == user.id)
        )
        codes = result.scalars().all()
        
        referral_codes = []
        for code in codes:
            referral_codes.append({
                "id": code.id,
                "code": code.code,
                "status": code.status,
                "reward_type": code.reward_type,
                "reward_value": code.reward_value,
                "max_uses": code.max_uses,
                "current_uses": code.current_uses,
                "remaining_uses": code.max_uses - code.current_uses,
                "expires_at": code.expires_at.isoformat() if code.expires_at else None,
                "share_url": f"https://veklom.com/signup?ref={code.code}",
                "created_at": code.created_at.isoformat()
            })
        
        return {
            "status": "success",
            "referral_codes": referral_codes
        }
        
    except Exception as e:
        return {"status": "error", "error": f"Failed to get referral codes: {str(e)}"}


@router.post("/referrals/apply")
async def apply_referral_code(
    code: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply a referral code during signup."""
    try:
        # Find valid referral code
        referral_code_result = await db.execute(
            select(ReferralCode).where(
                ReferralCode.code == code.upper(),
                ReferralCode.status == "active"
            )
        )
        referral_code = referral_code_result.scalar_one_or_none()
        
        if not referral_code:
            return {"status": "error", "error": "Invalid or expired referral code"}
        
        # Check if code has expired
        if referral_code.expires_at and referral_code.expires_at < datetime.now(timezone.utc):
            return {"status": "error", "error": "Referral code has expired"}
        
        # Check if code has reached max uses
        if referral_code.current_uses >= referral_code.max_uses:
            return {"status": "error", "error": "Referral code has reached maximum uses"}
        
        # Check if user already used a referral code
        existing_referral = await db.execute(
            select(Referral).where(Referral.referred_id == user.id)
        )
        if existing_referral.scalar_one_or_none():
            return {"status": "error", "error": "User has already used a referral code"}
        
        # Check if user is trying to refer themselves
        if referral_code.user_id == user.id:
            return {"status": "error", "error": "Cannot use your own referral code"}
        
        # Create referral record
        referral = Referral(
            referral_code_id=referral_code.id,
            referrer_id=referral_code.user_id,
            referred_id=user.id,
            status="pending",
            conversion_event="signup"
        )
        
        # Update referral code usage
        referral_code.current_uses += 1
        
        db.add(referral)
        await db.commit()
        
        return {
            "status": "success",
            "referral": {
                "id": referral.id,
                "referrer_id": referral_code.user_id,
                "reward_type": referral_code.reward_type,
                "reward_value": referral_code.reward_value,
                "status": "pending",
                "message": f"Referral code applied! You'll receive {referral_code.reward_value}{referral_code.reward_type} reward on your first purchase."
            }
        }
        
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": f"Failed to apply referral code: {str(e)}"}


# --- Referral Tracking ---
@router.get("/referrals")
async def get_user_referrals(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's referral history (both sent and received)."""
    try:
        # Get referrals where user is referrer
        referrer_result = await db.execute(
            select(Referral, ReferralCode.code, User.email).select_from(
                Referral.__table__.join(
                    ReferralCode, Referral.referral_code_id == ReferralCode.id
                ).join(
                    User, Referral.referred_id == User.id
                )
            ).where(
                Referral.referrer_id == user.id
            ).order_by(
                desc(Referral.created_at)
            ).offset(offset).limit(limit)
        )
        
        # Get referral where user is referred
        referred_result = await db.execute(
            select(Referral, ReferralCode.code, User.email).select_from(
                Referral.__table__.join(
                    ReferralCode, Referral.referral_code_id == ReferralCode.id
                ).join(
                    User, Referral.referrer_id == User.id
                )
            ).where(
                Referral.referred_id == user.id
            ).order_by(
                desc(Referral.created_at)
            )
        )
        
        sent_referrals = []
        for referral, code, referred_email in referrer_result:
            sent_referrals.append({
                "id": referral.id,
                "referred_email": referred_email,
                "code": code,
                "status": referral.status,
                "reward_amount": referral.reward_amount,
                "reward_paid": referral.reward_paid,
                "conversion_event": referral.conversion_event,
                "completed_at": referral.completed_at.isoformat() if referral.completed_at else None,
                "created_at": referral.created_at.isoformat()
            })
        
        received_referrals = []
        for referral, code, referrer_email in referred_result:
            received_referrals.append({
                "id": referral.id,
                "referrer_email": referrer_email,
                "code": code,
                "status": referral.status,
                "reward_amount": referral.reward_amount,
                "reward_paid": referral.reward_paid,
                "conversion_event": referral.conversion_event,
                "completed_at": referral.completed_at.isoformat() if referral.completed_at else None,
                "created_at": referral.created_at.isoformat()
            })
        
        return {
            "status": "success",
            "sent_referrals": sent_referrals,
            "received_referrals": received_referrals,
            "total_sent": len(sent_referrals),
            "total_received": len(received_referrals)
        }
        
    except Exception as e:
        return {"status": "error", "error": f"Failed to get referrals: {str(e)}"}


@router.post("/referrals/{referral_id}/complete")
async def complete_referral(
    referral_id: str,
    conversion_event: str = "first_purchase",
    purchase_amount: float = 0.0,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete a referral and calculate rewards."""
    try:
        # Find referral
        referral_result = await db.execute(
            select(Referral).where(Referral.id == referral_id)
        )
        referral = referral_result.scalar_one_or_none()
        
        if not referral:
            return {"status": "error", "error": "Referral not found"}
        
        if referral.status != "pending":
            return {"status": "error", "error": f"Referral already {referral.status}"}
        
        # Get referral code to calculate reward
        code_result = await db.execute(
            select(ReferralCode).where(ReferralCode.id == referral.referral_code_id)
        )
        referral_code = code_result.scalar_one_or_none()
        
        if not referral_code:
            return {"status": "error", "error": "Referral code not found"}
        
        # Calculate reward amount
        reward_amount = 0.0
        if referral_code.reward_type == "percentage":
            reward_amount = purchase_amount * (referral_code.reward_value / 100)
        elif referral_code.reward_type == "fixed":
            reward_amount = referral_code.reward_value
        elif referral_code.reward_type == "credits":
            reward_amount = referral_code.reward_value
        
        # Update referral
        referral.status = "completed"
        referral.reward_amount = reward_amount
        referral.conversion_event = conversion_event
        referral.completed_at = datetime.now(timezone.utc)
        
        # Create payout record
        payout = ReferralPayout(
            referral_id=referral.id,
            user_id=referral.referrer_id,
            amount=reward_amount,
            currency="USD",
            status="pending"
        )
        
        db.add(payout)
        await db.commit()
        
        return {
            "status": "success",
            "referral": {
                "id": referral.id,
                "status": "completed",
                "reward_amount": reward_amount,
                "conversion_event": conversion_event,
                "completed_at": referral.completed_at.isoformat()
            },
            "payout": {
                "id": payout.id,
                "amount": reward_amount,
                "currency": "USD",
                "status": "pending"
            }
        }
        
    except Exception as e:
        await db.rollback()
        return {"status": "error", "error": f"Failed to complete referral: {str(e)}"}


# --- Referral Analytics ---
@router.get("/referrals/analytics")
async def get_referral_analytics(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get referral analytics for the user."""
    try:
        # Get user's referral code
        code_result = await db.execute(
            select(ReferralCode).where(
                ReferralCode.user_id == user.id,
                ReferralCode.status == "active"
            )
        )
        referral_code = code_result.scalar_one_or_none()
        
        if not referral_code:
            return {
                "status": "success",
                "analytics": {
                    "has_referral_code": False,
                    "total_referrals": 0,
                    "completed_referrals": 0,
                    "pending_referrals": 0,
                    "total_earned": 0.0,
                    "pending_earnings": 0.0
                }
            }
        
        # Get referral statistics
        total_referrals_result = await db.execute(
            select(func.count(Referral.id)).where(Referral.referral_code_id == referral_code.id)
        )
        total_referrals = total_referrals_result.scalar() or 0
        
        completed_referrals_result = await db.execute(
            select(func.count(Referral.id)).where(
                Referral.referral_code_id == referral_code.id,
                Referral.status == "completed"
            )
        )
        completed_referrals = completed_referrals_result.scalar() or 0
        
        pending_referrals_result = await db.execute(
            select(func.count(Referral.id)).where(
                Referral.referral_code_id == referral_code.id,
                Referral.status == "pending"
            )
        )
        pending_referrals = pending_referrals_result.scalar() or 0
        
        # Calculate earnings
        total_earned_result = await db.execute(
            select(func.coalesce(func.sum(Referral.reward_amount), 0)).where(
                Referral.referral_code_id == referral_code.id,
                Referral.status == "completed"
            )
        )
        total_earned = float(total_earned_result.scalar() or 0.0)
        
        pending_earnings_result = await db.execute(
            select(func.coalesce(func.sum(ReferralPayout.amount), 0)).where(
                ReferralPayout.user_id == user.id,
                ReferralPayout.status == "pending"
            )
        )
        pending_earnings = float(pending_earnings_result.scalar() or 0.0)
        
        return {
            "status": "success",
            "analytics": {
                "has_referral_code": True,
                "referral_code": referral_code.code,
                "total_referrals": total_referrals,
                "completed_referrals": completed_referrals,
                "pending_referrals": pending_referrals,
                "total_earned": round(total_earned, 2),
                "pending_earnings": round(pending_earnings, 2),
                "conversion_rate": round((completed_referrals / total_referrals * 100) if total_referrals > 0 else 0, 2),
                "share_url": f"https://veklom.com/signup?ref={referral_code.code}"
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": f"Failed to get analytics: {str(e)}"}


# --- Referral Payouts ---
@router.get("/referrals/payouts")
async def get_referral_payouts(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's referral payout history."""
    try:
        query = select(ReferralPayout, Referral.conversion_event).select_from(
            ReferralPayout.__table__.join(Referral, ReferralPayout.referral_id == Referral.id)
        ).where(ReferralPayout.user_id == user.id)
        
        if status:
            query = query.where(ReferralPayout.status == status)
        
        query = query.order_by(desc(ReferralPayout.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        payouts = []
        
        for payout, conversion_event in result:
            payouts.append({
                "id": payout.id,
                "referral_id": payout.referral_id,
                "amount": payout.amount,
                "currency": payout.currency,
                "status": payout.status,
                "payment_method": payout.payment_method,
                "reference_id": payout.reference_id,
                "conversion_event": conversion_event,
                "processed_at": payout.processed_at.isoformat() if payout.processed_at else None,
                "created_at": payout.created_at.isoformat()
            })
        
        return {
            "status": "success",
            "payouts": payouts,
            "total_count": len(payouts)
        }
        
    except Exception as e:
        return {"status": "error", "error": f"Failed to get payouts: {str(e)}"}
