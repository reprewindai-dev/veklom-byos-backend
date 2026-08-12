import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PGLCertificate(Base):
    __tablename__ = 'pgl_certificates'
    id = Column(Integer, primary_key=True)
    actor_id = Column(String)
    kind = Column(String)
    status = Column(String)

async def test():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        session.add_all([
            PGLCertificate(actor_id='actor123', kind='post', status='SUCCEEDED'),
            PGLCertificate(actor_id='actor123', kind='post', status='SUCCEEDED'),
            PGLCertificate(actor_id='actor123', kind='post', status='FAILED'),
            PGLCertificate(actor_id='actor123', kind='get', status='SUCCEEDED'),
            PGLCertificate(actor_id='other', kind='post', status='SUCCEEDED'),
        ])
        await session.commit()

        stats_result = await session.execute(
            select(
                func.count().filter(PGLCertificate.status == "SUCCEEDED"),
                func.count().filter(PGLCertificate.status.in_(["FAILED", "ROLLED_BACK"]))
            ).where(
                PGLCertificate.actor_id == 'actor123',
                PGLCertificate.kind == 'post'
            )
        )
        active_attestations, active_rollbacks = stats_result.one()
        print(f"Attestations: {active_attestations}, Rollbacks: {active_rollbacks}")

asyncio.run(test())
