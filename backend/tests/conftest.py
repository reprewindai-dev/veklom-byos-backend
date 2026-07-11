from backend.core.database.database import Base, engine
from backend.db.models.billing import WalletTransaction
from backend.db.models.pgl import PGLCertificate, PGLIdentity, PGLLedgerEvent
from backend.db.models.user import User
from backend.db.models.workspace import Workspace

TEST_TABLES = (
    User.__table__,
    Workspace.__table__,
    PGLIdentity.__table__,
    PGLCertificate.__table__,
    PGLLedgerEvent.__table__,
    WalletTransaction.__table__,
)


async def init_test_db():
    """Create the tables required by onboarding integration tests."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn,
                tables=TEST_TABLES,
            )
        )
