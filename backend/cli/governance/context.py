from dataclasses import dataclass
from sqlalchemy import create_engine
import redis
import httpx

from backend.cli.governance.config import GovernanceCliConfig


@dataclass
class GovernanceCliContext:
    config: GovernanceCliConfig
    db_engine: object | None
    redis_client: object | None
    http: httpx.Client


def build_context(config: GovernanceCliConfig) -> GovernanceCliContext:
    db_engine = create_engine(config.db_url) if config.db_url else None
    redis_client = redis.from_url(config.redis_url) if config.redis_url else None
    http = httpx.Client(base_url=config.base_url, timeout=20.0)
    return GovernanceCliContext(config=config, db_engine=db_engine, redis_client=redis_client, http=http)
