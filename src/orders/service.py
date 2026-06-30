import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.order import Order
from src.db.tenant_scope import get_project_owned


async def get_order(
    db: AsyncSession, order_id: uuid.UUID, tenant_id: uuid.UUID
) -> Order | None:
    return await get_project_owned(db, Order, order_id, tenant_id)


async def list_orders_for_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[Order]:
    result = await db.execute(
        select(Order).where(Order.project_id == project_id)
    )
    return list(result.scalars().all())
