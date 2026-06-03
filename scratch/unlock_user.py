import asyncio
import os
import sys

# Add /app to sys.path so we can import backend packages
sys.path.append("/app")

from backend.core.database.database import async_session
from backend.db.models.user import User
from backend.db.models.billing import Subscription
from sqlalchemy import select, update

async def main():
    email = "reprewindai@gmail.com"
    async with async_session() as session:
        # Check if user exists
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        if not user:
            print(f"User {email} not found in the database.")
            return

        print(f"Current state: Role={user.role}, Status={user.status}, Superuser={user.is_superuser}")
        
        # Update user to OWNER, ACTIVE, is_superuser = True
        user.role = "OWNER"
        user.status = "ACTIVE"
        user.is_active = True
        user.is_superuser = True
        session.add(user)
        
        # Check subscriptions for the user's workspace
        ws_id = user.workspace_id
        sub_res = await session.execute(select(Subscription).where(Subscription.workspace_id == ws_id))
        sub = sub_res.scalar_one_or_none()
        if sub:
            print(f"Current subscription: plan={sub.plan}, status={sub.status}")
            sub.plan = "enterprise"
            sub.status = "active"
            session.add(sub)
        else:
            print("No subscription found, creating an active enterprise subscription...")
            from datetime import datetime, timedelta
            new_sub = Subscription(
                id=None,  # database auto-generates or model does
                user_id=user.id,
                workspace_id=ws_id,
                plan="enterprise",
                status="active",
                stripe_customer_id="mock_customer_unlocked",
                stripe_subscription_id="mock_sub_unlocked",
                current_period_end=datetime.utcnow() + timedelta(days=365)
            )
            session.add(new_sub)
            
        await session.commit()
        print(f"Successfully unlocked user {email} to OWNER/SUPER_ADMIN status with active enterprise plan.")

if __name__ == "__main__":
    asyncio.run(main())
