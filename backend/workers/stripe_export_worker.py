import asyncio
import logging
import time
from datetime import datetime, timezone
import stripe

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database.database import async_session
from backend.core.config.settings import settings
from backend.db.models.vnp import UsageEvent, SettlementEntry, LedgerEntryType

logger = logging.getLogger(__name__)

# Initialize Stripe with the API Key
# For VNP, Stripe Billing relies heavily on the Meter APIs.
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_mock")

async def run_stripe_export_cycle():
    """
    Periodically export aggregated usage events to Stripe Billing Meters.
    """
    logger.info("Starting VNP Stripe Export Worker...")
    
    while True:
        try:
            async with async_session() as db:
                # 1. Fetch un-exported usage events
                # In production, we'd add an `exported_to_stripe` boolean or track the cursor
                # For this MVP, we query events that don't have a corresponding settlement entry
                stmt = (
                    select(UsageEvent)
                    .outerjoin(SettlementEntry, SettlementEntry.usage_event_id == UsageEvent.id)
                    .where(SettlementEntry.id == None)
                    .where(UsageEvent.success == True)
                )
                res = await db.execute(stmt)
                unbilled_events = res.scalars().all()

                if not unbilled_events:
                    await asyncio.sleep(60)
                    continue
                
                logger.info(f"Found {len(unbilled_events)} unbilled VNP usage events.")

                # 2. Group by Customer and Meter (Unit Type)
                # Stripe Meters accept meter events per customer
                for event in unbilled_events:
                    try:
                        # Ensure customer has a stripe ID
                        # In production we'd join Customer table. For now assume stripe_customer_id is accessible
                        # We map unit_type directly to a Stripe Meter ID (e.g. mtr_tokens_used)
                        # The payload must have an idempotency key (identifier)
                        
                        idem_key = f"vnp_export_{event.event_id}"
                        
                        # Note: In a real environment, you use stripe.billing.MeterEvent.create
                        # Since we might not have meters set up in test mode, we just wrap in try/except
                        if stripe.api_key != "sk_test_mock":
                            # Use sync wrapper in an executor, or stripe async if available
                            # stripe.billing.MeterEvent.create is synchronous in older SDKs
                            # but stripe>12 supports some async, or we just block briefly
                            stripe.billing.MeterEvent.create(
                                event_name=event.unit_type,
                                payload={
                                    "value": event.billable_units,
                                    "stripe_customer_id": str(event.customer_id), # Ideally map this to actual stripe cus_
                                },
                                timestamp=int(event.occurred_at.timestamp()),
                                identifier=idem_key
                            )
                        
                        # 3. Create Internal Ledger Entry to mark as processed
                        settlement = SettlementEntry(
                            customer_id=event.customer_id,
                            provider_id=event.provider_id,
                            usage_event_id=event.id,
                            entry_type=LedgerEntryType.debit,
                            amount_minor=event.final_amount_minor or 0,
                            currency=event.currency,
                            reference_code=idem_key
                        )
                        db.add(settlement)

                    except Exception as e:
                        logger.error(f"Failed to export event {event.id} to Stripe: {e}")
                        # Don't add settlement, it will retry next cycle
                        continue

                await db.commit()

        except Exception as e:
            logger.error(f"Stripe Export cycle failed: {e}")
            
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_stripe_export_cycle())
