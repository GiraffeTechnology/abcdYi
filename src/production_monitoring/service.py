import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.production import Milestone, ProductionMonitoringPacket, ExpediteAlert
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion
from src.db.models.order import Order
from src.production_monitoring.delay_predictor import predict_completion_date
from src.approval_gates.service import create_approval_request, require_approved
from src.db.tenant_scope import order_belongs_to_tenant
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import (
    PRODUCTION_DELAY_PREDICTED, EXPEDITE_ALERT_CREATED, EXPEDITE_ALERT_APPROVED
)
from src.services.delivery_feasibility_service import DeliveryFeasibilityService

_feasibility_service = DeliveryFeasibilityService()


async def _load_form_fields(db: AsyncSession, order: Order) -> dict:
    if not order.locked_form_version_id:
        return {}
    version = await db.get(DynamicOrderFormVersion, order.locked_form_version_id)
    return version.fields if version else {}


async def run_delay_prediction(
    db: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ProductionMonitoringPacket:
    order = await db.get(Order, order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")

    form_fields = await _load_form_fields(db, order)

    # Load milestones
    ms_result = await db.execute(
        select(Milestone).where(Milestone.order_id == order_id)
    )
    milestones = list(ms_result.scalars().all())
    milestone_dicts = [
        {
            "milestone_type": m.milestone_type,
            "planned_date": m.planned_date,
            "predicted_date": m.predicted_date,
            "actual_date": m.actual_date,
            "status": m.status,
            "responsible_participant_id": m.responsible_participant_id,
        }
        for m in milestones
    ]

    prediction = predict_completion_date(milestone_dicts, form_fields)

    pkt = ProductionMonitoringPacket(
        order_id=order_id,
        standard_completion_date=prediction["standard_completion_date"],
        predicted_completion_date=prediction["predicted_completion_date"],
        delay_risk_level=prediction["delay_risk_level"],
        responsible_participant_id=prediction["responsible_participant_id"],
        delayed_milestones=prediction["delayed_milestones"],
        recommended_action=prediction["recommended_action"],
        expedite_alert_required=prediction["expedite_alert_required"],
        human_approval_required=True,
    )
    db.add(pkt)
    await db.flush()

    if prediction["expedite_alert_required"]:
        responsible_id = prediction["responsible_participant_id"]
        alert = ExpediteAlert(
            order_id=order_id,
            monitoring_packet_id=pkt.id,
            target_participant_id=responsible_id,
            alert_message=(
                f"Expedite required: {prediction['recommended_action']} "
                f"Delay risk: {prediction['delay_risk_level']}. "
                f"Delayed milestones: {', '.join(prediction['delayed_milestones'])}."
            ),
            status="DRAFT",
        )
        db.add(alert)
        await db.flush()

        await create_approval_request(
            db=db,
            tenant_id=tenant_id,
            action_type="EXPEDITE_NOTIFY",
            resource_type="expedite_alert",
            resource_id=alert.id,
            proposed_payload={
                "alert_id": str(alert.id),
                "order_id": str(order_id),
                "delay_risk_level": prediction["delay_risk_level"],
                "recommended_action": prediction["recommended_action"],
            },
            affected_participant_id=responsible_id,
            created_by=user_id,
        )

        await emit_event(
            db=db,
            event_type=EXPEDITE_ALERT_CREATED,
            payload={"alert_id": str(alert.id), "order_id": str(order_id)},
            tenant_id=tenant_id,
            order_id=order_id,
            triggered_by_user_id=user_id,
        )

    await emit_event(
        db=db,
        event_type=PRODUCTION_DELAY_PREDICTED,
        payload={
            "order_id": str(order_id),
            "delay_risk_level": prediction["delay_risk_level"],
            "expedite_alert_required": prediction["expedite_alert_required"],
        },
        tenant_id=tenant_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )

    # GLTG reforecast: re-evaluate delivery feasibility with current milestone state
    try:
        await _feasibility_service.evaluate(
            db=db,
            order_id=order_id,
            tenant_id=tenant_id,
            project_id=order.project_id,
            triggered_by_user_id=user_id,
        )
    except Exception:
        # Reforecast is best-effort; do not block delay prediction on GLTG errors
        pass

    return pkt


async def send_expedite_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ExpediteAlert:
    await require_approved(
        db,
        approval_id,
        action_type="EXPEDITE_NOTIFY",
        resource_type="expedite_alert",
        resource_id=alert_id,
        tenant_id=tenant_id,
    )

    alert = await db.get(ExpediteAlert, alert_id)
    if not alert or not await order_belongs_to_tenant(db, alert.order_id, tenant_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="ExpediteAlert not found")

    alert.status = "SENT"
    alert.human_approved_by = user_id
    alert.human_approved_at = datetime.now(timezone.utc)
    alert.sent_at = datetime.now(timezone.utc)
    await db.flush()

    await emit_event(
        db=db,
        event_type=EXPEDITE_ALERT_APPROVED,
        payload={"alert_id": str(alert_id), "order_id": str(alert.order_id)},
        tenant_id=tenant_id,
        order_id=alert.order_id,
        triggered_by_user_id=user_id,
    )
    return alert
