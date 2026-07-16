"""
VNP Treasury Worker
-------------------
Evaluates RegionalTelemetry to detect SLA breaches.
If an SLA breach is detected, it slashes the provider's prepaid balance
and issues refunds to affected customers automatically.
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_
from backend.core.database.database import async_session
from backend.db.models.vnp import (
    RegionalTelemetry, Api, Provider, Incident, IncidentState, 
    SettlementEntry, LedgerEntryType, SettlementState, UsageEvent
)

logger = logging.getLogger("VNPTreasuryWorker")

SLA_UPTIME_THRESHOLD = 99.5
SLASH_AMOUNT_MINOR = 5000  # $50.00 penalty per incident

async def run_treasury_cycle():
    logger.info("Starting VNP Treasury SLA Evaluation Cycle...")
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    async with async_session() as db:
        # 1. Find telemetry that breached SLA in the last hour
        stmt = select(RegionalTelemetry).where(
            and_(
                RegionalTelemetry.measured_at >= one_hour_ago,
                RegionalTelemetry.uptime_percent < SLA_UPTIME_THRESHOLD
            )
        )
        breached_telemetry = (await db.execute(stmt)).scalars().all()

        if not breached_telemetry:
            logger.info("No SLA breaches detected. Treasury cycle complete.")
            return

        # Deduplicate breaches by API ID
        breached_apis = {}
        for tel in breached_telemetry:
            if tel.api_id not in breached_apis:
                breached_apis[tel.api_id] = tel

        api_ids = list(breached_apis.keys())

        # Bulk Fetch APIs
        apis_stmt = select(Api).where(Api.id.in_(api_ids))
        apis_list = (await db.execute(apis_stmt)).scalars().all()
        apis_by_id = {api.id: api for api in apis_list}

        # Bulk Fetch existing incidents
        incs_stmt = select(Incident.scope_id).where(
            and_(
                Incident.scope_id.in_(api_ids),
                Incident.state.in_([IncidentState.open, IncidentState.acknowledged])
            )
        )
        existing_inc_scopes = set((await db.execute(incs_stmt)).scalars().all())

        for api_id, telemetry in breached_apis.items():
            # Use pre-fetched API
            api = apis_by_id.get(api_id)
            if not api:
                continue

            # Check if there's already an open incident for this API from pre-fetched set
            if api_id in existing_inc_scopes:
                logger.info(f"Open incident already exists for API {api_id}. Skipping slash.")
                continue

            logger.warning(f"SLA Breach detected for API {api_id} (Uptime: {telemetry.uptime_percent}%). Executing Slashing...")

            # 2. Create Incident
            incident_id = uuid.uuid4()
            incident = Incident(
                id=incident_id,
                scope_type="api",
                scope_id=api_id,
                title=f"SLA Breach: {api.name} uptime fell to {telemetry.uptime_percent}%",
                severity="high",
                state=IncidentState.open,
                opened_at=now
            )
            db.add(incident)

            # 3. Slash Provider
            slash_entry = SettlementEntry(
                provider_id=api.provider_id,
                entry_type=LedgerEntryType.slash,
                amount_minor=-SLASH_AMOUNT_MINOR,
                currency="USD",
                state=SettlementState.pending,
                reference_code=f"slash-{incident_id}",
                entry_metadata={"reason": "SLA Breach", "uptime": float(telemetry.uptime_percent)}
            )
            db.add(slash_entry)

            # 4. Refund Affected Customers
            usage_stmt = select(UsageEvent).where(
                and_(
                    UsageEvent.api_id == api_id,
                    UsageEvent.occurred_at >= one_hour_ago,
                    UsageEvent.success == False
                )
            )
            failed_usages = (await db.execute(usage_stmt)).scalars().all()

            refund_count = 0
            for usage in failed_usages:
                if usage.billable_units > 0:
                    # Issue 100% refund for the failed usage
                    refund_entry = SettlementEntry(
                        customer_id=usage.customer_id,
                        provider_id=api.provider_id,
                        usage_event_id=usage.id,
                        entry_type=LedgerEntryType.refund,
                        amount_minor=100, # Assume $1.00 refund per failed token batch for simplicity
                        currency="USD",
                        state=SettlementState.posted,
                        reference_code=f"refund-{usage.id}",
                        entry_metadata={"incident_id": str(incident_id)}
                    )
                    db.add(refund_entry)
                    refund_count += 1

            logger.info(f"Provider Slashed: {SLASH_AMOUNT_MINOR} minor units. Customers Refunded: {refund_count} events.")

        await db.commit()
        logger.info("VNP Treasury SLA Evaluation Cycle Complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_treasury_cycle())
