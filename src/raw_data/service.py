import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.project import RawMessage


async def store_raw_message(
    db: AsyncSession,
    project_id: uuid.UUID,
    inquiry_id: uuid.UUID | None,
    direction: str,
    content: str,
    sender: str | None = None,
) -> RawMessage:
    message = RawMessage(
        project_id=project_id,
        inquiry_id=inquiry_id,
        direction=direction,
        sender=sender,
        content=content,
    )
    db.add(message)
    await db.flush()
    return message


async def get_messages_for_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[RawMessage]:
    result = await db.execute(
        select(RawMessage).where(RawMessage.project_id == project_id)
    )
    return list(result.scalars().all())
