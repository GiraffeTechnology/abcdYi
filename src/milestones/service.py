import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.production import Milestone, ProductionUpdate
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import MILESTONE_UPDATED

VALID_MILESTONE_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "DELAYED"}


async def update_milestone(
    db: AsyncSession,
    milestone_id: uuid.UUID,
    status: str = None,
    actual_date=None,
    predicted_date=None,
    notes: str = None,
    responsible_participant_id=None,
    updated_by_user_id=None,
    tenant_id=None,
) -> Milestone:
    ms = await db.get(Milestone, milestone_id)
    if not ms:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Milestone not found")

    if status:
        ms.status = status
    if actual_date is not None:
        ms.actual_date = actual_date
    if predicted_date is not None:
        ms.predicted_date = predicted_date
        # Auto-mark as DELAYED if predicted > planned
        if ms.planned_date and predicted_date > ms.planned_date:
            ms.status = "DELAYED"
    if notes is not None:
        ms.notes = notes
    if responsible_participant_id is not None:
        ms.responsible_participant_id = responsible_participant_id

    # Save ProductionUpdate record
    update = ProductionUpdate(
        order_id=ms.order_id,
        milestone_id=milestone_id,
        update_text=f"Milestone {ms.milestone_type} updated to {ms.status}. {notes or ''}",
        submitted_by_participant_id=responsible_participant_id,
    )
    db.add(update)
    await db.flush()

    if tenant_id:
        await emit_event(
            db=db,
            event_type=MILESTONE_UPDATED,
            payload={
                "milestone_id": str(milestone_id),
                "milestone_type": ms.milestone_type,
                "status": ms.status,
                "order_id": str(ms.order_id),
            },
            tenant_id=tenant_id,
            order_id=ms.order_id,
            triggered_by_user_id=updated_by_user_id,
        )

    return ms


async def create_production_update(
    db: AsyncSession,
    order_id: uuid.UUID,
    milestone_id: uuid.UUID | None,
    update_text: str,
    submitted_by_participant_id: uuid.UUID | None,
    evidence: dict = None,
) -> ProductionUpdate:
    update = ProductionUpdate(
        order_id=order_id,
        milestone_id=milestone_id,
        update_text=update_text,
        submitted_by_participant_id=submitted_by_participant_id,
        evidence=evidence or {},
    )
    db.add(update)
    await db.flush()
    return update


async def get_production_monitoring_view(db: AsyncSession, order_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(Milestone)
        .where(Milestone.order_id == order_id)
        .order_by(Milestone.created_at)
    )
    milestones = list(result.scalars().all())

    completed = [m for m in milestones if m.status == "COMPLETED"]
    delayed = [m for m in milestones if m.status == "DELAYED"]
    pending = [m for m in milestones if m.status in ("PENDING", "IN_PROGRESS")]

    next_ms = pending[0] if pending else None

    return {
        "order_id": str(order_id),
        "milestones": [
            {
                "id": str(m.id),
                "milestone_type": m.milestone_type,
                "planned_date": m.planned_date.isoformat() if m.planned_date else None,
                "predicted_date": m.predicted_date.isoformat() if m.predicted_date else None,
                "actual_date": m.actual_date.isoformat() if m.actual_date else None,
                "status": m.status,
                "notes": m.notes,
            }
            for m in milestones
        ],
        "completed_count": len(completed),
        "delayed_count": len(delayed),
        "next_milestone": {
            "id": str(next_ms.id),
            "milestone_type": next_ms.milestone_type,
            "planned_date": next_ms.planned_date.isoformat() if next_ms.planned_date else None,
        } if next_ms else None,
    }
