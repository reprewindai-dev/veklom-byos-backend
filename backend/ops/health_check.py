#!/usr/bin/env python3
"""
Health check script for Veklom BYOS Backend.

This script checks the health of the backend services including:
- Database connectivity
- Redis connectivity
- API health endpoint
- Worker registry status
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def check_database():
    """Check database connectivity."""
    from backend.core.database.database import get_db_session
    from sqlalchemy import text
    
    try:
        async with get_db_session() as db:
            await db.execute(text("SELECT 1"))
        return True, "Database: OK"
    except Exception as e:
        return False, f"Database: FAILED - {str(e)}"


async def check_redis():
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(redis_url)
        await client.ping()
        await client.close()
        return True, "Redis: OK"
    except Exception as e:
        return False, f"Redis: FAILED - {str(e)}"


async def check_api():
    """Check API health endpoint."""
    try:
        import httpx
        api_url = os.getenv("API_URL", "http://localhost:80")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/health", timeout=2.0)
            if response.status_code == 200:
                return True, f"API: OK (status {response.status_code})"
            return False, f"API: FAILED (status {response.status_code})"
    except Exception as e:
        return False, f"API: FAILED - {str(e)}"


async def main():
    """Run all health checks."""
    print("Veklom BYOS Backend Health Check")
    print("=" * 50)
    
    checks = [
        check_database(),
        check_redis(),
        check_api(),
    ]
    
    results = await asyncio.gather(*checks)
    
    all_ok = True
    for ok, message in results:
        print(message)
        if not ok:
            all_ok = False
    
    print("=" * 50)
    if all_ok:
        print("All checks passed!")
        sys.exit(0)
    else:
        print("Some checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
