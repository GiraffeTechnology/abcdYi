import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.logistics import QualityIncident, ReplacementAlert
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import REPLACEMENT_ALERT_CREATED

REPLACEMENT_THRESHOLD = 3


async def check_and_trigger_replacement_alert(
    db: AsyncSession,
    participant_id: uuid.UUID,
    project_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
    current_count: int | None = None,
) -> ReplacementAlert | None:
    """
    If quality incidents >= REPLACEMENT_THRESHOLD and no active alert: create alert.
    Does NOT automatically replace the participant.
    """
    if current_count is None:
        count_result = await db.execute(
            select(func.count()).where(
                QualityIncident.responsible_participant_id == participant_id
            )
        )
        current_count = count_result.scalar() or 0

    if current_count < REPLACEMENT_THRESHOLD:
        return None

    # Check for existing active alert
    existing_result = await db.execute(
        select(ReplacementAlert).where(
            ReplacementAlert.participant_id == participant_id,
            ReplacementAlert.status == "PENDING_REVIEW",
        )
    )
    if existing_result.scalar_one_or_none():
        return None  # Already has an active alert

    alert = ReplacementAlert(
        participant_id=participant_id,
        project_id=project_id,
        trigger_reason=f"Quality issue count ({current_count}) reached replacement threshold ({REPLACEMENT_THRESHOLD})",
        quality_issue_count=current_count,
        status="PENDING_REVIEW",
    )
    db.add(alert)
    await db.flush()

    await emit_event(
        db=db,
        event_type=REPLACEMENT_ALERT_CREATED,
        payload={
            "alert_id": str(alert.id),
            "participant_id": str(participant_id),
            "quality_issue_count": current_count,
        },
        tenant_id=tenant_id,
        participant_id=participant_id,
    )
    return alert


async def review_replacement_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
    decision: str,
    reviewed_by: uuid.UUID,
    review_notes: str = "",
) -> ReplacementAlert:
    alert = await db.get(ReplacementAlert, alert_id)
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="ReplacementAlert not found")
    alert.status = decision  # "REPLACED" or "DISMISSED"
    alert.reviewed_by = reviewed_by
    alert.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    return alert
