from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.base import AsyncSessionLocal

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
