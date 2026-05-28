import asyncio
import uuid
import sys
from fastapi.testclient import TestClient

# Ensure package root is in path
sys.path.insert(0, ".")

# Override DATABASE_URL to in-memory SQLite before imports
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from backend.apps.api.main import app
from backend.core.database.database import engine, Base, async_session
from backend.db.models.marketplace import Pipeline
from backend.db.models.user import User
from backend.core.security.auth import create_access_token

async def seed_user_and_get_token(workspace_id: str, email: str) -> str:
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        user = User(
            id=user_id,
            email=email,
            hashed_password="password123",
            role="member",
            is_active=True,
            status="active",
            workspace_id=workspace_id
        )
        db.add(user)
        await db.commit()
    
    return create_access_token({"sub": user_id, "role": "member", "workspace_id": workspace_id})

async def simulate_get_pipelines(token: str, client: TestClient, results: list):
    try:
        # Simulate network delay/racing
        await asyncio.sleep(0.05)
        
        # TestClient is synchronous but we run it inside async loop using run_in_executor or direct call
        # Since TestClient can be called concurrently in the same thread/loop for in-memory, we call it
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.get("/api/v1/pipelines", headers={"Authorization": f"Bearer {token}"})
        )
        results.append(response)
    except Exception as e:
        results.append(e)

async def run_concurrent_test():
    # 0. Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[User.__table__, Pipeline.__table__]
        ))
        
    client = TestClient(app)
    
    # 1. Create two separate workspaces
    ws1_token = await seed_user_and_get_token("ws_finance", "finance@veklom.com")
    ws2_token = await seed_user_and_get_token("ws_healthcare", "medical@veklom.com")
    
    print("\n[TEST] Simulating 10 concurrent requests from Workspace A (ws_finance)...")
    results_a = []
    tasks_a = [simulate_get_pipelines(ws1_token, client, results_a) for _ in range(10)]
    await asyncio.gather(*tasks_a)
    
    # Verify all requests completed successfully (status 200)
    for i, res in enumerate(results_a):
        if isinstance(res, Exception):
            print(f"  Request {i} failed with Exception: {res}")
            assert False
        else:
            assert res.status_code == 200, f"Request {i} returned {res.status_code}: {res.text}"
            
    print("  [PASS] All 10 concurrent requests in Workspace A resolved successfully with 200 OK.")
    
    print("\n[TEST] Simulating 10 concurrent requests from Workspace B (ws_healthcare)...")
    results_b = []
    tasks_b = [simulate_get_pipelines(ws2_token, client, results_b) for _ in range(10)]
    await asyncio.gather(*tasks_b)
    
    for i, res in enumerate(results_b):
        if isinstance(res, Exception):
            print(f"  Request {i} failed with Exception: {res}")
            assert False
        else:
            assert res.status_code == 200, f"Request {i} returned {res.status_code}: {res.text}"
            
    print("  [PASS] All 10 concurrent requests in Workspace B resolved successfully with 200 OK.")
    
    # Verify that BOTH workspaces now have their own unique instances of clinical-rag, legal-redactor, etc.
    async with async_session() as db:
        from sqlalchemy import select
        res = await db.execute(select(Pipeline))
        all_pipelines = res.scalars().all()
        
        print(f"\n[VERIFY] Total pipelines seeded in DB: {len(all_pipelines)}")
        for p in all_pipelines:
            print(f"  - Pipeline ID: {p.id} | Workspace: {p.workspace_id} | Name: {p.name} | Steps template: {p.steps.get('template') if p.steps else None}")
            
        # Total should be exactly 6 (3 templates seeded per workspace for 2 workspaces)
        assert len(all_pipelines) == 6, f"Expected exactly 6 pipelines, found {len(all_pipelines)}"
        
    print("\n[OK] Pipeline Concurrency & Multi-Tenant Seeding Verification Test PASSED successfully!\n")

if __name__ == "__main__":
    asyncio.run(run_concurrent_test())
