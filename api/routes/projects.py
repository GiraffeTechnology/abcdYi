import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db, get_current_user
from src.projects import service
from src.projects.schemas import (
    ProjectCreate, ProjectOut, BuyerInquiryCreate, BuyerInquiryOut
)

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectOut)
async def create_project(
    data: ProjectCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await service.create_project(
        db, current_user.tenant_id, current_user.id, data
    )
    await db.commit()
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = await service.list_projects(db, current_user.tenant_id, skip, limit)
    return [ProjectOut.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await service.get_project(db, project_id, current_user.tenant_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut.model_validate(project)


@router.post(
    "/{project_id}/buyer-inquiries",
    status_code=status.HTTP_201_CREATED,
    response_model=BuyerInquiryOut,
)
async def import_buyer_inquiry(
    project_id: uuid.UUID,
    data: BuyerInquiryCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await service.get_project(db, project_id, current_user.tenant_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    inquiry = await service.import_buyer_inquiry(
        db, project_id, current_user.id, current_user.tenant_id, data
    )
    await db.commit()
    return BuyerInquiryOut.model_validate(inquiry)


@router.get("/{project_id}/timeline")
async def get_project_timeline(
    project_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    events = await service.get_project_timeline(db, project_id, current_user.tenant_id)
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "payload": e.payload,
            "occurred_at": e.occurred_at.isoformat(),
        }
        for e in events
    ]
