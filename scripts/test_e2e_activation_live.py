import asyncio
import os
import json
import uuid
import httpx
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from backend.core.security.auth import get_password_hash

BYOS_URL = 'http://localhost:8088'
CAPPO_URL = 'http://cappo-backend-node:8002'
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://veklom:veklom_password@postgres:5432/veklom")

async def setup_db_state():
    print(f'Setting up DB state... URL={DB_URL}')
    engine = create_async_engine(DB_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    workspace_id = f'ws_{uuid.uuid4().hex[:12]}'
    user_id = f'usr_{uuid.uuid4().hex[:12]}'
    vlink_id = f'vlk_{uuid.uuid4().hex[:12]}'
    api_key_id = f'key_{uuid.uuid4().hex[:12]}'
    raw_key = f'byos_{uuid.uuid4().hex[:20]}'
    key_prefix = raw_key[:10]
    key_hash = get_password_hash(raw_key)

    async with session_maker() as db:
        await db.execute(text(\"\"\"
            INSERT INTO users (id, email, hashed_password, is_active, workspace_id, created_at, updated_at)
            VALUES (:id, :email, 'hash', true, :workspace_id, :now, :now)
        \"\"\"), {'id': user_id, 'email': f'{user_id}@test.com', 'workspace_id': workspace_id, 'now': datetime.utcnow()})
        
        await db.execute(text(\"\"\"
            INSERT INTO api_keys (id, key_prefix, key_hash, name, workspace_id, scopes, created_at, expires_at)
            VALUES (:id, :prefix, :hash, 'Test VLink Key', :workspace_id, '[\"vlink:assertion\"]', :now, NULL)
        \"\"\"), {'id': api_key_id, 'prefix': key_prefix, 'hash': key_hash, 'workspace_id': workspace_id, 'now': datetime.utcnow()})
        
        await db.execute(text(\"\"\"
            INSERT INTO vlink_bindings (id, vlink_id, api_key_id, workspace_id, connection_ref, is_active, created_at)
            VALUES (:id, :vlink_id, :api_key_id, :workspace_id, :conn_ref, true, :now)
        \"\"\"), {
            'id': f'vlb_{uuid.uuid4().hex[:12]}',
            'vlink_id': vlink_id,
            'api_key_id': api_key_id,
            'workspace_id': workspace_id,
            'conn_ref': f'conn_{uuid.uuid4().hex[:12]}',
            'now': datetime.utcnow()
        })
        
        await db.commit()

    await engine.dispose()
    print('DB state setup complete.')
    return raw_key, vlink_id

async def run_e2e():
    raw_key, vlink_id = await setup_db_state()
    
    async with httpx.AsyncClient() as client:
        print(f'\n1. Requesting CAPPO assertion from BYOS for VLink {vlink_id}...')
        resp = await client.post(
            f'{BYOS_URL}/api/v1/auth/vlink-assertion',
            headers={'X-API-Key': raw_key},
            json={'vlink_id': vlink_id}
        )
        print('BYOS Response:', resp.status_code, resp.text)
        assert resp.status_code == 200, 'Failed to get assertion'
        assertion = resp.json()['access_token']
        
        print('\n2. Requesting CAPPO mount...')
        resp = await client.post(
            f'{CAPPO_URL}/api/v1/capability/mount',
            headers={'Authorization': f'Bearer {assertion}'},
            json={
                'target_ref': 'activation.local-record',
                'requested_actions': ['record.create', 'record.read', 'record.delete']
            }
        )
        print('CAPPO Mount Response:', resp.status_code, resp.text)
        assert resp.status_code == 200, 'Failed to mount CAPPO'
        mount_id = resp.json()['mount_id']
        
        print('\n3. Executing allowed consequence (record.create)...')
        resp = await client.post(
            f'{CAPPO_URL}/api/v1/capability/execute/{mount_id}',
            headers={'Authorization': f'Bearer {assertion}'},
            json={
                'action': 'record.create',
                'payload': {'data': 'test_creation'}
            }
        )
        print('CAPPO Execute Create Response:', resp.status_code, resp.text)
        assert resp.status_code == 200, 'Failed to execute allowed consequence'
        
        print('\n4. Executing forbidden consequence (record.delete)...')
        resp = await client.post(
            f'{CAPPO_URL}/api/v1/capability/execute/{mount_id}',
            headers={'Authorization': f'Bearer {assertion}'},
            json={
                'action': 'record.delete',
                'payload': {'id': '123'}
            }
        )
        print('CAPPO Execute Delete Response:', resp.status_code, resp.text)
        assert resp.status_code == 403, 'Forbidden consequence was not denied!'
        
        print('\n5. Testing replay (execute create again)...')
        resp = await client.post(
            f'{CAPPO_URL}/api/v1/capability/execute/{mount_id}',
            headers={'Authorization': f'Bearer {assertion}'},
            json={
                'action': 'record.create',
                'payload': {'data': 'test_creation'}
            }
        )
        print('CAPPO Execute Replay Response:', resp.status_code, resp.text)
        assert resp.status_code in [400, 403, 404, 410], 'Replay should be denied (mount terminated)'
        
        print('\n✅ E2E INTEGRATION PASSED SUCCESSFULLY!')

if __name__ == '__main__':
    asyncio.run(run_e2e())
