import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.deps import get_current_user, get_db
from src.db.models.user import User
from src.db.models.giraffe_jp import GiraffeJPFormalwearOrderProfile, GiraffeJPC2B2MRoleEdge
from src.giraffe_jp.schemas import (
    FormalwearProfileCreate,
    FormalwearProfileRead,
    FormalwearProfileUpdate,
    C2B2MEdgeRead,
)
from src.giraffe_jp.formalwear import (
    create_formalwear_profile,
    initialize_default_c2b2m_edges_for_project,
)
from src.execution_graph.writer import emit_event
from src.execution_graph import event_types

router = APIRouter()


@router.post("/projects/{project_id}/formalwear-profile", response_model=FormalwearProfileRead, status_code=201)
async def create_profile(
    project_id: uuid.UUID,
    body: FormalwearProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await create_formalwear_profile(
        db,
        tenant_id=current_user.tenant_id,
        project_id=project_id,
        garment_category=body.garment_category,
        hollow_to_hem_cm=body.hollow_to_hem_cm,
        model_try_on_required=body.model_try_on_required,
        local_alteration_possible=body.local_alteration_possible,
        custom_measurements=body.custom_measurements,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/projects/{project_id}/formalwear-profile", response_model=FormalwearProfileRead)
async def get_profile(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPFormalwearOrderProfile).where(
            GiraffeJPFormalwearOrderProfile.project_id == project_id,
            GiraffeJPFormalwearOrderProfile.tenant_id == current_user.tenant_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Formalwear profile not found")
    return profile


@router.patch("/projects/{project_id}/formalwear-profile", response_model=FormalwearProfileRead)
async def update_profile(
    project_id: uuid.UUID,
    body: FormalwearProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPFormalwearOrderProfile).where(
            GiraffeJPFormalwearOrderProfile.project_id == project_id,
            GiraffeJPFormalwearOrderProfile.tenant_id == current_user.tenant_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Formalwear profile not found")

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()
    await emit_event(
        db,
        event_type=event_types.FORMALWEAR_ORDER_PROFILE_UPDATED,
        payload={"profile_id": str(profile.id), "updates": update_data},
        tenant_id=current_user.tenant_id,
        project_id=project_id,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/projects/{project_id}/c2b2m-edges/initialize", response_model=list[C2B2MEdgeRead], status_code=201)
async def initialize_edges(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    edges = await initialize_default_c2b2m_edges_for_project(
        db,
        tenant_id=current_user.tenant_id,
        project_id=project_id,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    for edge in edges:
        await db.refresh(edge)
    return edges


@router.get("/projects/{project_id}/c2b2m-edges", response_model=list[C2B2MEdgeRead])
async def list_edges(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPC2B2MRoleEdge)
        .where(
            GiraffeJPC2B2MRoleEdge.project_id == project_id,
            GiraffeJPC2B2MRoleEdge.tenant_id == current_user.tenant_id,
        )
        .order_by(GiraffeJPC2B2MRoleEdge.created_at)
    )
    return list(result.scalars().all())
