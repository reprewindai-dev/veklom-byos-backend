import asyncio
import sys
import hashlib
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.core.database.database import get_db, async_session
from backend.db.models.user import User, _uuid
from backend.db.models.workspace import Workspace
from backend.db.models.marketplace import Vendor, MarketplaceListing, InstalledAsset
from backend.db.models.billing import Invoice
from backend.core.config.settings import settings
import stripe
import os
from fastapi.testclient import TestClient
from backend.apps.api.main import app
import json
import hmac

async def run_test():
    async with async_session() as db:
        import uuid
        # Create user
        uid = str(uuid.uuid4())
        wsid = str(uuid.uuid4())
        u = User(id=uid, email=f'test_{uid}@example.com', hashed_password='foo', workspace_id=wsid)
        db.add(u)
        w = Workspace(id=wsid, name='Test WS')
        db.add(w)
        await db.commit()
        
        # Create Vendor
        vid = str(uuid.uuid4())
        v = Vendor(id=vid, user_id=uid, business_name='Smoke Test', status='approved', stripe_account_id='acct_test', total_revenue=0.0)
        db.add(v)
        await db.commit()
        
        # Create Listing
        lid = str(uuid.uuid4())
        l = MarketplaceListing(id=lid, vendor_id=vid, name='Test App', price=50.0, inventory_quantity=10, inventory_reserved=1)
        db.add(l)
        await db.commit()
        
        # Call the stripe webhook logic directly
        whsec = os.getenv('STRIPE_WEBHOOK_SECRET_LIVE', 'whsec_test123')
        os.environ['STRIPE_WEBHOOK_SECRET'] = whsec
        os.environ['STRIPE_WEBHOOK_SECRET_LIVE'] = whsec
        
        payload = {
            'id': 'evt_test',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test',
                    'amount_total': 5000,
                    'metadata': {
                        'type': 'marketplace',
                        'user_id': uid,
                        'workspace_id': wsid,
                        'listing_id': lid,
                        'vendor_id': vid,
                        'expected_platform_fee': '500'
                    }
                }
            }
        }
        
        payload_str = json.dumps(payload)
        t = int(datetime.now(timezone.utc).timestamp())
        sig_payload = f'{t}.{payload_str}'
        sig = hmac.new(whsec.encode(), sig_payload.encode(), hashlib.sha256).hexdigest()
        header = f't={t},v1={sig}'
        
        client = TestClient(app)
        res = client.post('/api/v1/webhooks/stripe', content=payload_str, headers={'stripe-signature': header})
        print(f'Webhook Status: {res.status_code}, Body: {res.text}')
        
        await db.refresh(v)
        await db.refresh(l)
        assets = (await db.execute(select(InstalledAsset).where(InstalledAsset.listing_id == lid))).scalars().all()
        invoices = (await db.execute(select(Invoice).where(Invoice.workspace_id == wsid))).scalars().all()
        
        print(f'Vendor Rev: {v.total_revenue}')
        print(f'Listing Qty: {l.inventory_quantity}')
        print(f'Assets Created: {len(assets)}')
        print(f'Invoices Created: {len(invoices)}')
        if v.total_revenue == 45.0 and len(assets) == 1 and l.inventory_quantity == 9:
            print('SMOKE TEST SUCCESS')
        else:
            print('SMOKE TEST FAILED')
        
asyncio.run(run_test())
