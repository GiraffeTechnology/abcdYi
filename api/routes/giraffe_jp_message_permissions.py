import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.deps import get_current_user, get_db
from src.db.models.user import User
from src.db.models.giraffe_jp import GiraffeJPMessageCategoryPermission
from src.giraffe_jp.schemas import MessageCategoryPermissionRead, MessageCategoryPermissionUpdate
from src.giraffe_jp.message_permissions import seed_default_permissions
from src.execution_graph.writer import emit_event
from src.execution_graph import event_types

router = APIRouter()


@router.post("/permissions/seed-defaults", response_model=list[MessageCategoryPermissionRead], status_code=201)
async def seed_defaults(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    created = await seed_default_permissions(db, tenant_id=current_user.tenant_id)
    await emit_event(
        db,
        event_type=event_types.MESSAGE_CATEGORY_PERMISSIONS_SEEDED,
        payload={"tenant_id": str(current_user.tenant_id), "categories_created": len(created)},
        tenant_id=current_user.tenant_id,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    result = await db.execute(
        select(GiraffeJPMessageCategoryPermission)
        .where(GiraffeJPMessageCategoryPermission.tenant_id == current_user.tenant_id)
        .order_by(
            GiraffeJPMessageCategoryPermission.party_type,
            GiraffeJPMessageCategoryPermission.category_id,
        )
    )
    return list(result.scalars().all())


@router.get("/permissions", response_model=list[MessageCategoryPermissionRead])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPMessageCategoryPermission)
        .where(GiraffeJPMessageCategoryPermission.tenant_id == current_user.tenant_id)
        .order_by(
            GiraffeJPMessageCategoryPermission.party_type,
            GiraffeJPMessageCategoryPermission.category_id,
        )
    )
    return list(result.scalars().all())


@router.get("/permissions/{permission_id}", response_model=MessageCategoryPermissionRead)
async def get_permission(
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPMessageCategoryPermission).where(
            GiraffeJPMessageCategoryPermission.id == permission_id,
            GiraffeJPMessageCategoryPermission.tenant_id == current_user.tenant_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    return perm


@router.patch("/permissions/{permission_id}", response_model=MessageCategoryPermissionRead)
async def update_permission(
    permission_id: uuid.UUID,
    body: MessageCategoryPermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GiraffeJPMessageCategoryPermission).where(
            GiraffeJPMessageCategoryPermission.id == permission_id,
            GiraffeJPMessageCategoryPermission.tenant_id == current_user.tenant_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    perm.auto_send = body.auto_send
    await db.flush()
    await emit_event(
        db,
        event_type=event_types.MESSAGE_CATEGORY_PERMISSION_UPDATED,
        payload={
            "permission_id": str(perm.id),
            "category_id": perm.category_id,
            "auto_send": body.auto_send,
        },
        tenant_id=current_user.tenant_id,
        triggered_by_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(perm)
    return perm
