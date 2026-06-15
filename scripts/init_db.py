"""
Run: uv run python scripts/init_db.py
Creates schema and verifies table count.
"""
import asyncio
from src.db.base import engine
import src.db.models  # noqa: F401 — triggers model registration
from src.db.base import Base

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(main())
