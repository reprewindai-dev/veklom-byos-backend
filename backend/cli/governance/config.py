from pydantic import BaseModel, Field


class GovernanceCliConfig(BaseModel):
    db_url: str | None = None
    redis_url: str | None = None
    base_url: str = Field(default="http://localhost:8088")
    dashboard_url: str = Field(default="http://localhost:3000")
    tenant_id: str | None = None
    model_family: str = "default"
    output_format: str = "table"
    fail_fast: bool = False
    verbose: bool = False
