import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_current_user, get_db
from src.db.models.user import User
from src.giraffe_jp.schemas import ServiceNodeCreate, ServiceNodeRead
from src.giraffe_jp.service import create_service_node, list_service_nodes, get_service_node

router = APIRouter()


@router.post("/service-nodes", response_model=ServiceNodeRead, status_code=201)
async def create_node(
    body: ServiceNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await create_service_node(
        db,
        tenant_id=current_user.tenant_id,
        name=body.name,
        node_type=body.node_type,
        location_country=body.location_country,
        node_metadata=body.node_metadata,
    )
    await db.commit()
    await db.refresh(node)
    return node


@router.get("/service-nodes", response_model=list[ServiceNodeRead])
async def list_nodes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_service_nodes(db, tenant_id=current_user.tenant_id)


@router.get("/service-nodes/{node_id}", response_model=ServiceNodeRead)
async def get_node(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await get_service_node(db, tenant_id=current_user.tenant_id, node_id=node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Service node not found")
    return node
