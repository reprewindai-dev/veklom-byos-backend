#!/bin/bash
docker exec n13gp1nhrcdp0hvazvbnlxru-213557155694 python3 -c "
import backend.db.models
from backend.core.database.database import Base
tables = sorted(Base.metadata.tables.keys())
print(f'Tables registered on Base.metadata: {len(tables)}')
for t in tables:
    print(' ', t)
"
echo
echo "=== try create_all NOW from inside the live container ==="
docker exec n13gp1nhrcdp0hvazvbnlxru-213557155694 python3 -c "
import asyncio, traceback
import backend.db.models
from backend.core.database.database import Base, engine
async def go():
    try:
        async with engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        print('create_all completed without exception')
    except Exception as e:
        print('CAUGHT:', type(e).__name__, e)
        traceback.print_exc()
asyncio.run(go())
" 2>&1 | tail -40
