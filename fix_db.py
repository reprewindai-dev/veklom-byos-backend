import asyncio
from backend.core.database.database import get_db_session
from backend.db.models.marketplace import InstalledAsset
from sqlalchemy import select, delete

async def main():
    async with get_db_session() as session:
        # Find all InstalledAssets for PCI-DSS
        res = await session.execute(select(InstalledAsset).where(InstalledAsset.listing_id == 'ls_pci_dss'))
        assets = res.scalars().all()
        for a in assets:
            print(f"Deleting InstalledAsset {a.id} for workspace {a.workspace_id}")
            await session.delete(a)
            
        await session.commit()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
