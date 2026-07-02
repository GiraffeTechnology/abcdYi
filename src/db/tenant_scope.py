"""Tenant-scoped fetch helpers.

Multi-tenant isolation is enforced here. Every "fetch one row by id" path that
serves an authenticated request must resolve the row's owning tenant and reject
(treat as 404) anything that does not belong to the caller's tenant.

Entities reach their tenant in one of three ways:

* directly, via a ``tenant_id`` column (Project, Participant, ApprovalRequest,
  ExecutionEvent, ...);
* via ``project_id`` -> ``projects.tenant_id`` (RFQ, DecisionPacket, Order, ...);
* via ``order_id`` -> ``orders.project_id`` -> ``projects.tenant_id``
  (Milestone, QCRecord, Shipment, ExpediteAlert, ...).

Cross-tenant access returns ``None`` (callers translate to 404) rather than 403
so resource existence is not leaked across tenants.
"""
from __future__ import annotations

import uuid
from typing import Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.project import Project
from src.db.models.order import Order

T = TypeVar("T")


async def project_tenant_id(db: AsyncSession, project_id) -> Optional[uuid.UUID]:
    if project_id is None:
        return None
    return await db.scalar(select(Project.tenant_id).where(Project.id == project_id))


async def order_tenant_id(db: AsyncSession, order_id) -> Optional[uuid.UUID]:
    if order_id is None:
        return None
    project_id = await db.scalar(select(Order.project_id).where(Order.id == order_id))
    return await project_tenant_id(db, project_id)


async def project_belongs_to_tenant(db: AsyncSession, project_id, tenant_id) -> bool:
    return project_id is not None and await project_tenant_id(db, project_id) == tenant_id


async def order_belongs_to_tenant(db: AsyncSession, order_id, tenant_id) -> bool:
    return order_id is not None and await order_tenant_id(db, order_id) == tenant_id


async def get_tenant_owned(
    db: AsyncSession, model: Type[T], obj_id, tenant_id
) -> Optional[T]:
    """Fetch a row whose model has a direct ``tenant_id`` column."""
    obj = await db.get(model, obj_id)
    if obj is None or getattr(obj, "tenant_id", None) != tenant_id:
        return None
    return obj


async def get_project_owned(
    db: AsyncSession, model: Type[T], obj_id, tenant_id
) -> Optional[T]:
    """Fetch a row whose model reaches its tenant via ``project_id``."""
    obj = await db.get(model, obj_id)
    if obj is None:
        return None
    if not await project_belongs_to_tenant(db, getattr(obj, "project_id", None), tenant_id):
        return None
    return obj


async def get_order_owned(
    db: AsyncSession, model: Type[T], obj_id, tenant_id
) -> Optional[T]:
    """Fetch a row whose model reaches its tenant via ``order_id``."""
    obj = await db.get(model, obj_id)
    if obj is None:
        return None
    if not await order_belongs_to_tenant(db, getattr(obj, "order_id", None), tenant_id):
        return None
    return obj
