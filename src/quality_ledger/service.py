import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.logistics import QualityIncident
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import QUALITY_INCIDENT_CREATED


async def create_quality_incident(
    db: AsyncSession,
    order_id: uuid.UUID,
    qc_record_id: uuid.UUID | None,
    responsible_participant_id: uuid.UUID,
    incident_type: str,
    description: str,
    tenant_id: uuid.UUID,
) -> QualityIncident:
    incident = QualityIncident(
        order_id=order_id,
        qc_record_id=qc_record_id,
        responsible_participant_id=responsible_participant_id,
        incident_type=incident_type,
        description=description,
    )
    db.add(incident)
    await db.flush()

    # Count total incidents for this participant
    count_result = await db.execute(
        select(func.count()).where(
            QualityIncident.responsible_participant_id == responsible_participant_id
        )
    )
    total_count = count_result.scalar() or 0

    await emit_event(
        db=db,
        event_type=QUALITY_INCIDENT_CREATED,
        payload={
            "incident_id": str(incident.id),
            "responsible_participant_id": str(responsible_participant_id),
            "total_incident_count": total_count,
        },
        tenant_id=tenant_id,
        order_id=order_id,
        participant_id=responsible_participant_id,
    )

    # Trigger replacement alert if threshold reached
    from src.replacement_alerts.service import check_and_trigger_replacement_alert
    await check_and_trigger_replacement_alert(
        db=db,
        participant_id=responsible_participant_id,
        project_id=None,
        tenant_id=tenant_id,
        current_count=total_count,
    )

    return incident


async def get_quality_ledger_for_participant(
    db: AsyncSession, participant_id: uuid.UUID
) -> dict:
    result = await db.execute(
        select(QualityIncident).where(
            QualityIncident.responsible_participant_id == participant_id
        ).order_by(QualityIncident.created_at.desc())
    )
    incidents = list(result.scalars().all())
    total = len(incidents)

    from src.db.models.logistics import ReplacementAlert
    alert_result = await db.execute(
        select(ReplacementAlert).where(
            ReplacementAlert.participant_id == participant_id,
            ReplacementAlert.status == "PENDING_REVIEW",
        ).limit(1)
    )
    active_alert = alert_result.scalar_one_or_none()

    return {
        "participant_id": str(participant_id),
        "total_incidents": total,
        "incidents": [
            {
                "id": str(i.id),
                "order_id": str(i.order_id),
                "incident_type": i.incident_type,
                "description": i.description,
                "created_at": i.created_at.isoformat(),
            }
            for i in incidents
        ],
        "replacement_alert_triggered": active_alert is not None,
        "quality_issue_count": total,
    }
