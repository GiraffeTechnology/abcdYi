import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.project import Project, BuyerInquiry


async def get_project_by_id(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def get_inquiry_by_id(db: AsyncSession, inquiry_id: uuid.UUID) -> BuyerInquiry | None:
    result = await db.execute(
        select(BuyerInquiry).where(BuyerInquiry.id == inquiry_id)
    )
    return result.scalar_one_or_none()
