import asyncio
import sys
import os

# Add /app to sys.path if needed
sys.path.append("/app")

from backend.core.database.database import async_session
from backend.db.models import User
from sqlalchemy import update, select

async def main():
    email = 'studiogradekits@gmail.com'
    new_hash = '$2b$12$hTFR9dOZ2omteCsIQmjQHeGE.Vp8EgmynucsW6.ke6xl0FQGmTB6O'
    try:
        async with async_session() as session:
            async with session.begin():
                res = await session.execute(select(User).where(User.email == email))
                user = res.scalar_one_or_none()
                if user:
                    user.hashed_password = new_hash
                    print(f"Updated password hash for {email}")
                else:
                    print(f"User {email} not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
