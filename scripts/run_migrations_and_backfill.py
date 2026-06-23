import asyncio
import os
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def run_backfill():
    if not DATABASE_URL or "sqlite" in DATABASE_URL:
        print("Skipping backfill on SQLite. This script requires a PostgreSQL database.")
        return

    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("Reading migration SQL...")
        with open("migrations/versions/003_settlement_ledger.sql", "r") as f:
            migration_sql = f.read()
        
        print("Applying migration...")
        await conn.execute(text(migration_sql))
        print("Migration applied successfully.")
        
        print("Checking for legacy records in vnp_settlement_entries...")
        try:
            result = await conn.execute(text("SELECT * FROM vnp_settlement_entries"))
            legacy_entries = result.fetchall()
            
            if not legacy_entries:
                print("No legacy settlement entries found. Backfill complete.")
                return
                
            print(f"Found {len(legacy_entries)} legacy entries. Starting backfill...")
            
            for entry in legacy_entries:
                # Map old state to new state enum
                old_state = entry.state
                new_state = 'locked'
                if old_state in ('settled', 'posted', 'released'):
                    new_state = 'released'
                elif old_state in ('failed', 'error', 'rejected'):
                    new_state = 'rejected'
                
                # Derive amounts
                amount = entry.amount_minor or 0
                
                # Dedupe key logic
                dedupe_key = entry.reference_code or f"legacy_{entry.id}"
                
                # Map IDs (using nil UUID if missing)
                nil_uuid = '00000000-0000-0000-0000-000000000000'
                tenant_id = entry.customer_id or nil_uuid
                payer_id = entry.customer_id or nil_uuid
                payee_id = entry.provider_id or nil_uuid
                
                execution_hash = str(entry.usage_event_id) if entry.usage_event_id else f"legacy_{entry.id}"
                
                # Insert into new table
                insert_sql = text("""
                    INSERT INTO settlement_ledger (
                        id, tenant_id, workspace_id, payer_id, payee_id,
                        protected_route, service_name, currency_code,
                        quoted_amount_minor, locked_amount_minor, released_amount_minor,
                        execution_hash, settlement_state, dedupe_key,
                        metadata_json, created_at, updated_at
                    ) VALUES (
                        :id, :tenant_id, :workspace_id, :payer_id, :payee_id,
                        :route, :service_name, :currency,
                        :quoted_amount, :locked_amount, :released_amount,
                        :execution_hash, :state, :dedupe_key,
                        :metadata, :created_at, :created_at
                    ) ON CONFLICT (execution_hash) DO NOTHING
                """)
                
                await conn.execute(insert_sql, {
                    "id": entry.id,
                    "tenant_id": tenant_id,
                    "workspace_id": tenant_id,
                    "payer_id": payer_id,
                    "payee_id": payee_id,
                    "route": "/legacy/vnp",
                    "service_name": "legacy_vnp",
                    "currency": entry.currency or "USDC",
                    "quoted_amount": amount,
                    "locked_amount": amount,
                    "released_amount": amount if new_state == 'released' else 0,
                    "execution_hash": execution_hash,
                    "state": new_state,
                    "dedupe_key": dedupe_key,
                    "metadata": json.dumps({"legacy_entry_type": str(entry.entry_type)}),
                    "created_at": entry.created_at
                })
                
            print("Backfill completed successfully.")
            
        except Exception as e:
            print(f"Error during backfill (table might not exist yet): {e}")

if __name__ == "__main__":
    asyncio.run(run_backfill())
