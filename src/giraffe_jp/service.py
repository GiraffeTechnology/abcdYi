import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.giraffe_jp import (
    GiraffeJPServiceNode,
    GiraffeJPConfirmationRequest,
    GiraffeJPCustomerServiceTask,
)


async def create_service_node(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    node_type: str,
    location_country: str | None = None,
    node_metadata: dict | None = None,
) -> GiraffeJPServiceNode:
    node = GiraffeJPServiceNode(
        tenant_id=tenant_id,
        name=name,
        node_type=node_type,
        location_country=location_country,
        node_metadata=node_metadata,
    )
    db.add(node)
    await db.flush()
    return node


async def list_service_nodes(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[GiraffeJPServiceNode]:
    result = await db.execute(
        select(GiraffeJPServiceNode)
        .where(GiraffeJPServiceNode.tenant_id == tenant_id)
        .order_by(GiraffeJPServiceNode.created_at.desc())
    )
    return list(result.scalars().all())


async def get_service_node(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    node_id: uuid.UUID,
) -> GiraffeJPServiceNode | None:
    result = await db.execute(
        select(GiraffeJPServiceNode).where(
            GiraffeJPServiceNode.tenant_id == tenant_id,
            GiraffeJPServiceNode.id == node_id,
        )
    )
    return result.scalar_one_or_none()


async def create_confirmation_request(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    request_type: str,
    project_id: uuid.UUID | None = None,
    service_node_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> GiraffeJPConfirmationRequest:
    req = GiraffeJPConfirmationRequest(
        tenant_id=tenant_id,
        project_id=project_id,
        service_node_id=service_node_id,
        request_type=request_type,
        payload=payload,
    )
    db.add(req)
    await db.flush()
    return req


async def create_customer_service_task(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    task_type: str,
    project_id: uuid.UUID | None = None,
    description: str | None = None,
    assignee_user_id: uuid.UUID | None = None,
) -> GiraffeJPCustomerServiceTask:
    task = GiraffeJPCustomerServiceTask(
        tenant_id=tenant_id,
        project_id=project_id,
        task_type=task_type,
        description=description,
        assignee_user_id=assignee_user_id,
    )
    db.add(task)
    await db.flush()
    return task
