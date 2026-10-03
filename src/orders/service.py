from __future__ import annotations
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.order import Order
from src.db.models.project import Project
from src.db.tenant_scope import get_project_owned
from src.orders.state_machine import transition
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import QC_REQUESTED


async def request_qc(
    db: AsyncSession, order_id: uuid.UUID, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> Order:
    """Record an operator's QC handoff using the existing order state model."""
    from fastapi import HTTPException

    # Lock the tenant-owned order so repeated/concurrent requests cannot create
    # duplicate transition evidence. The caller owns the transaction.
    order = await db.scalar(
        select(Order)
        .join(Project, Order.project_id == Project.id)
        .where(Order.id == order_id, Project.tenant_id == tenant_id)
        .with_for_update(of=Order)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    previous_status = order.status
    try:
        next_status = transition(previous_status, "QC_PENDING")
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot request QC for order in status {previous_status}. Must be IN_PRODUCTION.",
        ) from exc

    order.status = next_status
    await emit_event(
        db=db,
        event_type=QC_REQUESTED,
        payload={"order_id": str(order_id), "previous_status": previous_status, "status": next_status},
        tenant_id=tenant_id,
        project_id=order.project_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )
    return order


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
