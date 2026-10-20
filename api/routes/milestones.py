import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.order_confirmation.execution_persistence import commit_execution
from src.integrations.execution_language import normalize_execution_input, record_input_lineage
from api.deps import get_db, get_current_user
from src.milestones.schemas import MilestoneOut, MilestoneUpdate, ProductionUpdateCreate
from src.milestones.service import (
    update_milestone, create_production_update, get_production_monitoring_view
)
from src.production_monitoring.service import run_delay_prediction
from src.db.models.production import ProductionMonitoringPacket

from src.permissions.project_access import bind_request_actor

router = APIRouter(dependencies=[Depends(bind_request_actor)])


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
async def patch_milestone(
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    body, language_evidence = await normalize_execution_input(body, "milestones")
    ms = await update_milestone(
        db=db,
        milestone_id=milestone_id,
        status=body.status,
        actual_date=body.actual_date,
        predicted_date=body.predicted_date,
        notes=body.notes,
        responsible_participant_id=body.responsible_participant_id,
        updated_by_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    await record_input_lineage(db, language_evidence, tenant_id=current_user.tenant_id, user_id=current_user.id, order_id=ms.order_id)
    await commit_execution(db, tenant_id=current_user.tenant_id, user_id=current_user.id, order_id=ms.order_id)
    await db.refresh(ms)
    return ms


@router.post("/orders/{order_id}/production-updates", status_code=status.HTTP_201_CREATED)
async def add_production_update(
    order_id: uuid.UUID,
    body: ProductionUpdateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    body, language_evidence = await normalize_execution_input(body, "production_updates")
    update = await create_production_update(
        db=db,
        order_id=order_id,
        milestone_id=body.milestone_id,
        update_text=body.update_text,
        submitted_by_participant_id=body.submitted_by_participant_id,
        evidence=body.evidence,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await record_input_lineage(db, language_evidence, tenant_id=current_user.tenant_id, user_id=current_user.id, order_id=update.order_id)
    await commit_execution(db, tenant_id=current_user.tenant_id, user_id=current_user.id, order_id=update.order_id)
    await db.refresh(update)
    return {
        "id": str(update.id),
        "order_id": str(update.order_id),
        "update_text": update.update_text,
    }


@router.get("/orders/{order_id}/production-monitoring")
async def get_production_monitoring(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    view = await get_production_monitoring_view(db, order_id, current_user.tenant_id)

    pkt_result = await db.execute(
        select(ProductionMonitoringPacket)
        .where(ProductionMonitoringPacket.order_id == order_id)
        .order_by(ProductionMonitoringPacket.created_at.desc())
        .limit(1)
    )
    pkt = pkt_result.scalar_one_or_none()
    monitoring_packet = None
    if pkt:
        monitoring_packet = {
            "id": str(pkt.id),
            "delay_risk_level": pkt.delay_risk_level,
            "expedite_alert_required": pkt.expedite_alert_required,
            "recommended_action": pkt.recommended_action,
            "delayed_milestones": pkt.delayed_milestones,
        }

    return {"milestones": view["milestones"], "monitoring_packet": monitoring_packet}


@router.post("/orders/{order_id}/run-delay-prediction")
async def trigger_delay_prediction(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pkt = await run_delay_prediction(
        db=db,
        order_id=order_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await commit_execution(db, tenant_id=current_user.tenant_id, user_id=current_user.id, order_id=pkt.order_id)
    await db.refresh(pkt)
    return {
        "id": str(pkt.id),
        "order_id": str(pkt.order_id),
        "delay_risk_level": pkt.delay_risk_level,
        "expedite_alert_required": pkt.expedite_alert_required,
        "recommended_action": pkt.recommended_action,
        "delayed_milestones": pkt.delayed_milestones,
    }
