import asyncio
from backend.core.database.database import get_db_session
from backend.core.models.user import User
from sqlalchemy.future import select
from datetime import datetime, timedelta
from jose import jwt
from backend.core.config.settings import settings

async def main():
    async with get_db_session() as db:
        result = await db.execute(select(User).where(User.status == 'pending_verification'))
        users = result.scalars().all()
        for u in users:
            verify_token = jwt.encode(
                {'sub': u.id, 'exp': datetime.utcnow() + timedelta(hours=24), 'type': 'email_verify'},
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )
            print(f'User: {u.email}')
            print(f'Activation Link: {settings.FRONTEND_URL}/activate?token={verify_token}')
            print('-'*50)

if __name__ == '__main__':
    asyncio.run(main())
