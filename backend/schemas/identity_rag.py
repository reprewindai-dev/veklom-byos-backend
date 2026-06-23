from datetime import datetime
from pydantic import BaseModel, Field


class IdentityRAGResolveRequest(BaseModel):
    agent_id: str | None = None
    public_key: str | None = None
    requester_provider_id: str = Field(..., description="Provider paying for the resolution request")

    def model_post_init(self, __context):
        if not self.agent_id and not self.public_key:
            raise ValueError("agent_id or public_key is required")


class GoldenRecordFinancials(BaseModel):
    total_x402_volume_minor: int
    released_volume_minor: int
    rejected_settlement_count: int
    bounce_rate: float


class GoldenRecordGovernance(BaseModel):
    total_authority_runs: int
    denied_runs: int
    quarantine_count: int
    kleros_dispute_count: int


class GoldenRecordIdentity(BaseModel):
    pgl_identity_id: str
    public_key: str | None
    lineage_depth: int
    certificate_count: int
    created_at: datetime | None


class GoldenRecordResponse(BaseModel):
    pgl_identity: GoldenRecordIdentity
    financials: GoldenRecordFinancials
    governance: GoldenRecordGovernance
    trust_summary: dict
    source_counts: dict
    generated_at: datetime
    resolution_fee_minor: int
    charged_to_provider_id: str
