import asyncio
from sqlalchemy import text
from backend.core.database.database import engine, Base

import backend.db.models.user
import backend.db.models.workspace
import backend.db.models.ai
import backend.db.models.agent
import backend.db.models.marketplace
import backend.db.models.billing
import backend.db.models.security
import backend.db.models.ledger
import backend.db.models.decision_frame

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
        tables = [row[0] for row in result]
        iron = {'CarbonIntensity','Organization','CarbonCommand','DashboardRoutingDecision','CarbonCommandTrace','CarbonCommandOutcome','Operator','DoctrineProposal','DoctrineVersion','WorkloadRequest','OrgUsageCounter','WorkloadEmbeddingIndex','CarbonCommandAccuracyDaily','AdaptiveRunLog','AdaptiveProfile','AdaptiveSignal','CarbonForecast','ForecastRefresh','CarbonCredit','EmissionLog','DoctrineAuditEvent','DekesWorkload','DekesLeadCandidate','Region','RegionMetricRollup','DailyMetrics','IntegrationMetric','IntegrationEvent','DecisionTraceEnvelope','IntegrationWebhookSink','WorkloadDecisionOutcome','GridSignalSnapshot','Eia930BalanceRaw','Eia930InterchangeRaw','Eia930SubregionRaw','DekesProspect','DekesTenant','DekesDemo','DekesHandoffEvent','CarbonLedgerEntry','RoutingCandidate','ProviderSnapshot','WaterProviderSnapshot','FacilityWaterTelemetry','WaterScenarioRun','WaterPolicyEvidence','CapacityBucket','RoutingDecision','DecisionEventOutbox','CIDecision'}
        vek = [t for t in tables if t not in iron]
        print("Veklom tables:", vek)
        print(f"Total: {len(vek)} Veklom tables created")

asyncio.run(main())
