import asyncio
import sys
import os

# Add /app to sys.path if needed
sys.path.append("/app")

from backend.core.database.database import async_session
from backend.db.models import User
from sqlalchemy import select

async def main():
    try:
        async with async_session() as session:
            res = await session.execute(select(User).where(User.email == 'studiogradekits@gmail.com'))
            user = res.scalar_one_or_none()
            if user:
                # Check both password_hash and hashed_password if they exist
                pwd_hash = getattr(user, "password_hash", "N/A")
                hashed_pwd = getattr(user, "hashed_password", "N/A")
                print(f"User found: {user.email}")
                print(f"password_hash: {pwd_hash}")
                print(f"hashed_password: {hashed_pwd}")
            else:
                print("User not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
