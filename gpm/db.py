from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool
from gpm.config import settings


engine = create_async_engine(settings.GPM_DATABASE_URL, echo=False, poolclass=NullPool)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class GPMBase(DeclarativeBase):
    pass


async def get_gpm_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
