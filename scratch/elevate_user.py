import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.core.config.settings import settings

engine = create_async_engine(settings.DATABASE_URL)

async def elevate():
    email = "reprewindai@gmail.com"
    async with engine.begin() as conn:
        # Find if user exists
        r = await conn.execute(text("SELECT id, email, role, is_superuser FROM users WHERE LOWER(email) = :email"), {"email": email.lower()})
        user = r.fetchone()
        if user:
            print(f"Found user: ID={user[0]}, Email={user[1]}, Current Role={user[2]}, Superuser={user[3]}")
            await conn.execute(
                text("UPDATE users SET role = 'SUPER_ADMIN', is_superuser = true WHERE id = :id"),
                {"id": user[0]}
            )
            print("Successfully elevated user to SUPER_ADMIN & is_superuser=true.")
        else:
            print(f"User {email} not found in database.")

if __name__ == "__main__":
    asyncio.run(elevate())
