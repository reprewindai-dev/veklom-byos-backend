"""Initialize database schema for production deployment."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from backend.db.models.user import Base as UserBase
from backend.db.models.workspace import Base as WorkspaceBase
from backend.db.models.workspace import WorkspaceMember, ModelConfig
from backend.db.models.user import Session, APIKey


async def init_database():
    """Create all database tables."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from backend.db.models.user import User
        from backend.db.models.workspace import Workspace
        
        # Create all tables
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(WorkspaceBase.metadata.create_all)
        
    await engine.dispose()
    print("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())
