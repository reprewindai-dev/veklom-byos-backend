import asyncio
import sys
import os

# Align path to import backend modules
sys.path.append("/app")

from backend.core.database.database import async_session
from backend.db.models.user import User
from backend.db.models.workspace import Workspace
from backend.db.models.billing import Subscription, WalletTransaction
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

async def seed_reviewer_incentive():
    email = "reprewindai@gmail.com"
    print(f"[*] Starting reviewer incentive seeding for: {email}")
    
    async with async_session() as session:
        # 1. Find user
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        if not user:
            print(f"[!] Error: User with email '{email}' not found in database.")
            return
            
        print(f"[+] Found User ID: {user.id}")
        ws_id = user.workspace_id or "default"
        print(f"[+] Workspace ID: {ws_id}")
        
        # 2. Verify or update Workspace Plan
        if ws_id != "default":
            ws_res = await session.execute(select(Workspace).where(Workspace.id == ws_id))
            workspace = ws_res.scalar_one_or_none()
            if workspace:
                workspace.license_tier = "starter"  # Align to "starter" (Founding)
                print(f"[+] Updated Workspace license_tier to 'starter'")
        
        # 3. Create active subscription
        # Check if active subscription exists
        sub_res = await session.execute(
            select(Subscription).where(
                Subscription.workspace_id == ws_id,
                Subscription.status == "active"
            )
        )
        existing_sub = sub_res.scalar_one_or_none()
        if not existing_sub:
            new_sub = Subscription(
                workspace_id=ws_id,
                user_id=user.id,
                plan="starter",
                status="active",
                stripe_subscription_id="sub_reviewer_founding_incentive",
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            )
            session.add(new_sub)
            print("[+] Created new 'starter' subscription for 1 month free")
        else:
            existing_sub.plan = "starter"
            print("[+] Updated existing subscription to 'starter' plan")
            
        # 4. Credit $150 minimum operating reserve
        credit_tx = WalletTransaction(
            workspace_id=ws_id,
            user_id=user.id,
            amount=150.0,
            tx_type="topup",
            description="Founding review reserve credit (1 month incentive)",
        )
        session.add(credit_tx)
        print("[+] Credited $150.00 to operating reserve wallet")
        
        await session.commit()
        print("[*] Reviewer incentive seeding successfully committed!")

if __name__ == "__main__":
    asyncio.run(seed_reviewer_incentive())
