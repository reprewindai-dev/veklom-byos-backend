import asyncio
from sqlalchemy import text
from backend.core.database.database import engine

async def migrate():
    async with engine.begin() as conn:
        # Alter users.pgl_id to VARCHAR(36)
        try:
            await conn.execute(text("ALTER TABLE users ALTER COLUMN pgl_id TYPE VARCHAR(36);"))
            print("Successfully altered users.pgl_id")
        except Exception as e:
            print(f"Skipping users.pgl_id alter (may already be applied or missing): {e}")
            
        # Create pgl_identities table
        try:
            await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pgl_identities (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(64) NOT NULL,
                primary_public_key TEXT NOT NULL,
                key_type VARCHAR(32) NOT NULL DEFAULT 'ed25519',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                rotated_at TIMESTAMP WITH TIME ZONE,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pgl_identities_tenant_id ON pgl_identities (tenant_id);"))
            print("Successfully created pgl_identities table")
        except Exception as e:
            print(f"Error creating pgl_identities: {e}")

        # Create agent_identities table
        try:
            await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_identities (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(64) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_by_pgl_id VARCHAR(36) NOT NULL,
                description TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSON DEFAULT '{}'::json
            );
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_identities_tenant_id ON agent_identities (tenant_id);"))
            print("Successfully created agent_identities table")
        except Exception as e:
            print(f"Error creating agent_identities: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
