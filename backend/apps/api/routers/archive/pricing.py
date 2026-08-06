"""Pricing tier system routes."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
import stripe

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.config.settings import settings
from backend.db.models.pricing import PricingTier, TierFeature, TierUpgrade, UsageMetric, BillingEvent
from backend.db.models.billing import Subscription

router = APIRouter(tags=["Pricing"])


# Standard pricing tiers configuration
STANDARD_TIERS = {
    "starter": {
        "name": "starter",
        "display_name": "Starter",
        "description": "Perfect for individuals and small teams getting started with AI governance",
        "tier_level": 1,
        "monthly_price": 29.0,
        "annual_price": 290.0,
        "features": {
            "basic_authority_control": True,
            "max_agents": 5,
            "max_workspaces": 1,
            "basic_monitoring": True,
            "email_support": True,
            "api_access": True,
            "basic_audit_logs": True,
            "max_api_calls_per_month": 10000
        },
        "limits": {
            "agents": 5,
            "workspaces": 1,
            "api_calls_per_month": 10000,
            "storage_gb": 10,
            "team_members": 5
        }
    },
    "professional": {
        "name": "professional",
        "display_name": "Professional",
        "description": "Advanced features for growing teams and production workloads",
        "tier_level": 2,
        "monthly_price": 99.0,
        "annual_price": 990.0,
        "features": {
            "advanced_authority_control": True,
            "max_agents": 25,
            "max_workspaces": 5,
            "advanced_monitoring": True,
            "priority_support": True,
            "api_access": True,
            "advanced_audit_logs": True,
            "custom_policies": True,
            "max_api_calls_per_month": 100000,
            "sla_guarantee": True
        },
        "limits": {
            "agents": 25,
            "workspaces": 5,
            "api_calls_per_month": 100000,
            "storage_gb": 100,
            "team_members": 25
        }
    },
    "enterprise": {
        "name": "enterprise",
        "display_name": "Enterprise",
        "description": "Full-featured platform with enterprise-grade security and compliance",
        "tier_level": 3,
        "monthly_price": 499.0,
        "annual_price": 4990.0,
        "features": {
            "full_authority_control": True,
            "unlimited_agents": True,
            "unlimited_workspaces": True,
            "enterprise_monitoring": True,
            "dedicated_support": True,
            "api_access": True,
            "full_audit_logs": True,
            "custom_policies": True,
            "unlimited_api_calls": True,
            "sla_guarantee": True,
            "custom_integrations": True,
            "on_premise_deployment": True,
            "compliance_reports": True,
            "advanced_analytics": True
        },
        "limits": {
            "agents": -1,  # Unlimited
            "workspaces": -1,  # Unlimited
            "api_calls_per_month": -1,  # Unlimited
            "storage_gb": -1,  # Unlimited
            "team_members": -1  # Unlimited
        }
    }
}


def _get_stripe_client():
    """Get initialized Stripe client."""
    if not settings.STRIPE_SECRET_KEY.strip():
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
    return stripe


@router.get("/pricing/tiers")
async def get_pricing_tiers(
    include_inactive: bool = False,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available pricing tiers."""
    try:
        query = select(PricingTier)
        if not include_inactive:
            query = query.where(PricingTier.is_active == True, PricingTier.is_public == True)
        
        query = query.order_by(PricingTier.tier_level)
        result = await db.execute(query)
        tiers = result.scalars().all()
        
        # If no tiers in database, return standard tiers
        if not tiers:
            return {
                "tiers": [
                    {
                        "id": tier_data["name"],
                        "name": tier_data["display_name"],
                        "description": tier_data["description"],
                        "tier_level": tier_data["tier_level"],
                        "monthly_price": tier_data["monthly_price"],
                        "annual_price": tier_data["annual_price"],
                        "currency": "USD",
                        "features": tier_data["features"],
                        "limits": tier_data["limits"],
                        "is_active": True,
                        "is_public": True
                    }
                    for tier_data in STANDARD_TIERS.values()
                ],
                "total_count": len(STANDARD_TIERS)
            }
        
        return {
            "tiers": [
                {
                    "id": tier.id,
                    "name": tier.name,
                    "display_name": tier.display_name,
                    "description": tier.description,
                    "tier_level": tier.tier_level,
                    "monthly_price": tier.monthly_price,
                    "annual_price": tier.annual_price,
                    "currency": tier.currency,
                    "features": tier.features,
                    "limits": tier.limits,
                    "is_active": tier.is_active,
                    "is_public": tier.is_public
                }
                for tier in tiers
            ],
            "total_count": len(tiers)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get pricing tiers: {str(e)}")


@router.get("/pricing/tiers/{tier_id}")
async def get_pricing_tier(
    tier_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific pricing tier details."""
    try:
        # Check if it's a standard tier
        if tier_id in STANDARD_TIERS:
            tier_data = STANDARD_TIERS[tier_id]
            return {
                "id": tier_id,
                "name": tier_data["display_name"],
                "description": tier_data["description"],
                "tier_level": tier_data["tier_level"],
                "monthly_price": tier_data["monthly_price"],
                "annual_price": tier_data["annual_price"],
                "currency": "USD",
                "features": tier_data["features"],
                "limits": tier_data["limits"],
                "is_active": True,
                "is_public": True
            }
        
        # Check database tiers
        result = await db.execute(
            select(PricingTier).where(
                PricingTier.id == tier_id,
                PricingTier.is_active == True
            )
        )
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise HTTPException(status_code=404, detail="Pricing tier not found")
        
        return {
            "id": tier.id,
            "name": tier.name,
            "display_name": tier.display_name,
            "description": tier.description,
            "tier_level": tier.tier_level,
            "monthly_price": tier.monthly_price,
            "annual_price": tier.annual_price,
            "currency": tier.currency,
            "features": tier.features,
            "limits": tier.limits,
            "is_active": tier.is_active,
            "is_public": tier.is_public
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get pricing tier: {str(e)}")


@router.get("/pricing/current")
async def get_current_pricing(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current workspace pricing tier and usage."""
    try:
        # Get current subscription
        subscription_result = await db.execute(
            select(Subscription).where(
                Subscription.workspace_id == user.workspace_id,
                Subscription.status == "active"
            )
        )
        subscription = subscription_result.scalar_one_or_none()
        
        current_tier = None
        if subscription:
            # Get tier details
            if subscription.pricing_tier_id in STANDARD_TIERS:
                tier_data = STANDARD_TIERS[subscription.pricing_tier_id]
                current_tier = {
                    "id": subscription.pricing_tier_id,
                    "name": tier_data["display_name"],
                    "tier_level": tier_data["tier_level"],
                    "monthly_price": tier_data["monthly_price"],
                    "annual_price": tier_data["annual_price"],
                    "features": tier_data["features"],
                    "limits": tier_data["limits"]
                }
            else:
                tier_result = await db.execute(
                    select(PricingTier).where(PricingTier.id == subscription.pricing_tier_id)
                )
                tier = tier_result.scalar_one_or_none()
                if tier:
                    current_tier = {
                        "id": tier.id,
                        "name": tier.display_name,
                        "tier_level": tier.tier_level,
                        "monthly_price": tier.monthly_price,
                        "annual_price": tier.annual_price,
                        "features": tier.features,
                        "limits": tier.limits
                    }
        
        # Get current usage metrics
        usage_result = await db.execute(
            select(UsageMetric).where(
                UsageMetric.workspace_id == user.workspace_id,
                UsageMetric.period_start >= datetime.now(timezone.utc) - timedelta(days=30)
            ).order_by(desc(UsageMetric.created_at)).limit(100)
        )
        usage_metrics = usage_result.scalars().all()
        
        return {
            "current_tier": current_tier,
            "subscription": {
                "id": subscription.id if subscription else None,
                "status": subscription.status if subscription else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
                "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False
            },
            "usage": [
                {
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "metric_unit": metric.metric_unit,
                    "tier_limit": metric.tier_limit,
                    "usage_percentage": metric.usage_percentage,
                    "period_start": metric.period_start.isoformat(),
                    "period_end": metric.period_end.isoformat()
                }
                for metric in usage_metrics
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get current pricing: {str(e)}")


@router.post("/pricing/upgrade")
async def initiate_tier_upgrade(
    tier_id: str,
    billing_cycle: str = "monthly",  # monthly, annual
    upgrade_type: str = "immediate",  # immediate, at_billing_cycle
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate a pricing tier upgrade."""
    try:
        # Get target tier
        target_tier = None
        if tier_id in STANDARD_TIERS:
            tier_data = STANDARD_TIERS[tier_id]
            target_tier = {
                "id": tier_id,
                "name": tier_data["display_name"],
                "tier_level": tier_data["tier_level"],
                "monthly_price": tier_data["monthly_price"],
                "annual_price": tier_data["annual_price"]
            }
        else:
            tier_result = await db.execute(
                select(PricingTier).where(
                    PricingTier.id == tier_id,
                    PricingTier.is_active == True
                )
            )
            tier = tier_result.scalar_one_or_none()
            if not tier:
                raise HTTPException(status_code=404, detail="Pricing tier not found")
            target_tier = {
                "id": tier.id,
                "name": tier.display_name,
                "tier_level": tier.tier_level,
                "monthly_price": tier.monthly_price,
                "annual_price": tier.annual_price
            }
        
        # Get current subscription
        current_subscription = await db.execute(
            select(Subscription).where(
                Subscription.workspace_id == user.workspace_id,
                Subscription.status == "active"
            )
        )
        subscription = current_subscription.scalar_one_or_none()
        
        # Calculate price
        price = target_tier["monthly_price"] if billing_cycle == "monthly" else target_tier["annual_price"]
        
        # Create upgrade record
        upgrade = TierUpgrade(
            workspace_id=user.workspace_id,
            from_tier_id=subscription.pricing_tier_id if subscription else None,
            to_tier_id=target_tier["id"],
            status="pending",
            upgrade_type=upgrade_type,
            scheduled_at=datetime.now(timezone.utc) if upgrade_type == "immediate" else None,
            payment_method="stripe",
            prorated_amount=price,
            currency="USD"
        )
        
        db.add(upgrade)
        await db.commit()
        
        # Create Stripe checkout session
        stripe_client = _get_stripe_client()
        
        success_url, cancel_url = (
            f"{settings.FRONTEND_URL}/workspace#/billing?upgrade=success",
            f"{settings.FRONTEND_URL}/workspace#/billing?upgrade=cancelled"
        )
        
        session = stripe_client.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Veklom {target_tier['name']} Plan",
                        "description": f"Upgrade to {target_tier['name']} tier"
                    },
                    "unit_amount": int(price * 100),
                    "recurring": {
                        "interval": billing_cycle
                    } if billing_cycle in ["monthly", "annual"] else None
                },
                "quantity": 1,
            }],
            mode="subscription" if billing_cycle in ["monthly", "annual"] else "payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "workspace_id": user.workspace_id,
                "upgrade_id": upgrade.id,
                "tier_id": target_tier["id"]
            }
        )
        
        # Update upgrade with Stripe session ID
        upgrade.stripe_subscription_id = session.id
        await db.commit()
        
        return {
            "upgrade_id": upgrade.id,
            "checkout_url": session.url,
            "tier": target_tier,
            "billing_cycle": billing_cycle,
            "price": price,
            "currency": "USD"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to initiate upgrade: {str(e)}")


@router.get("/pricing/usage")
async def get_usage_metrics(
    metric_name: str = Query(None, description="Filter by metric name"),
    days: int = Query(30, description="Days of usage to retrieve"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage metrics for the workspace."""
    try:
        since_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(UsageMetric).where(
            UsageMetric.workspace_id == user.workspace_id,
            UsageMetric.period_start >= since_time
        )
        
        if metric_name:
            query = query.where(UsageMetric.metric_name == metric_name)
        
        query = query.order_by(desc(UsageMetric.created_at)).limit(1000)
        
        result = await db.execute(query)
        metrics = result.scalars().all()
        
        return {
            "metrics": [
                {
                    "id": metric.id,
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "metric_unit": metric.metric_unit,
                    "tier_limit": metric.tier_limit,
                    "usage_percentage": metric.usage_percentage,
                    "period_start": metric.period_start.isoformat(),
                    "period_end": metric.period_end.isoformat(),
                    "metadata": metric.metadata
                }
                for metric in metrics
            ],
            "total_count": len(metrics)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get usage metrics: {str(e)}")


@router.post("/pricing/usage/record")
async def record_usage_metric(
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Record a usage metric (typically called by internal services)."""
    try:
        metric = UsageMetric(
            workspace_id=user.workspace_id,
            metric_name=body.get("metric_name"),
            metric_value=float(body.get("metric_value", 0)),
            metric_unit=body.get("metric_unit", "count"),
            period_start=datetime.fromisoformat(body.get("period_start")) if body.get("period_start") else datetime.now(timezone.utc) - timedelta(days=1),
            period_end=datetime.fromisoformat(body.get("period_end")) if body.get("period_end") else datetime.now(timezone.utc),
            tier_limit=body.get("tier_limit"),
            usage_percentage=body.get("usage_percentage", 0.0),
            metadata=body.get("metadata", {})
        )
        
        db.add(metric)
        await db.commit()
        
        return {"recorded": True, "id": metric.id}
        
    except Exception as e:
        await db.rollback()
        return {"recorded": False, "error": str(e)}


@router.get("/pricing/billing-events")
async def get_billing_events(
    event_type: str = Query(None, description="Filter by event type"),
    days: int = Query(30, description="Days of events to retrieve"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing events for the workspace."""
    try:
        since_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(BillingEvent).where(
            BillingEvent.workspace_id == user.workspace_id,
            BillingEvent.created_at >= since_time
        )
        
        if event_type:
            query = query.where(BillingEvent.event_type == event_type)
        
        query = query.order_by(desc(BillingEvent.created_at)).limit(100)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        return {
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "event_data": event.event_data,
                    "amount": event.amount,
                    "currency": event.currency,
                    "status": event.status,
                    "processed_at": event.processed_at.isoformat() if event.processed_at else None,
                    "created_at": event.created_at.isoformat(),
                    "metadata": event.metadata
                }
                for event in events
            ],
            "total_count": len(events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get billing events: {str(e)}")
