import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.project import Project, BuyerInquiry, RawMessage
from src.db.models.execution_graph import ExecutionEvent
from src.projects.schemas import ProjectCreate, BuyerInquiryCreate
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import (
    PROJECT_CREATED, BUYER_INQUIRY_RECEIVED
)


async def create_project(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ProjectCreate,
) -> Project:
    project = Project(
        tenant_id=tenant_id,
        title=data.title,
        status="OPEN",
        created_by=user_id,
    )
    db.add(project)
    await db.flush()

    await emit_event(
        db=db,
        event_type=PROJECT_CREATED,
        payload={"title": project.title, "project_id": str(project.id)},
        tenant_id=tenant_id,
        project_id=project.id,
        triggered_by_user_id=user_id,
    )
    return project


async def get_project(
    db: AsyncSession, project_id: uuid.UUID, tenant_id: uuid.UUID
) -> Project | None:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def list_projects(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Project]:
    result = await db.execute(
        select(Project)
        .where(Project.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def import_buyer_inquiry(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    data: BuyerInquiryCreate,
) -> BuyerInquiry:
    inquiry = BuyerInquiry(
        project_id=project_id,
        buyer_participant_id=data.buyer_participant_id,
        raw_text=data.raw_text,
        source_channel=data.source_channel,
    )
    db.add(inquiry)
    await db.flush()

    raw_message = RawMessage(
        project_id=project_id,
        inquiry_id=inquiry.id,
        direction="INBOUND",
        content=data.raw_text,
    )
    db.add(raw_message)
    await db.flush()

    await emit_event(
        db=db,
        event_type=BUYER_INQUIRY_RECEIVED,
        payload={
            "inquiry_id": str(inquiry.id),
            "raw_text": data.raw_text,
            "source_channel": data.source_channel,
        },
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )
    return inquiry


async def get_project_timeline(
    db: AsyncSession, project_id: uuid.UUID, tenant_id: uuid.UUID
) -> list[ExecutionEvent]:
    result = await db.execute(
        select(ExecutionEvent)
        .where(
            ExecutionEvent.project_id == project_id,
            ExecutionEvent.tenant_id == tenant_id,
        )
        .order_by(ExecutionEvent.occurred_at.asc())
    )
    return list(result.scalars().all())
