"""Tenant-scoped execution lookups, including nested references and row locks."""
from __future__ import annotations

import uuid
from fastapi import HTTPException
from sqlalchemy import select

from src.db.models.order import Order
from src.db.models.project import Project
from src.db.models.participant import Participant
from src.db.models.user import User, UserRole


async def require_order(db, order_id, tenant_id, *, lock=False):
    query = select(Order).join(Project, Order.project_id == Project.id).where(
        Order.id == order_id, Project.tenant_id == tenant_id)
    if lock:
        query = query.with_for_update(of=Order)
    order = await db.scalar(query)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    from src.permissions.project_access import require_project_access
    await require_project_access(db, order.project_id)
    return order


async def require_order_child(db, model, record_id, tenant_id):
    record = await db.get(model, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Execution record not found")
    await require_order(db, record.order_id, tenant_id)
    return record


async def require_participant(db, participant_id, tenant_id):
    if participant_id is None:
        return
    participant = await db.get(Participant, participant_id)
    if participant is None or participant.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Participant not found")


async def require_resolution_actor(db, user_id, tenant_id):
    """QC disposition is a human action; authenticate its existing role in DB."""
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="QC resolution requires an authorized human")
    if user.is_platform_admin:
        return "admin"
    roles = await db.scalars(select(UserRole.role_name).where(UserRole.user_id == user_id))
    allowed = {"admin", "operator", "approver", "buyer", "quality", "qc", "quality_manager", "production_manager"}
    for role in roles:
        if role.lower() in allowed:
            return role
    raise HTTPException(status_code=403, detail="QC resolution requires an authorized human role")
